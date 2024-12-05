from typing import List, Tuple
from datetime import datetime, timedelta

from vehicle import Vehicle
from consumer_model import TimeInterval, PowerCurve, Consumer

class SchedulingParameters:
    def __init__(self,
                 flatten = False,
                 overcharge = True,
                 reducemax = True
                ):
        self.flatten=flatten
        self.overcharge=overcharge
        self.reducemax=reducemax

    def parseSchedulingParameters(self, string: str):
        parameter_strings = string.split(",")
        for string in parameter_strings:
            keyval = string.split("=")
            key = keyval[0]
            val = keyval[1]
            if(key=='flatten'):
                self.flatten = val.lower() == 'true'
            elif(key=='overcharge'):
                self.overcharge = val.lower() == 'true'
            elif(key=='reducemax'):
                self.reducemax = val.lower() == 'true'

    def to_dict(self):
        return {
            "flatten": self.flatten,
            "overcharge": self.overcharge,
            "reducemax": self.reducemax
        }
    
    @staticmethod
    def from_dict(data: dict) -> "SchedulingParameters":
        return SchedulingParameters(
            flatten=data.get("flatten", False),
            overcharge=data.get("overcharge", True),
            reducemax=data.get("reducemax", True)
        )

def vehiclepower(v: Vehicle, startTime: datetime, t: datetime) -> int: # returns the power from vehicle v during time t when the charging starts at time startTime
    if startTime <= t < startTime + timedelta(minutes=v.charge_duration):
        return v.charge_max*1000
    return 0
    
def greedy(scheduling_parameters: SchedulingParameters, vehicles: List[Vehicle], simulationdate: datetime, production: List[float]) -> Tuple[List[Consumer], List[float]]:
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

        if(scheduling_parameters.reducemax):
        # reduce max power if possible
            if(maxstationpower>20 and minduration<30 and parkduration>4*minduration):
                print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/4 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
                maxstationpower = maxstationpower/4
                minduration = minduration*4
            if(maxstationpower>15 and parkduration>2*minduration):
                print(f"INFO: vehicle with ID {v.id_user} can be charged with 1/2 max vehicle power. Parking: {parkduration} minutes. Required {minduration} minutes.")
                maxstationpower = maxstationpower/2
                minduration = minduration*2

        if(scheduling_parameters.flatten):
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

        if(scheduling_parameters.overcharge):
            print("Overcharging vehicle if possible.")

        interval: TimeInterval = TimeInterval(bestStartTime,bestStartTime+timedelta(minutes=minduration))
        powercurve: PowerCurve = PowerCurve(stationpower,interval)
        consumer: Consumer = Consumer(v.id_user,powercurve)
        consumers.append(consumer)
        print("Added "+str(consumer.id_user)+" with starting time "+str(consumer.power.interval.time_start))

    return consumers,powerUsage