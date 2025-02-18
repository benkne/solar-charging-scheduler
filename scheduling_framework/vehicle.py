from datetime import datetime
from typing import List, Optional

# the Vehicle class defines the BEV parameters
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

    # print all list of vehicles to command line
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
    
    def sort_vehicles_by_energy(vehicles: List["Vehicle"]) -> List["Vehicle"]:
        return sorted(vehicles, reverse=True, key=lambda vehicle: vehicle.energy_required)

    # creates vehicles from dictionary
    def create_vehicles(data: Optional[List[dict]], simulationdate: datetime) -> List["Vehicle"]:
        vehicles: List[Vehicle] = []
        if data:
            for entry in data:
                time_arrive: datetime = datetime(simulationdate.year,
                                                        simulationdate.month,
                                                        simulationdate.day,
                                                        int(entry['time_arrive'][:2]),
                                                        int(entry['time_arrive'][3:]))
                time_leave: datetime = datetime(simulationdate.year,
                                                        simulationdate.month,
                                                        simulationdate.day,
                                                        int(entry['time_leave'][:2]),
                                                        int(entry['time_leave'][3:]))
                
                id_user=str(entry['id_user'])# +"_"+entry['time_arrive'][:2]+entry['time_arrive'][3:] # make user id unique by extending the id by the the arrive time
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
    
    # returns a list of vehicles arriving at the given timestamp 
    def vehicles_arriving(vehicles: List["Vehicle"],time: datetime) -> List["Vehicle"]:
        return [v for v in vehicles if v.time_arrive==time]
    
    def to_dict(self):
        return {
            "id_user": self.id_user,
            "time_arrive": self.time_arrive.timestamp(),
            "time_leave": self.time_leave.timestamp(),
            "percent_arrive": self.percent_arrive,
            "percent_leave": self.percent_leave,
            "battery_size": self.battery_size,
            "charge_max": self.charge_max,
            "energy_required": self.energy_required,
            "charge_duration": self.charge_duration
        }

    @staticmethod
    def vehicles_to_dict(vehicles: List["Vehicle"]):
        return [vehicle.to_dict() for vehicle in vehicles]
    
    @staticmethod
    def from_dict(data: dict) -> "Vehicle":
        time_arrive = datetime.fromtimestamp(data["time_arrive"])
        time_leave = datetime.fromtimestamp(data["time_leave"])
        
        return Vehicle(
            id_user=data["id_user"],
            time_arrive=time_arrive,
            time_leave=time_leave,
            percent_arrive=data["percent_arrive"],
            percent_leave=data["percent_leave"],
            battery_size=data["battery_size"],
            charge_max=data["charge_max"]
        )

    @staticmethod
    def vehicles_from_dict(data: List[dict]) -> List["Vehicle"]:
        return [Vehicle.from_dict(vehicle_data) for vehicle_data in data]
    
# return a single vehicle to add it to the list of vehicles
def add_vehicle(simulationdate: datetime, vehicles: List[Vehicle], vehicle: str):
    if(vehicle is None):
        print("Error: Vehicle not set!")
        exit()
    vehicle_parameters = vehicle.split(',')

    id_user = vehicle_parameters[0]
    if any(vehicle.id_user == id_user for vehicle in vehicles):
        print("Error: A vehicle with this User ID already exists. Please enter a unique User ID.")
        exit()

    try:
        time_arrive_str = vehicle_parameters[1]
        time_arrive_str = time_arrive_str.split(":")
        time_arrive: datetime = datetime(simulationdate.year,
                                    simulationdate.month,
                                    simulationdate.day,
                                    int(time_arrive_str[0]),
                                    int(time_arrive_str[1]))
        if vehicles and any(time_arrive < vehicle.time_arrive for vehicle in vehicles):
            print("Error: Arrival time must be after the arrival times of all other vehicles.")
            exit()
            
    except ValueError:
        print("Error: Invalid format. Please enter the date and time in the format HH:MM.")
        exit()

    try:
        time_leave_str = vehicle_parameters[2]
        time_leave_str = time_leave_str.split(":")
        time_leave: datetime = datetime(simulationdate.year,
                                    simulationdate.month,
                                    simulationdate.day,
                                    int(time_leave_str[0]),
                                    int(time_leave_str[1]))
        if time_leave <= time_arrive:
            print("Error: Leave time must be after arrival time.")
            exit()
    except ValueError:
        print("Error: Invalid format. Please enter the date and time in the format HH:MM.")
        exit()

    try:
        percent_arrive = float(vehicle_parameters[3])
        if not (0 <= percent_arrive <= 100):
            print("Error: Please enter a value between 0 and 100.")
            exit()
    except ValueError:
        print("Error: Invalid input. Please enter an integer.")
        exit()

    try:
        percent_leave = float(vehicle_parameters[4])
        if not (0 <= percent_arrive <= 100):
            print("Error: Please enter a value between 0 and 100.")
            exit()
    except ValueError:
        print("Error: Invalid input. Please enter an integer.")
        exit()

    try:
        battery_size = float(vehicle_parameters[5])
        if battery_size <= 0:
            print("Error: Please enter a positive number.")
            exit()
    except ValueError:
        print("Error: Invalid input. Please enter a numeric value.")
        exit()

    try:
        charge_max = float(vehicle_parameters[6])
        if charge_max <= 0:
            print("Error: Please enter a positive number.")
            exit()
    except ValueError:
        print("Error: Invalid input. Please enter a numeric value.")
        exit()

    return Vehicle(id_user, time_arrive, time_leave, percent_arrive, percent_leave, battery_size, charge_max)

