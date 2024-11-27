import json
from typing import List, Optional
import sys
import os
import datetime
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vehicle import Vehicle
from forecast_power import Forecast
from consumer_model import Consumer, ConsumerPlot
from renewable_production import Production

import energy_charts_api
import dynamic_scheduling

# ---------------- constants ---------------- #

simulationdate = datetime.datetime.now() + datetime.timedelta(days=1)
simulationdate = datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day)

peakSolarPower = 300_000 # 300 kWp
peakPowerAustria = 4_196_000_000 # 4196 MW Spitzenwert im Jahr 2024 (juni) / energy-charts.info

# ---------------- functions ---------------- #

def read_json(file_path: str) -> Optional[List[dict]]:
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

# ---------------- main ---------------- #

def main():
    file_path = 'test\\testdata.json'
    
    data = read_json(file_path)
    
    vehicles: List[Vehicle] = Vehicle.create_vehicles(data,simulationdate)

    forecast: Forecast = energy_charts_api.api_request()
    forecast.scale(peakSolarPower, peakPowerAustria)

    solarProduction = Production(forecast,simulationdate)    

    vehicles = vehicles[:10] # reduce vehicle count for faster testing
    allvehicles = vehicles
    for v in vehicles:
        if v.energy_required==0: 
            vehicles.remove(v) # remove vehicles with 0 energy required
            print(f"Info: Removed vehicle with ID {v.id_user} because it does not require charging.")

    ### print stats (starting) ###
    required_energy = sum([v.energy_required for v in vehicles])
    solar_energy = (solarProduction.getEnergy()/1000)
    print(f"Starting scheduling process for {len(vehicles)} vehicles.")
    print(f"Total energy required: {required_energy:.2f} kWh")
    print(f"Total solar energy available (prediction): {solar_energy:.2f} kWh")
    if(required_energy>solar_energy):
        print("Warning: There is less solar power available than required. Power from the grid is necessary!")

    ### scheduling algorithm ###
    consumers,powerUsage = dynamic_scheduling.greedy(vehicles, simulationdate, solarProduction)
    #consumers,powerUsage = dynamic_scheduling.differential_evolution(vehicles, simulationdate, solarProduction)

    ### print stats (finished) ###
    print('\n')
    print(f"Total energy consumed: {(sum(powerUsage.values())/60/1000):.2f} kWh")

    Consumer.printAllStats(allvehicles,consumers)

    ### visualisation ###

    plt.figure(figsize=(10, 6))

    solarProduction.visualize(plt)
    #forecast.visualizeGauss(plt,simulationdate)
    forecast.visualizeSin2(plt,simulationdate)
    
    plt.step(list(powerUsage.keys()), list(powerUsage.values()), where='post', marker='', linestyle='-', color='black',label="total consumed power")

    plt.step(list(powerUsage.keys()),[max(solarProduction.production[i]-list(powerUsage.values())[i],0) for i in range(len(powerUsage))],where='post',label="remaining solar power")
    plt.step(list(powerUsage.keys()),[max(-(solarProduction.production[i]-list(powerUsage.values())[i]),0) for i in range(len(powerUsage))], color='r',where='post',label="power drawn from grid")
    #plt.step(list(powerUsage.keys()),[solarProduction.production[i] for i in range(len(powerUsage))],where='post')


    plt.title('Solar forecast and BEV consumption - {}kWp'.format(peakSolarPower/1000), fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    ax = plt.gca()

    consumerPlot: ConsumerPlot = ConsumerPlot(consumers)
    consumerPlot.visualize(ax)

    plt.xlim(datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,6,0),datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,17,59))
    plt.ylim((0,forecast.getDailyPeak(simulationdate)*1.2))

    plt.legend(loc="upper left")

    plt.tight_layout()  
    plt.show()

if __name__ == "__main__":
    main()