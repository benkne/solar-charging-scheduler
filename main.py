import json
import energy_charts_api
from forecast_power import Forecast
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
from typing import List, Optional

from vehicle import Vehicle
from forecast_power import Forecast
from renewable_production import Production
from consumer_model import ConsumerPlot
import dynamic_scheduling
import numpy as np

# ---------------- constants ---------------- #

simulationdate = datetime.now() + timedelta(days=1)
simulationdate = datetime(simulationdate.year,simulationdate.month,simulationdate.day)

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
    

def visualize_forecast(forecast: Forecast):
    plt.figure(figsize=(10, 6))
    forecast.visualize(plt)

    plt.title('Solar Power Forecast', fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    plt.tight_layout()  
    plt.show()

def vehicles_arriving(vehicles: List[Vehicle],time: datetime) -> List[Vehicle]:
    return [v for v in vehicles if v.time_arrive==time]

def generate_time_vector(date: datetime):
    vector = []
    time = date
    while time < date+timedelta(days=1):
        vector.append(time)
        time=time+timedelta(minutes=1)
    return vector

# ---------------- main ---------------- #

def main():
    file_path = 'test\\testdata.json'
    
    print("# Reading vehicle data from file...")

    data = read_json(file_path)
    
    vehicles: List[Vehicle] = Vehicle.create_vehicles(data,simulationdate)

    print("# Making forecast API request...")

    forecast: Forecast = energy_charts_api.api_request()
    forecast.scale(peakSolarPower, peakPowerAustria)

    solarProduction = Production(forecast,simulationdate) 

    print("# Preparing vehicle data...")

    vehicles = Vehicle.sort_vehicles_by_arrive_time(vehicles)
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

    print("\n------- Simulation starting -------")

    consumers = []
    powerUsage = [0.0]*24*60

    time_vector = generate_time_vector(simulationdate)
    for t in time_vector:
        arriving_vehicles: List[Vehicle] = []

        arriving_vehicles = vehicles_arriving(vehicles,t)
        if(len(arriving_vehicles) != 0):
            print(f"{t}: "+"Arriving vehicles: "+str([v.id_user for v in arriving_vehicles]))

            renewable_available = solarProduction.production
            renewable_available = np.subtract(renewable_available,powerUsage)
            renewable_available = np.maximum(renewable_available,0)

            added_consumers,updated_powerUsage = dynamic_scheduling.greedy(arriving_vehicles, simulationdate, renewable_available)
            #added_consumers,updated_powerUsage = dynamic_scheduling.differential_evolution(arriving_vehicles, simulationdate, renewable_available)

            consumers.extend(added_consumers)
            powerUsage = np.add(powerUsage,updated_powerUsage)

    print("------- Simulation ended -------\n")

    total_consumed_energy =(sum(powerUsage)/60/1000)
    grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000)
    unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
    ### print stats (finished) ###
    print(f"Total energy consumed: {total_consumed_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% grid, {((1-grid_energy/total_consumed_energy)*100):.0f}% solar)")
    print(f"Grid energy used: {grid_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% from total energy)")
    print(f"Solar energy unused: {unused_solar_energy:.2f} kWh ({(unused_solar_energy/solar_energy*100):.0f}% from total solar energy)")

    #Consumer.printAllStats(allvehicles,consumers)

    ### visualisation ###

    plt.figure(figsize=(10, 6))

    solarProduction.visualize(plt)
    #forecast.visualizeGauss(plt,simulationdate)
    forecast.visualizeSin2(plt,simulationdate)
    
    plt.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black',label="total consumed power")

    plt.step(time_vector,[max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))],where='post',label="remaining solar power")
    plt.step(time_vector,[max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))], color='r',where='post',label="power drawn from grid")

    plt.title('Solar forecast and BEV consumption - {}kWp'.format(peakSolarPower/1000), fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    ax = plt.gca()

    consumerPlot: ConsumerPlot = ConsumerPlot(consumers)
    consumerPlot.visualize(ax)

    plt.xlim(datetime(simulationdate.year,simulationdate.month,simulationdate.day,6,0),datetime(simulationdate.year,simulationdate.month,simulationdate.day,17,59))
    plt.ylim((0,forecast.getDailyPeak(simulationdate)*1.2))

    plt.legend(loc="upper left")

    plt.tight_layout()  
    plt.show()
if __name__ == "__main__":
    main()