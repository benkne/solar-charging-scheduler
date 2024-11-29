import json
import csv
import energy_charts_api
from forecast_power import Forecast
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
from typing import List, Optional

from vehicle import Vehicle
from forecast_power import Forecast
from renewable_production import Production
from consumer_model import Consumer, ConsumerPlot
import dynamic_scheduling
import numpy as np
import argparse

class SimulationParameters:
    def __init__(self,
                 testdatapath = 'test\\testdata.json',
                 resultpath = 'results\\result.csv',
                 exportresults = False,
                 hideresults = False,
                 simulationdate = datetime.now() + timedelta(days=1),
                 peakSolarPower = 300_000, # 300 kWp
                 peakPowerForecast = 4_196_000_000, # 4196 MW Spitzenwert im Jahr 2024 (juni) / energy-charts.info
                 forecastapi = "https://api.energy-charts.info/public_power_forecast?country=at&production_type=solar&forecast_type=current"
                ):
        self.testdatapath = testdatapath
        self.resultpath = resultpath
        self.exportresults = exportresults
        self.hideresults = hideresults
        self.simulationdate = datetime(simulationdate.year,simulationdate.month,simulationdate.day)
        self.peakSolarPower = peakSolarPower
        self.peakPowerForecast = peakPowerForecast
        self.forecastapi = forecastapi

# ---------------- functions ---------------- #

def read_json(file_path: str) -> Optional[List[dict]]:
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        exit()
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}.")
        exit()

def csv_write(file_path: str, data) -> None:
    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(data)
    print(f"Results written to {file_path}.")

def generate_time_vector(date: datetime):
    vector = []
    time = date
    while time < date+timedelta(days=1):
        vector.append(time)
        time=time+timedelta(minutes=1)
    return vector

def remove_consumer_from_powerUsage(simulationdate: datetime, powerUsage: List[float], consumer: Consumer) -> List[float]:
    t = simulationdate
    i=0
    while t<simulationdate+timedelta(days=1):
        powerUsage[i]-=consumer.power.getPower(t)
        t=t+timedelta(minutes=1)
        i+=1
    return powerUsage

# ---------------- simulation ---------------- #

def simulate(simulation_parameters: SimulationParameters):

    simulationdate = simulation_parameters.simulationdate

    exportdata=[]

    print("# Reading vehicle data from file...")
    data = read_json(simulation_parameters.testdatapath)
    vehicles: List[Vehicle] = Vehicle.create_vehicles(data,simulationdate)

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast,simulationdate) 

    print("# Preparing vehicle data...")
    vehicles = Vehicle.sort_vehicles_by_arrive_time(vehicles)
    allvehicles = vehicles[:]

    vehicles_ = []
    for v in vehicles:
        if v.energy_required>0:
            vehicles_.append(v)
        else:
            print(f"Info: Removed vehicle with ID {v.id_user} because it does not require charging.")
    vehicles = vehicles_

    print("Starting information:")
    required_energy = sum([v.energy_required for v in vehicles])
    solar_energy = (solarProduction.getEnergy()/1000)
    print(f"Starting scheduling process for {len(vehicles)} vehicles.")
    print(f"Total energy required: {required_energy:.2f} kWh")
    print(f"Total solar energy available (prediction): {solar_energy:.2f} kWh")
    if(required_energy>solar_energy):
        print("Warning: There is less solar power available than required. Power from the grid is necessary!")

    exportdata.append(simulationdate)
    exportdata.append(simulation_parameters.peakSolarPower)
    exportdata.append(len(allvehicles))
    exportdata.append(len(vehicles))
    exportdata.append(required_energy*1000)
    exportdata.append(solar_energy*1000)

    print("\n------- Simulation starting -------")

    consumers = []
    advanced_consumers = []
    powerUsage = [0.0]*24*60

    time_vector = generate_time_vector(simulationdate)
    for t in time_vector:
        arriving_vehicles: List[Vehicle] = []

        arriving_vehicles = Vehicle.vehicles_arriving(vehicles,t)
        
        schedule_vehicles = arriving_vehicles
        if(len(schedule_vehicles) != 0):
            consumer_ids = Consumer.unstarted_consumers(consumers,t)
            unstarted_vehicles = [v for v in vehicles if v.id_user in consumer_ids]
            for c in consumers[:]:  # Remove consumers that will be rescheduled
                if c.id_user in consumer_ids:
                    consumers.remove(c)
                    powerUsage = remove_consumer_from_powerUsage(simulationdate,powerUsage,c)
            schedule_vehicles.extend(unstarted_vehicles) # reschedule unstarted consumers
            print(f"{t}: "+"Schedule vehicles: "+str([v.id_user for v in schedule_vehicles]))


            renewable_available = solarProduction.production
            renewable_available = np.subtract(renewable_available,powerUsage)
            renewable_available = np.maximum(renewable_available,0)
            
            added_consumers,updated_powerUsage = dynamic_scheduling.greedy(schedule_vehicles, simulationdate, renewable_available)
            #added_consumers,updated_powerUsage = dynamic_scheduling.differential_evolution(schedule_vehicles, simulationdate, renewable_available)

            consumers.extend(added_consumers)
            powerUsage = np.add(powerUsage,updated_powerUsage)
        
            # check if solar energy can be used more efficiently
            # unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
            # print(f"Unused solar energy: {unused_solar_energy:.2f} kWh")
            # advanced_consumers = consumers

    print("------- Simulation ended -------\n")

    Consumer.printAllStats(allvehicles,consumers)

    total_consumed_energy =(sum(powerUsage)/60/1000)
    grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000)
    unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
    ### print stats (finished) ###
    print(f"Total energy consumed: {total_consumed_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% grid, {((1-grid_energy/total_consumed_energy)*100):.0f}% solar)")
    print(f"Grid energy used: {grid_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% from total energy)")
    print(f"Solar energy unused: {unused_solar_energy:.2f} kWh ({(unused_solar_energy/solar_energy*100):.0f}% from total solar energy)")

    exportdata.append(total_consumed_energy*1000)
    exportdata.append(grid_energy*1000)
    exportdata.append(unused_solar_energy*1000)

    if(simulation_parameters.exportresults):
        try:
            csv_write(simulation_parameters.resultpath, exportdata)
        except:
            print(f"Error: Failed to write data to file {simulation_parameters.resultpath}.")

    if(not simulation_parameters.hideresults):
        print("# Visualizing results...")
        plt.figure(figsize=(10, 6))

        solarProduction.visualize(plt)
        #forecast.visualizeGauss(plt,simulationdate)
        forecast.visualizeSin2(plt,simulationdate)
        
        plt.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black',label="total consumed power")
        plt.step(time_vector,[max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))],where='post',label="remaining solar power")
        plt.step(time_vector,[max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))], color='r',where='post',label="power drawn from grid")

        plt.title('Solar forecast and BEV consumption - {}kWp'.format(simulation_parameters.peakSolarPower/1000), fontsize=16)
        plt.xlabel('Time (CEST)', fontsize=12)
        plt.ylabel('Power (W)', fontsize=12)
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

# ---------------- main ---------------- #

def main():
    parser = argparse.ArgumentParser(
                    prog='Simulate Charging Station Management',
                    description='')
    parser.add_argument('-t', '--testdatapath', type=str)
    parser.add_argument('-r', '--resultpath', type=str)
    parser.add_argument('-e', '--exportresults', action='store_true')
    parser.add_argument('-v', '--hideresults', action='store_true')
    parser.add_argument('-d', '--simulationdate', type=str)
    parser.add_argument('-p', '--peaksolarpower', type=float)
    parser.add_argument('-f', '--peakpowerforecast', type=float)
    parser.add_argument('-a', '--forecastapi', type=str)
    args = parser.parse_args()

    simulation_parameters = SimulationParameters()
    if args.testdatapath is not None:
        simulation_parameters.testdatapath = args.testdatapath
    if args.resultpath is not None:
        simulation_parameters.resultpath = args.resultpath
    if args.exportresults is not None:
        simulation_parameters.exportresults = args.exportresults
    if args.hideresults is not None:
        simulation_parameters.hideresults = args.hideresults
    if args.simulationdate is not None:
        datetime_object = None
        try:
            datetime_format = "%Y-%m-%d %H:%M:%S"
            datetime_object = datetime.strptime(args.simulationdate, datetime_format)
        except:
            datetime_format = "%Y-%m-%d"
            datetime_object = datetime.strptime(args.simulationdate, datetime_format)
        simulation_parameters.simulationdate = datetime(datetime_object.year,datetime_object.month,datetime_object.day)
    if args.peaksolarpower is not None:
        simulation_parameters.peakSolarPower = args.peaksolarpower
    if args.peakpowerforecast is not None:
        simulation_parameters.peakpowerforecast = args.peakPowerForecast
    if args.forecastapi is not None:
        simulation_parameters.forecastapi = args.forecastapi

    simulate(simulation_parameters)
    
if __name__ == "__main__":
    main()