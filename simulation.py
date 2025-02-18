import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import csv
import os
from datetime import timedelta, datetime
from typing import List

import scheduling_framework.energy_charts_api as energy_charts_api
from scheduling_framework.vehicle import Vehicle, add_vehicle
from scheduling_framework.forecast_power import Forecast
from scheduling_framework.renewable_production import Production
from scheduling_framework.consumer_model import Consumer, ConsumerPlot
from scheduling_framework.dynamic_scheduling import SchedulingParameters, dynamic_scheduling, no_strategy, overcharge_scheduling
from scheduling_framework.parameters import SimulationParameters

# ---------------- functions ---------------- #

# write generic data to csv file
def csv_write(file_path: str, data) -> None:
    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(data)
    print(f"Results written to {file_path}.")

# generate json file containing all simulation information
def generate_json(filename: str, simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    dict_data = {"simulation_parameters": simulation_parameters.to_dict(),
                 "vehicles": Vehicle.vehicles_to_dict(vehicles),
                 "consumers": Consumer.consumers_to_dict(consumers)
                }

    with open(filename, 'w') as file:
        json.dump(dict_data, file, indent=4)

# load the json file containing all simulation information
def load_json(filename: str):
    with open(filename, "r") as file:
        data = json.load(file)
        
        # Deserialize each object
        simulation_parameters = SimulationParameters.from_dict(data["simulation_parameters"])
        vehicles = Vehicle.vehicles_from_dict(data["vehicles"])
        consumers = Consumer.consumers_from_dict(data["consumers"])
        
        return simulation_parameters, vehicles, consumers
    
# generate a one-minute step time vector for the duration of 1 day
def generate_time_vector(date: datetime):
    vector = []
    time = date
    while time < date+timedelta(days=1):
        vector.append(time)
        time=time+timedelta(minutes=1)
    return vector

# return the total power usage of all consumers
def total_power_usage(simulationdate: datetime, consumers: List[Consumer]):
    powerUsage = [0.0]*24*60
    for c in consumers:
        power_start_index =int((c.power.interval.time_start.timestamp()-simulationdate.timestamp())/60)
        powerUsage = np.add(powerUsage,[0]*(power_start_index)+c.power.power+[0]*(24*60-power_start_index-len(c.power.power)))
    return powerUsage

# return the power from overcharging of all consumers
def overcharge_power(simulationdate: datetime, consumers: List[Consumer]):
    overchargePower = [0.0]*24*60
    for c in consumers:
        if c.overpower.interval is not None:
            power_start_index =int((c.overpower.interval.time_start.timestamp()-simulationdate.timestamp())/60)
            overchargePower = np.add(overchargePower,[0]*(power_start_index)+c.overpower.power+[0]*(24*60-power_start_index-len(c.overpower.power)))
    return overchargePower

# plot power curves and scheduling graph
def visualize_results(consumers: List[Consumer], solarProduction: Production, forecast: Forecast, simulation_parameters: SimulationParameters, powerUsage: List[float], overchargePower: List[float]):
    print("# Visualizing results...")
    simulationdate = simulation_parameters.simulationdate
    #plt.figure(figsize=(10, 6))
    fig, axs = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 2]})
    ax1 = axs[0]
    ax2 = axs[1]

    ax1.set_title('Solar forecast and BEV consumption - {}kWp'.format(simulation_parameters.peakSolarPower / 1000), fontsize=16)
    ax1.set_xlabel('Time (CEST)', fontsize=12)
    ax1.set_ylabel('Power (W)', fontsize=12)
    ax1.grid(True)
    ax1.tick_params(axis='x', rotation=45)

    ax2.set_xlabel('Time (CEST)', fontsize=12)
    ax2.set_ylabel('Power (W)', fontsize=12)
    ax2.grid(True)
    ax2.tick_params(axis='x', rotation=45)

    solarProduction.visualize(ax1)
    solarProduction.visualize(ax2)
    # forecast.visualizeGauss(plt,simulationdate)
    forecast.visualizeSin2(ax1,simulationdate)

    time_vector: datetime = generate_time_vector(simulationdate)
    
    ax1.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black', label="total consumed power")
    ax2.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black', label="total consumed power")
    ax2.step(time_vector, overchargePower, where='post', marker='', linestyle='-.', color='lime', label="overcharge power")
    ax2.step(time_vector,[max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))], where='post', linestyle=':', label="remaining solar power")
    ax2.step(time_vector,[max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))], color='r', where='post', label="power drawn from grid")
    
    if(len(consumers)>0):
        consumerPlot: ConsumerPlot = ConsumerPlot(consumers)
        consumerPlot.visualize(ax1)

        consumers_sorted_starting: List[Consumer] = Consumer.sort_consumers_by_start_time(consumers)
        consumers_sorted_ending: List[Consumer] = Consumer.sort_consumers_by_end_time(consumers)

        last_consumer = consumers_sorted_ending[-1]
        endtime = last_consumer.power.interval.time_end if last_consumer.overpower.interval is None else last_consumer.overpower.interval.time_end
        ax1.set_xlim(consumers_sorted_starting[0].power.interval.time_start-timedelta(minutes=30),endtime+timedelta(minutes=30))
        ax1.set_ylim((0,max(forecast.getDailyPeak(simulationdate),max(powerUsage))*1.15))
        ax2.set_xlim(consumers_sorted_starting[0].power.interval.time_start-timedelta(minutes=30),endtime+timedelta(minutes=30))
        ax2.set_ylim((0,max(forecast.getDailyPeak(simulationdate),max(powerUsage))*1.15))
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper left")
    plt.tight_layout() 
    plt.savefig('./results/output.svg')
    plt.show()

# create a new simulation 
def create(simulation_parameters: SimulationParameters):
    return [], []

# add a vehicle to the simulation
def add(simulation_parameters: SimulationParameters, vehicles: List[Vehicle], vehicle: str):
    if(vehicle is None):
        print("Error: No vehicle specified.")
        exit()
    vehicle = add_vehicle(simulation_parameters.simulationdate, vehicles, vehicle)
    vehicles.append(vehicle)
    return vehicles

# schedule vehicles 
def schedule(simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    simulationdate = simulation_parameters.simulationdate

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast, simulationdate, smooth=simulation_parameters.smoothForecast) 

    if(solarProduction.getEnergy()==0):
        print("Warning: No solar production for requested date!")

    print("# Preparing vehicle data...")
    allvehicles = vehicles[:]

    vehicles_ = []
    for v in vehicles:
        if v.energy_required>0:
            vehicles_.append(v)
        else:
            print(f"Info: Removed vehicle with ID {v.id_user} because it does not require charging.")
    vehicles = vehicles_

    vehicles = Vehicle.sort_vehicles_by_arrive_time(vehicles)

    if(len(vehicles)==0): # terminate if there are no vehicles
        print("No vehicles to schedule.")
        exit()

    print("Starting information:")
    required_energy = sum([v.energy_required for v in vehicles])
    solar_energy = (solarProduction.getEnergy()/1000)
    print(f"Starting scheduling process for {len(vehicles)} vehicles.")
    print(f"Total energy required: {required_energy:.2f} kWh")
    print(f"Total solar energy available (prediction): {solar_energy:.2f} kWh")
    if(required_energy>solar_energy):
        print("Warning: There is less solar power available than required. Power from the grid is necessary!")
    print("\n")

    powerUsage = [0.0]*24*60
    overchargePower = [0.0]*24*60


    t = vehicles[-1].time_arrive # the scheduling time will be the arrive time of the last vehicle
    consumer_ids = [c.id_user for c in consumers]
    schedule_vehicles = [v for v in vehicles if v.id_user not in consumer_ids]
    
    consumer_ids = Consumer.unstarted_consumers(consumers,t)
    unstarted_vehicles = [v for v in vehicles if v.id_user in consumer_ids]
    for c in consumers[:]:  # Remove consumers that will be rescheduled
        if c.id_user in consumer_ids:
            consumers.remove(c)
    schedule_vehicles.extend(unstarted_vehicles) # reschedule unstarted consumers

    if(len(schedule_vehicles) != 0):
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
   
        consumers.extend(added_consumers)

        powerUsage = total_power_usage(simulationdate, consumers)

    return len(schedule_vehicles), allvehicles, consumers

# visualize the state of the simulation
def visualize(simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    simulationdate = simulation_parameters.simulationdate

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast, simulationdate, smooth=simulation_parameters.smoothForecast) 

    print("Starting information:")
    required_energy = sum([v.energy_required for v in vehicles])
    solar_energy = (solarProduction.getEnergy()/1000)
    print(f"Vehicles available: {len(vehicles)}.")
    print(f"Total energy required: {required_energy:.2f} kWh")
    print(f"Total solar energy available (prediction): {solar_energy:.2f} kWh")
    if(required_energy>solar_energy):
        print("Warning: There is less solar power available than required. Power from the grid is necessary!")

    print("\n")

    Consumer.printAllStats(vehicles,consumers)

    powerUsage = total_power_usage(simulationdate, consumers)
    overchargePower = overcharge_power(simulationdate,consumers)
    powerUsage = np.add(powerUsage,overchargePower)

    total_consumed_energy =(sum(powerUsage)/60/1000)
    grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000) if powerUsage is not None else 0
    unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
    ### print stats (finished) ###
    print(f"Total energy consumed: {total_consumed_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100 if total_consumed_energy != 0 else 0):.0f}% grid, {((1-grid_energy/total_consumed_energy)*100  if total_consumed_energy != 0 else 0):.0f}% solar)")
    print(f"Grid energy used: {grid_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100  if total_consumed_energy != 0 else 0):.0f}% from total energy)")
    print(f"Solar energy unused: {unused_solar_energy:.2f} kWh ({(unused_solar_energy/solar_energy*100 if solar_energy!=0 else 0):.0f}% from total solar energy)")

    if(not simulation_parameters.hideresults):
        visualize_results(consumers,solarProduction,forecast,simulation_parameters,powerUsage,overchargePower)

# overcharge egligible vehicles
def overcharge(simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    simulationdate = simulation_parameters.simulationdate

    vehicles = Vehicle.sort_vehicles_by_arrive_time(vehicles)
    t=simulation_parameters.simulationdate
    if(len(vehicles)>0):
        t = vehicles[-1].time_arrive

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast, simulationdate, smooth=simulation_parameters.smoothForecast) 

    powerUsage = total_power_usage(simulation_parameters.simulationdate, consumers)
    
    ##### overcharging logic #####
    number_scheduled=0
    if(simulation_parameters.scheduling.overcharge):
        number_scheduled, consumers, overchargePower = overcharge_scheduling(consumers,vehicles,solarProduction,powerUsage,t)

    return number_scheduled,vehicles,consumers

# ---------------- parsing ---------------- #

def argument_parser(parser):
    parser.add_argument('-e', '--storepath', type=str, help="Path for simulation *.json savefile.")
    parser.add_argument('-t', '--testdatapath', type=str, help="Path for testdata *.json file.")
    parser.add_argument('-r', '--resultpath', type=str, help="Path for *.csv file if result export is enabled.")
    parser.add_argument('-x', '--exportresults', action='store_true', help="Exports scheduling results to *.csv file.")
    parser.add_argument('-v', '--hideresults', action='store_true', help="Do not show plot after simulation run.")
    parser.add_argument('-d', '--simulationdate', type=str, help="Set the date for the simulation. e.g.: 2025-01-30")
    parser.add_argument('-p', '--peaksolarpower', type=float, help="The peak solar power in Watts for the simulated power plant.")
    parser.add_argument('-f', '--peakpowerforecast', type=float, help="The scaling factor for the forcast.")
    parser.add_argument('-o', '--smoothforecast', type=str, help="Linearize data points from forecast.")
    parser.add_argument('-a', '--forecastapi', type=str, help="Forecast API url.")
    
    parser.add_argument('-b', '--flatten', type=str, help="Flatten the power draw at the end to fit the descending solar generation.")
    parser.add_argument('-c', '--overcharge', type=str, help="Allow charging more power than requested.")
    parser.add_argument('-m', '--reducemax', type=str, help="Reduce the maximum power draw to optimize the scheduling.")
    parser.add_argument('-g', '--allowgrid', type=str, help="Allow drawing power from the grid at the beginning of the charging process to optimize the scheduling.")

    return parser

def parse(parser, op=False):
    parser = argument_parser(parser)

    if(op):
        parser.add_argument('operation', help='Available operations: create, add, schedule, overcharge, visualize')
        parser.add_argument('--vehicle', type=str, help="Add vehicle to simulation. Format: \"id_user,time_arrive,time_leave,percent_arrive,percent_leave,battery_size,charge_max\"")

    args = parser.parse_args()

    simulation_parameters = SimulationParameters()
    if args.storepath is not None:
        simulation_parameters.storepath = args.storepath
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
        simulation_parameters.update_forecastapi()
    if args.peaksolarpower is not None:
        simulation_parameters.peakSolarPower = args.peaksolarpower
    if args.peakpowerforecast is not None:
        simulation_parameters.peakPowerForecast = args.peakPowerForecast
    if args.smoothforecast is not None:
        simulation_parameters.smoothForecast = args.smoothforecast.lower() == 'true'
    if args.forecastapi is not None:
        simulation_parameters.forecastapi = args.forecastapi
    
    scheduling_parameters = SchedulingParameters()
    if args.flatten is not None:
        scheduling_parameters.flatten = args.flatten.lower() == 'true'
    if args.overcharge is not None:
        scheduling_parameters.overcharge = args.overcharge.lower() == 'true'
    if args.reducemax is not None:
        scheduling_parameters.reducemax = args.reducemax.lower() == 'true'
    if args.allowgrid is not None:
        scheduling_parameters.allowgrid = args.allowgrid.lower() == 'true'

    simulation_parameters.scheduling = scheduling_parameters

    if(op):
        vehicle=None
        if args.vehicle is not None:
            vehicle=str(args.vehicle)
        operation = args.operation
        return operation, vehicle, simulation_parameters
    
    return simulation_parameters
    
if __name__ == "__main__":
    p = argparse.ArgumentParser(
                prog='simulation.py',
                description='This program allows the iterative simulation of the scheduling process. The different operations are: create, add, schedule, overcharge and visualize.\n\
                            create: creates a new simulation file with the set simulation parameters.\n\
                            add: add new vehicle to simulation using --vehicle\n\
                            schedule: (re)schedule all vehicles\n\
                            overcharge: if possible, charge vehicles more than required\n\
                            visualize: show stats and open plot of scheduling overwiew')
    operation, vehicle, simulation_parameters = parse(p,op=True)

    if(operation!="create"):
        try:
            simulation_parameters, vehicles, consumers = load_json(filename=simulation_parameters.storepath)
        except:
            print("Error: Can not read simulation file!")
            exit()

    number_scheduled = 0
    if operation == "create":
        vehicles, consumers = create(simulation_parameters)
    elif operation == "add":
        vehicles = add(simulation_parameters,vehicles,vehicle)
    elif operation == "schedule":
        number_scheduled, vehicles, consumers = schedule(simulation_parameters,vehicles,consumers)
    elif operation == "visualize":
        visualize(simulation_parameters,vehicles,consumers)
    elif operation == "overcharge":
        number_scheduled, vehicles, consumers = overcharge(simulation_parameters,vehicles,consumers)

    generate_json(simulation_parameters.storepath, simulation_parameters, vehicles, consumers)

    if(simulation_parameters.exportresults):
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

        required_energy = sum([v.energy_required for v in vehicles])

        forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
        forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
        solarProduction = Production(forecast, simulation_parameters.simulationdate, smooth=simulation_parameters.smoothForecast) 
        solar_energy = (solarProduction.getEnergy()/1000)

        exportdata["simulationdate"] = simulation_parameters.simulationdate
        exportdata["peakSolarPower"] = simulation_parameters.peakSolarPower
        exportdata["totalVehicles"] = len(vehicles)
        exportdata["scheduledVehicles"] = number_scheduled
        exportdata["requiredEnergy"] = required_energy*1000
        exportdata["solarEnergy"] = solar_energy*1000

        powerUsage = total_power_usage(simulation_parameters.simulationdate, consumers)
        overchargePower = overcharge_power(simulation_parameters.simulationdate,consumers)
        powerUsage = np.add(powerUsage,overchargePower)

        total_consumed_energy =(sum(powerUsage)/60/1000)
        grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000)
        unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)

        exportdata["consumedEnergy"] = total_consumed_energy*1000
        exportdata["gridEnergy"] = grid_energy*1000
        exportdata["solarUnused"] = unused_solar_energy*1000

        if(not os.path.exists(simulation_parameters.resultpath)):
            try:
                csv_write(simulation_parameters.resultpath, exportdata.keys())
            except:
                print(f"Error: Failed to write data to file {simulation_parameters.resultpath}.")
        try:
            csv_write(simulation_parameters.resultpath, exportdata.values())
        except:
            print(f"Error: Failed to write data to file {simulation_parameters.resultpath}.")