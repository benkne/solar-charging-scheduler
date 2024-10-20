import json
from typing import List, Optional
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from vehicle import Vehicle

def read_json_from_file(file_path: str) -> Optional[List[dict]]:
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}.")
        return None

def create_vehicles(data: Optional[List[dict]]) -> List[Vehicle]:
    vehicles: List[Vehicle] = []
    if data:
        for entry in data:
            vehicle = Vehicle(
                id_user=entry['id_user'],
                time_arrive=entry['time_arrive'],
                time_leave=entry['time_leave'],
                percent_arrive=entry['percent_arrive'],
                percent_leave=entry['percent_leave'],
                battery_size=entry['battery_size'],
                charge_max=entry['charge_max']
            )
            vehicles.append(vehicle)
    return vehicles

def display_vehicles(vehicles: List[Vehicle]) -> None:
    if vehicles:
        for vehicle in vehicles:
            print(vehicle)
            print("-" * 40)
    else:
        print("No vehicles to display.")

def main():
    file_path = 'test\\testdata.json'
    
    data = read_json_from_file(file_path)
    
    vehicles = create_vehicles(data)

    display_vehicles(vehicles)

if __name__ == "__main__":
    main()