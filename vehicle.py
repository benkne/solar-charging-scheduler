import datetime
from typing import List, Optional

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

        self.energy_required: float = max(battery_size*(percent_leave-percent_arrive)/100,0)
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

    def display_vehicles(vehicles: List["Vehicle"]) -> None:
        if vehicles:
            for vehicle in vehicles:
                print(vehicle)
                print("-" * 40)
        else:
            print("No vehicles to display.")

    def sort_vehicles_by_arrive_time(vehicles: List["Vehicle"]) -> List["Vehicle"]:
        return sorted(vehicles, reverse=False, key=lambda vehicle: vehicle.time_arrive)
    
    def sort_vehicles_by_max_power(vehicles: List["Vehicle"]) -> List["Vehicle"]:
        return sorted(vehicles, reverse=True, key=lambda vehicle: vehicle.charge_max)

    def create_vehicles(data: Optional[List[dict]], simulationdate: datetime) -> List["Vehicle"]:
        vehicles: List[Vehicle] = []
        if data:
            for entry in data:
                time_arrive: datetime = datetime.datetime(simulationdate.year,
                                                        simulationdate.month,
                                                        simulationdate.day,
                                                        int(entry['time_arrive'][:2]),
                                                        int(entry['time_arrive'][3:]))
                time_leave: datetime = datetime.datetime(simulationdate.year,
                                                        simulationdate.month,
                                                        simulationdate.day,
                                                        int(entry['time_leave'][:2]),
                                                        int(entry['time_leave'][3:]))
                
                id_user=entry['id_user']
                percent_arrive=entry['percent_arrive']
                percent_leave=entry['percent_leave']
                battery_size=entry['battery_size']
                charge_max=entry['charge_max']
                required_energy = (percent_leave-percent_arrive)/100*battery_size # in kWh
                parking_time = int((time_leave-time_arrive).total_seconds())/60 # in minutes

                max_possible_energy = parking_time/60*charge_max
                if(max_possible_energy<required_energy): # check if the desired SoC can possibly be reached bevore leaving
                    percent_leave_old = percent_leave
                    percent_leave = max_possible_energy*100/battery_size+percent_arrive # recalculate SoC_leave so that the vehicle can be charged within parking time
                    print(f"Warning: Vehicle with ID {id_user} cannot be charged {required_energy:.2f} kWh ({int(percent_leave_old)}%) within {int(parking_time)} minutes. At most {max_possible_energy:.2f} kWh ({int(percent_leave)}%) are possible.")
            
                vehicle = Vehicle(
                    id_user=id_user,
                    time_arrive=time_arrive,
                    time_leave=time_leave,
                    percent_arrive=percent_arrive,
                    percent_leave=percent_leave,
                    battery_size=battery_size,
                    charge_max=charge_max
                )
                vehicles.append(vehicle)
        return vehicles
    
    def vehicles_arriving(vehicles: List["Vehicle"],time: datetime) -> List["Vehicle"]:
        return [v for v in vehicles if v.time_arrive==time]