from typing import List, Tuple
from datetime import datetime, timedelta
from scipy import optimize

from vehicle import Vehicle
from consumer_model import TimeInterval, PowerCurve, Consumer

def vehiclepower(v: Vehicle, startTime: datetime, t: datetime) -> int: # returns the power from vehicle v during time t when the charging starts at time startTime
    if startTime <= t < startTime + timedelta(minutes=v.charge_duration):
        return v.charge_max*1000
    return 0
    
def greedy(vehicles: List[Vehicle], simulationdate: datetime, production: List[float]) -> Tuple[List[Consumer], List[float]]:
    vehicles = Vehicle.sort_vehicles_by_max_power(vehicles)
    powerUsage = [0.0]*24*60
    consumers = []

    t = datetime(simulationdate.year,simulationdate.month,simulationdate.day)
    end_time = t + timedelta(days=1)
    for v in vehicles:
        maxstationpower = v.charge_max
        minduration = v.charge_duration
        parkduration = int((v.time_leave-v.time_arrive).total_seconds()/60)
        stationpower: List[float] = []
        # reduce max power if possible
        if(maxstationpower>20 and minduration<30 and parkduration>4*minduration):
            print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/4 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
            maxstationpower = maxstationpower/4
            minduration = minduration*4
        if(maxstationpower>15 and parkduration>2*minduration):
            print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/2 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
            maxstationpower = maxstationpower/2
            minduration = minduration*2

        # reduce power at the end if charging takes longer than 2 hours
        if(minduration>=120):
            stationpower = [maxstationpower*1000]*(int(minduration*0.85)) # charge 70% of energy with max energy
            slopeduration = int(0.15*v.energy_required/maxstationpower*4/3*60)
            stationpower.extend([(maxstationpower-maxstationpower/2*t/slopeduration)*1000 for t in range(0,slopeduration)])
            duration = int(slopeduration+0.85*minduration)
            # check if the charging duration is still shorter then the parking time
            if(duration>parkduration):
                stationpower = [maxstationpower*1000]*minduration
            else:
                minduration = duration
        else:
            stationpower = [maxstationpower*1000]*minduration
        print(f"v.energy_required: {v.energy_required}, scheduled: {sum(stationpower)/60/1000:0.2f}")

        end_time = v.time_leave - timedelta(minutes=minduration)

        bestStartTime = None
        leastGridEnergy = float('inf')
        t = v.time_arrive
        if(t==end_time):
            bestStartTime=t
        while t < end_time:
            gridEnergyUsed = 0
            chargeTime = t
            while chargeTime < t + timedelta(minutes=minduration):
                index = int((chargeTime-simulationdate).total_seconds()/60)
                solarAvailable = production[index] - \
                                powerUsage[index] - stationpower[int((chargeTime-t).total_seconds()/60)]
                if solarAvailable < 0:
                    gridEnergyUsed = gridEnergyUsed - solarAvailable/60
                
                chargeTime += timedelta(minutes=1)
            if gridEnergyUsed < leastGridEnergy:
                leastGridEnergy = gridEnergyUsed
                bestStartTime = t
            t += timedelta(minutes=1)
        # set start time to best possible time
        chargeTime = bestStartTime
        end_time = bestStartTime + timedelta(minutes=minduration)

        while chargeTime < end_time:
            index = int((chargeTime-simulationdate).total_seconds()/60)
            powerUsage[index] = powerUsage[index] + stationpower[int((chargeTime-bestStartTime).total_seconds()/60)]
            chargeTime += timedelta(minutes=1)

        interval: TimeInterval = TimeInterval(bestStartTime,bestStartTime+timedelta(minutes=minduration))
        powercurve: PowerCurve = PowerCurve(stationpower,interval)
        consumer: Consumer = Consumer(v.id_user,powercurve,interval)
        consumers.append(consumer)
        print("Added "+str(consumer.id_user)+" with starting time "+str(consumer.interval.time_start))

    return consumers,powerUsage
    
def differential_evolution(vehicles: List[Vehicle], simulationdate: datetime, production: List[float])  -> Tuple[List[Consumer], List[float]]:
    consumers = []

    def targetfunction(t: datetime,startTimes: List[datetime]):
        temp = 0
        for j in range(len(vehicles)):
            v = vehicles[j]
            temp = temp + vehiclepower(v,startTimes[j],t)
        t = (t-simulationdate).total_seconds()/60
        erg = production[int(t)] - temp
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

    powerUsage = []

    while current_time < end_time:
        usage = sum(vehiclepower(vehicles[j], result[j], current_time) for j in range(len(vehicles)))

        powerUsage.append(usage)
        current_time+=timedelta(minutes=1)

    return consumers, powerUsage