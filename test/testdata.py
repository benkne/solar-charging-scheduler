import json
from typing import List, Optional
import sys
import os
import random
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

simulationdate = datetime.datetime.now() + datetime.timedelta(days=1)

from vehicle import Vehicle
from consumer_model import TimeInterval, PowerCurve, Consumer, CurrentPower

import energy_charts_api
from forecast_power import Forecast

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
            vehicle = Vehicle(
                id_user=entry['id_user'],
                time_arrive=time_arrive,
                time_leave=time_leave,
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

def vehicles_to_consumers(vehicles: List[Vehicle]) -> List[Consumer]:
    consumers: list[Consumer] = []
    for vehicle in vehicles:
        interval: TimeInterval = TimeInterval(vehicle.time_arrive,vehicle.time_arrive+datetime.timedelta(minutes=vehicle.charge_duration))
        powercurve: PowerCurve = PowerCurve([vehicle.charge_max*1000]*vehicle.charge_duration,interval)
        consumer: Consumer = Consumer(vehicle.id_user,powercurve,interval)
        consumers.append(consumer)
    return consumers

def sort_consumers_by_start_time(consumers: List[Consumer]) -> List[Consumer]:
    return sorted(consumers, key=lambda consumer: consumer.interval.time_start)

def main():
    file_path = 'test\\testdata.json'
    
    data = read_json_from_file(file_path)
    
    vehicles: List[Vehicle] = create_vehicles(data)
    display_vehicles(vehicles)

    consumers = vehicles_to_consumers(vehicles)
    consumers = sort_consumers_by_start_time(consumers)

    starttimes = []
    endtimes = []
    for c in consumers:
        starttime = c.interval.time_start
        endtime = c.interval.time_end
        starttimes.append(starttime)
        endtimes.append(endtime)
    starttimes.sort()
    endtimes.sort()
    firststart = starttimes[0]
    lastend = endtimes[-1]

    time = firststart
    currentpowers = []
    while time <= lastend:
        currentpower: CurrentPower = CurrentPower(time,consumers)
        currentpowers.append(currentpower)
        time = time+datetime.timedelta(minutes=1)


    plt.figure(figsize=(10, 6))

    forecast: Forecast = energy_charts_api.api_request()
    forecast.scale(500_000, 6_395_000_000)
    forecast.visualize(plt)

    forecast.visualizeGauss(plt,simulationdate)
    
    plt.plot([currentpower.timestamp for currentpower in currentpowers], [currentpower.power for currentpower in currentpowers], marker='o', linestyle='-', color='r')

    plt.title('Power consumption', fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    ax = plt.gca()

    poweroffset = 0
    for c in consumers:
        time_start = c.interval.time_start
        power_start = poweroffset  
        width = datetime.timedelta(minutes=c.interval.intervalLength())
        height = c.power.getPower(c.interval.time_start) 
        randomcolor = (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
        rect = patches.Rectangle((time_start, power_start), 
                                 width, 
                                 height, 
                                 linewidth=1, 
                                 facecolor=randomcolor)
        ax.add_patch(rect)
        poweroffset = poweroffset+c.power.getPower(time_start)

    plt.ylim(0, poweroffset)
    plt.xlim(datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,0,0),datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,23,59))
    
    plt.tight_layout()  
    plt.show()

if __name__ == "__main__":
    main()