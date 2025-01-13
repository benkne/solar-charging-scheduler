import numpy as np
from typing import List, Tuple
from datetime import datetime, timedelta

from scheduling_framework.vehicle import Vehicle
from scheduling_framework.consumer_model import TimeInterval, PowerCurve, Consumer
from scheduling_framework.renewable_production import Production
from scheduling_framework.parameters import SchedulingParameters

    
# no strategy scheduling starts the charging process on arrival
def no_strategy(scheduling_parameters: SchedulingParameters, vehicles: List[Vehicle], timestamp: datetime, production: List[float]) -> Tuple[List[Consumer], List[float]]:
    consumers = []

    for v in vehicles:
        interval: TimeInterval = TimeInterval(v.time_arrive,v.time_arrive+timedelta(minutes=v.energy_required/v.charge_max*60))
        powercurve: PowerCurve = PowerCurve([v.charge_max*1000 for i in range(0,interval.intervalLength())],interval)
        consumer: Consumer = Consumer(v.id_user,powercurve)
        consumers.append(consumer)

        print("Added "+str(consumer.id_user)+" with starting time "+str(consumer.power.interval.time_start))

    return consumers

# the dynamic scheduling algorithm applies multiple strategies in optimizing the charging process
def dynamic_scheduling(scheduling_parameters: SchedulingParameters, vehicles: List[Vehicle], timestamp: datetime, production: List[float]) -> Tuple[List[Consumer], List[float]]:
    vehicles = Vehicle.sort_vehicles_by_energy(vehicles)
    powerUsage = [0.0]*24*60
    consumers = []

    simulationdate = datetime(timestamp.year,timestamp.month,timestamp.day)

    t = simulationdate
    end_time = t + timedelta(days=1)

    # (re)schedule all vehicles
    for v in vehicles:
        maxstationpower = v.charge_max
        minduration = v.charge_duration
        parkduration = int((v.time_leave-v.time_arrive).total_seconds()/60)
        stationpower: List[float] = []

        required_energy = (v.percent_leave-v.percent_arrive)/100*v.battery_size # in kWh
        parking_time = int((v.time_leave-v.time_arrive).total_seconds())/60 # in minutes

        max_possible_energy = parking_time/60*v.charge_max
        if(max_possible_energy<required_energy): # check if the desired SoC can possibly be reached bevore leaving
            percent_leave_old = v.percent_leave
            percent_leave = max_possible_energy*100/v.battery_size+v.percent_arrive # recalculate SoC_leave so that the vehicle can be charged within parking time
            print(f"Warning: Vehicle with ID {v.id_user} cannot be charged {required_energy:.2f} kWh ({int(percent_leave_old)}%) within {int(parking_time)} minutes. At most {max_possible_energy:.2f} kWh ({int(percent_leave)}%) are possible.")
            v.percent_leave=percent_leave
            required_energy = (v.percent_leave-v.percent_arrive)/100*v.battery_size # in kWh
            v.energy_required = required_energy
            v.charge_duration= int(v.energy_required/v.charge_max*60)
            minduration = v.charge_duration

        # reduce max power if possible
        if(scheduling_parameters.reducemax):
            if(maxstationpower>20 and minduration<30 and parkduration>4*minduration):
                print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/4 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
                maxstationpower = maxstationpower/4
                minduration = minduration*4
            if(maxstationpower>15 and parkduration>2*minduration):
                print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/2 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
                maxstationpower = maxstationpower/2
                minduration = minduration*2

        # reduce power at the end if charging takes longer than 2 hours
        if(scheduling_parameters.flatten):
            if(minduration>=120):
                stationpower = [maxstationpower*1000]*(int(minduration*0.85)) # charge 70% of energy with max energy
                slopeduration = int(0.15*v.energy_required/maxstationpower*4/3*60)
                stationpower.extend([(maxstationpower-maxstationpower/2*t/slopeduration)*1000 for t in range(0,slopeduration)])
                duration = int(slopeduration+0.85*minduration)
                # check if the charging duration is still shorter than the parking time
                if(duration>parkduration):
                    stationpower = [maxstationpower*1000]*minduration
                else:
                    minduration = duration
            else:
                stationpower = [maxstationpower*1000]*minduration
        else:
            stationpower = [maxstationpower*1000]*minduration
        
        print(f"v.energy_required: {v.energy_required}, scheduled: {sum(stationpower)/60/1000:0.2f}")

        end_time = v.time_leave - timedelta(minutes=minduration)

        bestStartTime = None
        leastGridEnergy = float('inf')
        t = timestamp
        if(t==end_time):
            bestStartTime=t

        # find the optimal starting time of the charging process
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
            
            # allow 1 kWh energy from grid per vehicle
            if(scheduling_parameters.allowgrid):
                if gridEnergyUsed <= 1000:    
                    gridEnergyUsed=0

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
        consumer: Consumer = Consumer(v.id_user,powercurve)
        consumers.append(consumer)
        print("Added "+str(consumer.id_user)+" with starting time "+str(consumer.power.interval.time_start))

    return consumers

# overcharge consumers if excess renewable power is available
def overcharge_scheduling(consumers: List[Consumer], vehicles: List[Vehicle], solarProduction: Production, powerUsage: List[float], timestamp: datetime):
    simulationdate = datetime(timestamp.year,timestamp.month,timestamp.day)
    
    total_overcharge_power = [0.0]*24*60

    overpower_consumers: List[Consumer] = []
    overpower_consumers_: List[Consumer] = []

    for c in consumers: # check which consumers can use excess energy
        if(c.overpower.interval is None or c.overpower.interval.time_start > timestamp):
            c.overpower.power.clear()
            c.overpower.interval = None
            overpower_consumers.append(c)

    number_scheduled=0
    for c in overpower_consumers:
        id_user: str = c.id_user
        v: Vehicle = next(filter(lambda v: v.id_user == id_user, vehicles))
        total_energy = c.power.getEnergy()/1000 + (c.overpower.getEnergy()/1000 if c.overpower.interval is not None else 0)
        soc_charged = (v.battery_size*v.percent_arrive/100+total_energy)/v.battery_size
        soc_left = (1-soc_charged)
        energy_left = soc_left*v.battery_size*1000
        if(True or energy_left>2000): # only overcharge if more than 2kWh can be charged

            renewable_power = Production.renewable_available(solarProduction.production, np.add(powerUsage,total_overcharge_power))

            regular_end_index = int((c.power.interval.time_end.timestamp()-simulationdate.timestamp())/60)
            overpower_offset = int((c.overpower.interval.time_end.timestamp()-simulationdate.timestamp())/60) if c.overpower.interval is not None else 0
            lastRegularPower = 0
            if overpower_offset == 0:
                lastRegularPower = c.power.power[-1]
            else:
                lastRegularPower = c.overpower.power[-1]

            overcharge_start_index = regular_end_index
            overcharge_end_index = 0

            vehicle_leave_index = int((v.time_leave.timestamp()-simulationdate.timestamp())/60)

            overcharge_power = []
            for i in range(overcharge_start_index + overpower_offset,len(renewable_power)):
                overcharge_end_index = i

                not_leaving: bool = i<vehicle_leave_index 
                not_fully_charged: bool = energy_left-sum(overcharge_power)/60>0
                min_charging_power_possible: bool = renewable_power[i]>=1000

                if(not_leaving and not_fully_charged and min_charging_power_possible ):
    
                    charging_power = min(lastRegularPower,renewable_power[i])
                    if(i != overcharge_start_index and overcharge_power[i-1-overcharge_start_index] > 0):
                        charging_power = min(overcharge_power[i-1-overcharge_start_index],charging_power)

                    overcharge_power.append(charging_power)
                    total_overcharge_power[i]+=charging_power
                else:
                    break
            overcharge_interval = TimeInterval(simulationdate+timedelta(minutes=overcharge_start_index),simulationdate+timedelta(minutes=overcharge_end_index))
            if(overcharge_interval.intervalLength()<0):
                overcharge_interval = None
                overcharge_power.clear()

            overpower_consumers_.append(Consumer(c.id_user, c.power, PowerCurve(overcharge_power,overcharge_interval)))
            print(f"Overcharging: {c.id_user}: energy: {PowerCurve(overcharge_power,overcharge_interval).getEnergy()/1000:.2f} kWh")
            number_scheduled+=1

    # return all consumers
    for c in consumers:
        if c.id_user not in [o.id_user for o in overpower_consumers_]:
            overpower_consumers_.append(c)
            if(c.overpower.interval is not None):
                overpower_start_index = int((c.overpower.interval.time_start.timestamp()-simulationdate.timestamp())/60)
                total_overcharge_power = np.add(total_overcharge_power,[0]*(overpower_start_index)+c.overpower.power+[0]*(24*60-overpower_start_index-len(c.overpower.power)))
                print(f"Overcharging: {c.id_user}: energy: {c.overpower.getEnergy()/1000:.2f} kWh")
    return number_scheduled,overpower_consumers_, total_overcharge_power