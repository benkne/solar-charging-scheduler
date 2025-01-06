from datetime import datetime, timedelta
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
    
    def timeInInterval(self, timestep: datetime) -> bool:
        if(timestep>=self.time_start and timestep<=self.time_end):
            return True
        return False
    
    def to_dict(self):
        return {
            "time_start": self.time_start.timestamp(),
            "time_end": self.time_end.timestamp()
        }
    
    @staticmethod
    def from_dict(data: dict) -> "TimeInterval":
        if data is None:
            return None
        
        if not data or "time_start" not in data or "time_end" not in data:
            raise ValueError("Invalid or missing interval data")

        if data["time_start"] is None or data["time_end"] is None:
            raise ValueError("time_start and time_end cannot be None")

        time_start = datetime.fromtimestamp(data["time_start"])
        time_end = datetime.fromtimestamp(data["time_end"])
        return TimeInterval(time_start, time_end)
    

    
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
    
    def getEnergy(self) -> float:
        if(self.power is None):
            return 0
        return sum(self.power)/60
    
    def to_dict(self):
        return {
            "power": self.power,
            "interval": self.interval.to_dict() if self.interval else None
        }
    
    @staticmethod
    def from_dict(data: dict) -> "PowerCurve":
        interval = TimeInterval.from_dict(data["interval"])
        return PowerCurve(
            power=data["power"],
            interval=interval
        )
    

    
class Consumer:
    def __init__(self, id_user: str, power: PowerCurve, overpower: PowerCurve = PowerCurve([],None)):
        self.id_user: str = id_user
        self.power: PowerCurve = power
        self.overpower: PowerCurve = overpower 

    def __str__(self) -> str:
        return (f"ID User: {self.id_user}\n"
                f"Total Power: {(sum(self.power.power)/60/1000):.2f} kWh (+{(sum(self.overpower.power)/60/1000 if self.overpower.power is not None else 0):.2f} kWh overcharge)\n"
                f"Time Start: {self.power.interval.time_start}\n"
                f"Time End: {self.power.interval.time_end}\n"
                f"Interval length: {self.power.interval.intervalLength()} min\n")
    
    def sort_consumers_by_start_time(consumers: List["Consumer"]) -> List["Consumer"]:
        return sorted(consumers, key=lambda consumer: consumer.power.interval.time_start)
    
    def sort_consumers_by_end_time(consumers: List["Consumer"]) -> List["Consumer"]:
        return sorted(
            consumers, 
            key=lambda consumer: max(
                consumer.power.interval.time_end.timestamp(), 
                consumer.overpower.interval.time_end.timestamp() if consumer.overpower.interval is not None else consumer.power.interval.time_end.timestamp()
            )
        )

    def vehicles_to_consumers(vehicles: List[Vehicle]) -> List["Consumer"]:
        consumers: list["Consumer"] = []
        for vehicle in vehicles:
            interval: TimeInterval = TimeInterval(vehicle.time_arrive,vehicle.time_arrive+timedelta(minutes=vehicle.charge_duration))
            powercurve: PowerCurve = PowerCurve([vehicle.charge_max*1000]*vehicle.charge_duration,interval)
            consumer: Consumer = Consumer(vehicle.id_user,powercurve)
            consumers.append(consumer)
        return consumers
    
    def unstarted_consumers(consumers: List["Consumer"], time: datetime) -> List[str]:
        consumer_ids = [c.id_user for c in consumers if c.power.interval.time_start>time]
        return consumer_ids
    
    def printAllStats(vehicles: List[Vehicle], consumers: List["Consumer"]) -> None:
        print('\n')
        requirement_missed = []
        for v in vehicles:
            print(f"User ID: {v.id_user}")
            print(f"Energy required: {v.energy_required:.1f} kWh")
            print(f"SoC start: {v.percent_arrive:.0f}%")
            print(f"SoC required: {v.percent_leave:.0f}%")
            consumer = next((c for c in consumers if c.id_user == v.id_user), None)
            if(consumer==None):
                print("Vehicle not scheduled.")
                print(f"Energy charged: 0 kWh")
            else:
                total_energy = consumer.power.getEnergy()/1000+(consumer.overpower.getEnergy()/1000 if consumer.overpower is not None else 0)
                soc_charged = (v.battery_size*v.percent_arrive/100+total_energy)/v.battery_size
                print(f"SoC charged: {soc_charged*100:.0f}%")
                print(f"Energy charged: {total_energy:.1f} kWh")
                print(f"Energy missing: {v.energy_required-total_energy:.2f}kWh")
                print(f"Overpower energy: {consumer.overpower.getEnergy()/1000:.2f}kWh")
                if(v.energy_required-total_energy>v.charge_max/60):
                    requirement_missed.append(consumer.id_user)
            print("------------------------")
        if(len(requirement_missed)==0):
            print("All vehicles were charged successfully.")
        else:
            print(f"Required SoC missed for vehicles: {requirement_missed}")    

    def to_dict(self):
        return {
            "id_user": self.id_user,
            "power": self.power.to_dict(),
            "overpower": self.overpower.to_dict()
        }

    @staticmethod
    def consumers_to_dict(consumers: List["Consumer"]):
        return [consumer.to_dict() for consumer in consumers]
    
    @staticmethod
    def from_dict(data: dict) -> "Consumer":
        power = PowerCurve.from_dict(data["power"])
        overpower = PowerCurve.from_dict(data["overpower"])
        
        return Consumer(
            id_user=data["id_user"],
            power=power,
            overpower=overpower
        )

    @staticmethod
    def consumers_from_dict(data: List[dict]) -> List["Consumer"]:
        return [Consumer.from_dict(consumer_data) for consumer_data in data]



class Segment:
    def __init__(self, id_user: str, interval: TimeInterval, power: float, basePower: float):
        self.id_user = id_user
        self.interval = interval
        self.power = power
        self.basePower = basePower

    def powerOfTimestep(self, timestep: datetime) -> float:
        if(self.interval.timeInInterval(timestep)):
            return self.power
        return 0



class ConsumerPlot:
    consumerSegments: List[Segment] = []

    def __init__(self, consumers: List[Consumer]) -> None:
        for consumer in consumers:
            self.createSegments(consumer, consumer.power,consumer.power.interval.time_start)
            if(consumer.overpower.interval is not None):
                self.createSegments(consumer, consumer.overpower,consumer.overpower.interval.time_start)
                
    def totalTimestepPower(self, timestep: datetime) -> float:
        totalPower = 0
        for segment in self.consumerSegments:
            totalPower = totalPower+segment.powerOfTimestep(timestep)
        return totalPower
    
    def createSegments(self,consumer: Consumer, powerCurve: PowerCurve, startTime) -> None:
        basePower = self.totalTimestepPower(startTime)
        time = startTime
        while time <= powerCurve.interval.time_end:
            currentPower = self.totalTimestepPower(time)
            if currentPower != basePower or powerCurve.getPower(time) != powerCurve.getPower(time+timedelta(minutes=1)):
                self.consumerSegments.append(Segment(
                    consumer.id_user,
                    TimeInterval(startTime, time-timedelta(minutes=1)), 
                    powerCurve.getPower(startTime), 
                    basePower
                ))
                basePower = currentPower
                startTime = time

            if time == powerCurve.interval.time_end:
                self.consumerSegments.append(Segment(
                    consumer.id_user,
                    TimeInterval(startTime, time-timedelta(minutes=1)), 
                    powerCurve.getPower(startTime), 
                    basePower
                ))

            time += timedelta(minutes=1)
            
    def visualize(self,ax) -> None:
        def color(string: str):
            random.seed(string)
            return (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))

        for s in self.consumerSegments:
            time_start = s.interval.time_start
            power_start = s.basePower
            width = timedelta(minutes=s.interval.intervalLength())+timedelta(minutes=1)
            height = s.power
            randomcolor=color(s.id_user)
            rect = patches.Rectangle((time_start, power_start), 
                                    width, 
                                    height, 
                                    linewidth=1, 
                                    facecolor=randomcolor)
            ax.add_patch(rect)