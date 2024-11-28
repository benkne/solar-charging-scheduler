import datetime
from typing import List
import random
import matplotlib.patches as patches
from vehicle import Vehicle

class TimeInterval:
    def __init__(self, time_start: datetime, time_end: datetime) -> None:
        self.time_start: datetime = time_start
        self.time_end: datetime = time_end

    def intervalLength(self) -> int:
        return int((self.time_end-self.time_start).total_seconds() / 60.0)
    
    def timeInInterval(self, timestep: datetime.datetime) -> bool:
        if(timestep>=self.time_start and timestep<=self.time_end):
            return True
        return False
    
class PowerCurve:
    def __init__(self, power: list[float], interval: TimeInterval) -> None:
        self.power: list[float] = power
        self.interval: TimeInterval = interval
    
    def getPower(self, time: datetime) -> float:
        if(time<self.interval.time_start or time>self.interval.time_end):
            return 0
        minutes_diff = int((time - self.interval.time_start).total_seconds() / 60.0)
        if minutes_diff<0 or minutes_diff>=self.interval.intervalLength():
            return 0
        return self.power[minutes_diff]
    
class Consumer:
    def __init__(self, id_user: str, power: PowerCurve, interval: TimeInterval):
        self.id_user: str = id_user
        self.power: PowerCurve = power
        self.interval: TimeInterval = interval

    def __str__(self) -> str:
        return (f"ID User: {self.id_user}\n"
                f"Total Power: {(sum(self.power.power)/60/1000):.2f} kWh\n"
                f"Time Start: {self.interval.time_start}\n"
                f"Time End: {self.interval.time_end}\n"
                f"Interval length: {self.interval.intervalLength()} min\n")
    
    def sort_consumers_by_start_time(consumers: List["Consumer"]) -> List["Consumer"]:
        return sorted(consumers, key=lambda consumer: consumer.interval.time_start)
    
    def vehicles_to_consumers(vehicles: List[Vehicle]) -> List["Consumer"]:
        consumers: list["Consumer"] = []
        for vehicle in vehicles:
            interval: TimeInterval = TimeInterval(vehicle.time_arrive,vehicle.time_arrive+datetime.timedelta(minutes=vehicle.charge_duration))
            powercurve: PowerCurve = PowerCurve([vehicle.charge_max*1000]*vehicle.charge_duration,interval)
            consumer: Consumer = Consumer(vehicle.id_user,powercurve,interval)
            consumers.append(consumer)
        return consumers
    
    def printAllStats(vehicles: List[Vehicle], consumers: List["Consumer"]) -> None:
        print('\n')
        for v in vehicles:
            consumer = next((c for c in consumers if c.id_user == v.id_user), None)
            if(consumer==None):
                print(v)
                print("Vehicle not scheduled.")
            else:
                print(v)
                print(consumer)
            print("------------------------")

class Segment:
    def __init__(self, id_user: str, interval: TimeInterval, power: float, basePower: float):
        self.id_user = id_user
        self.interval = interval
        self.power = power
        self.basePower = basePower

    def powerOfTimestep(self, timestep: datetime.datetime) -> float:
        if(self.interval.timeInInterval(timestep)):
            return self.power
        return 0


class ConsumerPlot:
    consumerSegments: List[Segment] = []

    def __init__(self, consumers: List[Consumer]) -> None:
        for consumer in consumers:
            self.createSegments(consumer,consumer.interval.time_start)
                
    def totalTimestepPower(self, timestep: datetime.datetime) -> float:
        totalPower = 0
        for segment in self.consumerSegments:
            totalPower = totalPower+segment.powerOfTimestep(timestep)
        return totalPower
    
    def createSegments(self,consumer,startTime) -> None:
        basePower = self.totalTimestepPower(startTime)
        time = startTime
        while time <= consumer.interval.time_end:
            currentPower = self.totalTimestepPower(time)
            if currentPower != basePower or consumer.power.getPower(time) != consumer.power.getPower(time+datetime.timedelta(minutes=1)):
                self.consumerSegments.append(Segment(
                    consumer.id_user,
                    TimeInterval(startTime, time-datetime.timedelta(minutes=1)), 
                    consumer.power.getPower(startTime), 
                    basePower
                ))
                basePower = currentPower
                startTime = time

            if time == consumer.interval.time_end:
                self.consumerSegments.append(Segment(
                    consumer.id_user,
                    TimeInterval(startTime, time-datetime.timedelta(minutes=1)), 
                    consumer.power.getPower(startTime), 
                    basePower
                ))

            time += datetime.timedelta(minutes=1)
            
    def visualize(self,ax) -> None:
        for s in self.consumerSegments:
            time_start = s.interval.time_start
            power_start = s.basePower
            width = datetime.timedelta(minutes=s.interval.intervalLength())+datetime.timedelta(minutes=1)
            height = s.power
            random.seed(s.id_user)
            randomcolor = (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
            rect = patches.Rectangle((time_start, power_start), 
                                    width, 
                                    height, 
                                    linewidth=1, 
                                    facecolor=randomcolor)
            ax.add_patch(rect)