import argparse
import json
from typing import List

import energy_charts_api
from datetime import timedelta, datetime
from dynamic_scheduling import SchedulingParameters
from vehicle import Vehicle, prompt_vehicle
from forecast_power import Forecast
from renewable_production import Production
from consumer_model import Consumer, ConsumerPlot, PowerCurve, TimeInterval
from dynamic_scheduling import SchedulingParameters, dynamic_scheduling, no_strategy, overcharge_scheduling
import matplotlib.pyplot as plt
from parameters import SimulationParameters

import numpy as np
    
def generate_json(filename: str, simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    dict_data = {"simulation_parameters": simulation_parameters.to_dict(),
                 "vehicles": Vehicle.vehicles_to_dict(vehicles),
                 "consumers": Consumer.consumers_to_dict(consumers)
                }

    with open(filename, 'w') as file:
        json.dump(dict_data, file, indent=4)

def load_json(filename: str):
    with open(filename, "r") as file:
        data = json.load(file)
        
        # Deserialize each object
        simulation_parameters = SimulationParameters.from_dict(data["simulation_parameters"])
        vehicles = Vehicle.vehicles_from_dict(data["vehicles"])
        consumers = Consumer.consumers_from_dict(data["consumers"])
        
        return simulation_parameters, vehicles, consumers
    
def generate_time_vector(date: datetime):
    vector = []
    time = date
    while time < date+timedelta(days=1):
        vector.append(time)
        time=time+timedelta(minutes=1)
    return vector

def total_power_usage(simulationdate: datetime, consumers: List[Consumer]):
    powerUsage = [0.0]*24*60
    for c in consumers:
        power_start_index =int((c.power.interval.time_start.timestamp()-simulationdate.timestamp())/60)
        powerUsage = np.add(powerUsage,[0]*(power_start_index)+c.power.power+[0]*(24*60-power_start_index-len(c.power.power)))

    return powerUsage

def overcharge_power(simulationdate: datetime, consumers: List[Consumer]):
    overchargePower = [0.0]*24*60
    for c in consumers:
        if c.overpower.interval is not None:
            power_start_index =int((c.overpower.interval.time_start.timestamp()-simulationdate.timestamp())/60)
            overchargePower = np.add(overchargePower,[0]*(power_start_index)+c.overpower.power+[0]*(24*60-power_start_index-len(c.overpower.power)))

    return overchargePower

def create(simulation_parameters: SimulationParameters):
    return [], []

def add(simulation_parameters: SimulationParameters, vehicles: List[Vehicle]):
    vehicle = prompt_vehicle(simulation_parameters.simulationdate, vehicles)
    vehicles.append(vehicle)
    return vehicles

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


    t = vehicles[-1].time_arrive
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

    return allvehicles, consumers

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

    powerUsage = total_power_usage(simulationdate,consumers)
    powerUsage = powerUsage + overcharge_power(simulationdate,consumers)
    overchargePower = overcharge_power(simulationdate,consumers)

    total_consumed_energy =(sum(powerUsage)/60/1000)
    grid_energy = (sum([max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))])/60/1000)
    unused_solar_energy = (sum([max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))])/60/1000)
    ### print stats (finished) ###
    print(f"Total energy consumed: {total_consumed_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100 if total_consumed_energy != 0 else 0):.0f}% grid, {((1-grid_energy/total_consumed_energy)*100  if total_consumed_energy != 0 else 0):.0f}% solar)")
    print(f"Grid energy used: {grid_energy:.2f} kWh ({(grid_energy/total_consumed_energy*100  if total_consumed_energy != 0 else 0):.0f}% from total energy)")
    print(f"Solar energy unused: {unused_solar_energy:.2f} kWh ({(unused_solar_energy/solar_energy*100 if solar_energy!=0 else 0):.0f}% from total solar energy)")

    if(not simulation_parameters.hideresults):
        print("# Visualizing results...")
        plt.figure(figsize=(10, 6))

        solarProduction.visualize(plt)
        #forecast.visualizeGauss(plt,simulationdate)
        forecast.visualizeSin2(plt,simulationdate)

        time_vector: datetime = generate_time_vector(simulationdate)
        
        plt.step(time_vector, powerUsage, where='post', marker='', linestyle='-', color='black', label="total consumed power")
        plt.step(time_vector, overchargePower, where='post', marker='', linestyle='-', color='lime', label="overcharge power")
        plt.step(time_vector,[max(solarProduction.production[i]-powerUsage[i],0) for i in range(len(powerUsage))], where='post', label="remaining solar power")
        plt.step(time_vector,[max(-(solarProduction.production[i]-powerUsage[i]),0) for i in range(len(powerUsage))], color='r', where='post', label="power drawn from grid")

        plt.title('Solar forecast and BEV consumption - {}kWp'.format(simulation_parameters.peakSolarPower/1000), fontsize=16)
        plt.xlabel('Time (CEST)', fontsize=12)
        plt.ylabel('Power (W)', fontsize=12)
        plt.grid(True)
        plt.xticks(rotation=45)
    	
        if(len(consumers)>0):
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

def overcharge(simulation_parameters: SimulationParameters, vehicles: List[Vehicle], consumers: List[Consumer]):
    simulationdate = simulation_parameters.simulationdate

    vehicles = Vehicle.sort_vehicles_by_arrive_time(vehicles)
    t = vehicles[-1].time_arrive

    print("# Making forecast API request...")
    forecast: Forecast = energy_charts_api.api_request(simulation_parameters.forecastapi)
    forecast.scale(simulation_parameters.peakSolarPower, simulation_parameters.peakPowerForecast)
    solarProduction = Production(forecast, simulationdate, smooth=simulation_parameters.smoothForecast) 

    powerUsage = total_power_usage(simulation_parameters.simulationdate, consumers)
    ##### overcharging logic #####
    if(simulation_parameters.scheduling.overcharge):
        consumers, overchargePower = overcharge_scheduling(consumers,vehicles,solarProduction,powerUsage,t)

    return vehicles,consumers


def parse(parser):
    parser = argparse.ArgumentParser(
                    prog='Simulate Charging Station Management',
                    description='')
    parser.add_argument('operation', type=str)
    parser.add_argument('-e', '--storepath', type=str)
    parser.add_argument('-t', '--testdatapath', type=str)
    parser.add_argument('-r', '--resultpath', type=str)
    parser.add_argument('-x', '--exportresults', action='store_true')
    parser.add_argument('-v', '--hideresults', action='store_true')
    parser.add_argument('-d', '--simulationdate', type=str)
    parser.add_argument('-p', '--peaksolarpower', type=float)
    parser.add_argument('-f', '--peakpowerforecast', type=float)
    parser.add_argument('-o', '--smoothforecast', type=str, default='true')
    parser.add_argument('-a', '--forecastapi', type=str)
    parser.add_argument('-s', '--scheduling', type=str)
    args = parser.parse_args()

    operation = args.operation

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
    if args.peaksolarpower is not None:
        simulation_parameters.peakSolarPower = args.peaksolarpower
    if args.peakpowerforecast is not None:
        simulation_parameters.peakPowerForecast = args.peakPowerForecast
    if args.smoothforecast is not None:
        simulation_parameters.smoothForecast = args.smoothforecast.lower() == 'true'
    if args.forecastapi is not None:
        simulation_parameters.forecastapi = args.forecastapi
    if args.scheduling is not None:
        scheduling_parameters = SchedulingParameters()
        scheduling_parameters.parseSchedulingParameters(args.scheduling)
        simulation_parameters.scheduling = scheduling_parameters

    return operation, simulation_parameters
    
if __name__ == "__main__":
    p = argparse.ArgumentParser(
                prog='Simulate Charging Station Management',
                description='')
    operation, simulation_parameters = parse(p)

    try:
        simulation_parameters, vehicles, consumers = load_json(filename=simulation_parameters.storepath)
    except:
        if(operation!="create"):
            print("Error: Can not read simulation file!")
            exit()

    if operation == "create":
        vehicles, consumers = create(simulation_parameters)
    elif operation == "add":
        vehicles = add(simulation_parameters,vehicles)
    elif operation == "schedule":
        vehicles, consumers = schedule(simulation_parameters,vehicles,consumers)
    elif operation == "visualize":
        visualize(simulation_parameters,vehicles,consumers)
    elif operation == "overcharge":
        vehicles, consumers = overcharge(simulation_parameters,vehicles,consumers)
    generate_json(simulation_parameters.storepath, simulation_parameters, vehicles, consumers)