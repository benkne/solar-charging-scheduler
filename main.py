import os
import json
import csv
import energy_charts_api
from forecast_power import Forecast
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
from typing import List, Optional
import numpy as np
import argparse

from vehicle import Vehicle
from forecast_power import Forecast
from renewable_production import Production
from consumer_model import Consumer, ConsumerPlot, PowerCurve, TimeInterval
from dynamic_scheduling import SchedulingParameters, dynamic_scheduling, no_strategy, overcharge_scheduling
import simulation
from simulation import SimulationParameters, generate_time_vector, total_power_usage


# ---------------- functions ---------------- #

def read_testdata_json(file_path: str) -> Optional[List[dict]]:
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

# ---------------- simulation ---------------- #

def simulate(simulation_parameters: SimulationParameters):

    simulationdate = simulation_parameters.simulationdate

    exportdata= {
        "simulationdate" : None,
        "peakSolarPower" : None,
        "totalVehicles" : None,
        "scheduledVehicles" : None,
        "requiredEnergy" : None,
        "solarEnergy" : None,
        "consumedEnergy" : None,
        "gridEnergy" : None,
        "solarUnused" : None
    }

    print("# Reading vehicle data from file...")
    data = read_testdata_json(simulation_parameters.testdatapath)
    vehicles: List[Vehicle] = Vehicle.create_vehicles(data,simulationdate)

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast, simulationdate, smooth=simulation_parameters.smoothForecast) 

    if(solarProduction.getEnergy()==0):
        print("Warning: No solar production for requested date!")

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

    exportdata["simulationdate"] = simulationdate
    exportdata["peakSolarPower"] = simulation_parameters.peakSolarPower
    exportdata["totalVehicles"] = len(allvehicles)
    exportdata["scheduledVehicles"] = len(vehicles)
    exportdata["requiredEnergy"] = required_energy*1000
    exportdata["solarEnergy"] = solar_energy*1000

    print("\n------- Simulation starting -------")

    consumers: List[Consumer] = []
    powerUsage = [0.0]*24*60
    overchargePower = [0.0]*24*60

    time_vector: datetime = generate_time_vector(simulationdate)
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
            schedule_vehicles.extend(unstarted_vehicles) # reschedule unstarted consumers
            print(f"{t}: "+"Schedule vehicles: "+str([v.id_user for v in schedule_vehicles]))

            # remove overcharging after time t
            for c in consumers:
                if c.overpower.interval is not None:
                    if c.overpower.interval.timeInInterval(t):
                        index_in_interval = int((t.timestamp()-c.overpower.interval.time_start.timestamp())/60)
                        c.overpower.interval.time_end = t #-timedelta(minutes=1)
                        c.overpower.power = c.overpower.power[0:index_in_interval]

            powerUsage = total_power_usage(simulationdate, consumers)
            renewable_power = Production.renewable_available(solarProduction.production,powerUsage)
            
            added_consumers = dynamic_scheduling(simulation_parameters.scheduling, schedule_vehicles, t, renewable_power)
            #added_consumers = no_strategy(simulation_parameters.scheduling, schedule_vehicles, t, renewable_power)

            consumers.extend(added_consumers)

            powerUsage = total_power_usage(simulationdate, consumers)

            ##### overcharging logic #####
            if(simulation_parameters.scheduling.overcharge):
                consumers, overchargePower = overcharge_scheduling(consumers,vehicles,solarProduction,powerUsage,t)
            powerUsage = list(np.add(powerUsage,overchargePower))

    print("------- Simulation ended -------\n")

    Consumer.printAllStats(allvehicles,consumers)

    total_consumed_energy =(sum(powerUsage)/60/1000)
    grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000)
    unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
    ### print stats (finished) ###
    print(f"Total energy consumed: {total_consumed_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% grid, {((1-grid_energy/total_consumed_energy)*100):.0f}% solar)")
    print(f"Grid energy used: {grid_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100):.0f}% from total energy)")
    print(f"Solar energy unused: {unused_solar_energy:.2f} kWh ({(unused_solar_energy/solar_energy*100 if solar_energy!=0 else 0):.0f}% from total solar energy)")

    exportdata["consumedEnergy"] = total_consumed_energy*1000
    exportdata["gridEnergy"] = grid_energy*1000
    exportdata["solarUnused"] = unused_solar_energy*1000

    if(simulation_parameters.exportresults):
        if(not os.path.exists(simulation_parameters.resultpath)):
            try:
                csv_write(simulation_parameters.resultpath, exportdata.keys())
            except:
                print(f"Error: Failed to write data to file {simulation_parameters.resultpath}.")
        try:
            csv_write(simulation_parameters.resultpath, exportdata.values())
        except:
            print(f"Error: Failed to write data to file {simulation_parameters.resultpath}.")

    if(not simulation_parameters.hideresults):
        print("# Visualizing results...")
        plt.figure(figsize=(10, 6))

        solarProduction.visualize(plt)
        #forecast.visualizeGauss(plt,simulationdate)
        forecast.visualizeSin2(plt,simulationdate)
        
        plt.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black',label="total consumed power")
        plt.step(time_vector, overchargePower, where='post', marker='', linestyle='-', color='lime',label="overcharge power")
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

        consumers_sorted_starting: List[Consumer] = Consumer.sort_consumers_by_start_time(consumers)
        consumers_sorted_ending: List[Consumer] = Consumer.sort_consumers_by_end_time(consumers)

        last_consumer = consumers_sorted_ending[-1]
        endtime = last_consumer.power.interval.time_end if last_consumer.overpower.interval is None else last_consumer.overpower.interval.time_end
        plt.xlim(consumers_sorted_starting[0].power.interval.time_start-timedelta(minutes=30),endtime+timedelta(minutes=30))
        plt.ylim((0,max(forecast.getDailyPeak(simulationdate),max(powerUsage))*1.15))
        plt.legend(loc="upper left")
        plt.tight_layout() 
        plt.show()

# ---------------- main ---------------- #
    
if __name__ == "__main__":
    p = argparse.ArgumentParser(
                    prog='Simulate Charging Station Management',
                    description='')
    operation, simulation_parameters = simulation.parse(p)
    simulate(simulation_parameters)