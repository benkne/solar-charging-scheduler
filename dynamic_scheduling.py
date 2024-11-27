from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from scipy import optimize

from vehicle import Vehicle
from consumer_model import TimeInterval, PowerCurve, Consumer
from renewable_production import Production

def vehiclepower(v: Vehicle, startTime: datetime, t: datetime) -> int: # returns the power from vehicle v during time t when the charging starts at time startTime
    if startTime <= t < startTime + timedelta(minutes=v.charge_duration):
        return v.charge_max*1000
    return 0
    
def greedy(vehicles: List[Vehicle], simulationdate: datetime, production: Production) -> Tuple[List[Consumer], Dict[datetime, int]]:
    vehicles = Vehicle.sort_vehicles_by_max_power(vehicles)
    powerUsage = []
    consumers = []

    t = datetime(simulationdate.year,simulationdate.month,simulationdate.day)
    end_time = t + timedelta(days=1)
    while t < end_time: # create list of CurrentPower for simulationd day (descrete 1 minute intervals)
        powerUsage.append((t,0))
        t += timedelta(minutes=1)
    powerUsage = {timestamp: power for timestamp,power in powerUsage}
    for v in vehicles:
        bestStartTime = None
        leastGridEnergy = float('inf')
        t = v.time_arrive
        end_time = v.time_leave - timedelta(minutes=v.charge_duration)

        while t < end_time:
            gridEnergyUsed = 0
            chargeTime = t
            while chargeTime < t + timedelta(minutes=v.charge_duration):
                solarAvailable = production.production[int((chargeTime-simulationdate).total_seconds()/60)] - \
                                powerUsage[chargeTime] - v.charge_max*1000
                if solarAvailable < 0:
                    gridEnergyUsed = gridEnergyUsed - solarAvailable/60
                
                chargeTime += timedelta(minutes=1)
            if gridEnergyUsed < leastGridEnergy:
                leastGridEnergy = gridEnergyUsed
                bestStartTime = t
            t += timedelta(minutes=1)
        # set start time to best possible time
        chargeTime = bestStartTime
        end_time = bestStartTime + timedelta(minutes=v.charge_duration)

        while chargeTime < end_time:
            powerUsage[chargeTime] = powerUsage[chargeTime] + v.charge_max*1000
            chargeTime += timedelta(minutes=1)

        interval: TimeInterval = TimeInterval(bestStartTime,bestStartTime+timedelta(minutes=v.charge_duration))
        powercurve: PowerCurve = PowerCurve([v.charge_max*1000]*v.charge_duration,interval)
        consumer: Consumer = Consumer(v.id_user,powercurve,interval)
        consumers.append(consumer)
        print("Added "+str(consumer.id_user)+" with starting time "+str(consumer.interval.time_start))

    return consumers,powerUsage
    
def differential_evolution(vehicles: List[Vehicle], simulationdate: datetime, production: Production)  -> Tuple[List[Consumer], Dict[datetime, int]]:
    powerUsage = []
    consumers = []

    def targetfunction(t: datetime,startTimes: List[datetime]):
        temp = 0
        for j in range(len(vehicles)):
            v = vehicles[j]
            temp = temp + vehiclepower(v,startTimes[j],t)
        t = (t-simulationdate).total_seconds()/60
        erg = production.production[int(t)] - temp
        return  -(erg if erg<0 else 0)

    def objective(st: List[int]):
        startTimes = [simulationdate+timedelta(minutes=s) for s in st]
        energy = 0
    
        end_time = simulationdate + timedelta(days=1)
        current_time = simulationdate

        while current_time < end_time:
            energy += targetfunction(current_time, startTimes)
            current_time += timedelta(minutes=1)
        
        return energy

    def callback(xk, convergence):
        energy = objective(xk)
        if energy<=100:
            print(f"Stopping early: solution with {energy} kWh drawn from grid found.")
            return True  
        return False 
        
    # -------- main --------

    bounds = [((datetime.timestamp(v.time_arrive)-datetime.timestamp(simulationdate))/60, 
               (datetime.timestamp(v.time_leave - timedelta(minutes=v.charge_duration))-datetime.timestamp(simulationdate))/60) for v in vehicles]
    print(bounds)
    result = optimize.differential_evolution(objective, bounds, tol=0.1, disp=True, mutation=(0.5, 1), x0=[(b[0]+b[1])/2 for b in bounds], callback=callback) # with bounds

    result = [simulationdate+timedelta(minutes=r) for r in result.x]
    result = [r.replace(second=0,microsecond=0) for r in result]

    for i in range(len(vehicles)):
        v = vehicles[i]
        startTime = result[i]
        i = TimeInterval(startTime,startTime+timedelta(minutes=v.charge_duration))
        p = PowerCurve([v.charge_max*1000 for i in range(v.charge_duration)],i)
        c = Consumer(v.id_user,p,i)
        consumers.append(c)

    end_time = simulationdate + timedelta(days=1)
    current_time = simulationdate

    powerUsage = {}

    while current_time < end_time:
        usage = sum(vehiclepower(vehicles[j], result[j], current_time) for j in range(len(vehicles)))

        powerUsage[current_time] = usage

        current_time += timedelta(minutes=1)

    return consumers, powerUsage