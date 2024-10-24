import datetime

class Vehicle:
    def __init__(self, 
                 id_user: str, 
                 time_arrive: datetime, 
                 time_leave: datetime, 
                 percent_arrive: int, 
                 percent_leave: int, 
                 battery_size: float, 
                 charge_max: float):
        self.id_user: str = id_user
        self.time_arrive: datetime = time_arrive
        self.time_leave: datetime = time_leave
        self.percent_arrive: int = percent_arrive
        self.percent_leave: int = percent_leave
        self.battery_size: float = battery_size
        self.charge_max: float = charge_max

        self.energy_required: float = battery_size*(percent_leave-percent_arrive)/100 if (self.percent_leave>self.percent_arrive) else 0 
        self.charge_duration: int = int(self.energy_required/self.charge_max*60)

    def __str__(self) -> str:
        return (f"ID User: {self.id_user}\n"
                f"Time Arrive: {self.time_arrive}\n"
                f"Time Leave: {self.time_leave}\n"
                f"Percent Arrive: {self.percent_arrive}%\n"
                f"Percent Leave: {self.percent_leave}%\n"
                f"Battery Size: {self.battery_size} kWh\n"
                f"Max Charge Power: {self.charge_max} kW\n"
                f"Energy required: {self.energy_required} kWh\n"
                f"Charging duration: {int(self.charge_duration)} min\n")
