import datetime

class TimeInterval:
    def __init__(self, time_start: datetime, time_end: datetime) -> None:
        self.time_start: datetime = time_start
        self.time_end: datetime = time_end

    def intervalLength(self) -> int:
        return int((self.time_end-self.time_start).total_seconds() / 60.0)
    
class PowerCurve:
    def __init__(self, power: list[float], interval: TimeInterval) -> None:
        self.power: list[float] = power
        self.interval: TimeInterval = interval
    
    def getPower(self, time: datetime):
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
                f"PowerCurve: {self.power.power}\n"
                f"Time Start: {self.interval.time_start}\n"
                f"Time End: {self.interval.time_end}\n"
                f"Interval length: {self.interval.intervalLength()} min\n")

class CurrentPower:
    def __init__(self, timestamp: datetime, consumers: list[Consumer]) -> None:
        self.timestamp: datetime = timestamp
        self.consumers: list[Consumer] = consumers
        totalpower = 0
        for c in consumers:
            totalpower = totalpower+c.power.getPower(timestamp)
        self.power: float = totalpower

    def addConsumer(self, consumer: Consumer):
        self.consumers.append(consumer)
        self.power = self.power+consumer.power.getPower(self.timestamp)