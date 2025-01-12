import json
import random
import numpy as np
import argparse
from scipy.stats import erlang, beta
from datetime import datetime, timedelta

# parameter definition for testdata generation
class TestdataParameters:
    def __init__(self,
                 filename='./test/testdata.json', 
                 vehiclecount=10, 
                 socmaxdistribution=[(60,0.5),(18,0.2),(100,0.3)], 
                 socmeanarrival=0.4, 
                 socvariance=0.04,
                 chargepowermax=[11,22,7], 
                 meanparkingtime=8, 
                 parkingtimeparameter=40,
                 seed=0):
        self.filename = filename

        self.vehiclecount = vehiclecount
        self.socmaxdistribution = socmaxdistribution
        self.socmeanarrival = socmeanarrival
        self.socvariance = socvariance
        self.chargepowermax = chargepowermax

        self.meanparkingtime = meanparkingtime
        self.parkingtimeparameter = parkingtimeparameter

        self.seed = seed

# generate the testdata based on the given parameters
def generate_testdata(testdata_parameters: TestdataParameters = TestdataParameters()) -> None:
    random.seed(testdata_parameters.seed)
    np.random.seed(testdata_parameters.seed)

    socmaxdistribution=list(zip(*(testdata_parameters.socmaxdistribution)))

    if(not 1==sum(socmaxdistribution[1])):
        print("Error: The sum of the SoC max distribution values must equal 1 (100%).")
        exit()

    mean_parking_time = testdata_parameters.meanparkingtime  # Mean arrival time before departure in hours
    soc_mean = testdata_parameters.socmeanarrival # mean SoC on arrival
    variance = testdata_parameters.socvariance # beta distribution variance parameter

    # calculate alpha and beta for the beta distribution
    a = soc_mean * ((soc_mean * (1 - soc_mean)) / variance - 1)
    b = (1 - soc_mean) * ((soc_mean * (1 - soc_mean)) / variance - 1)
    print(f"SoC state: Beta distribution parameters - alpha: {a}, beta: {b}")

    k = testdata_parameters.parkingtimeparameter # Erlang distribution shape parameter (k)
    print(f"Parking time: Erlang distribution parameters - k: {k}, mean: {mean_parking_time} hours")

    bev_data = []
    for i in range(1, testdata_parameters.vehiclecount+1):
        battery_size = int(np.random.choice(socmaxdistribution[0], p=socmaxdistribution[1]))

        parking_time = erlang.rvs(k, scale=mean_parking_time / k)

        departure_time = datetime.strptime("17:00", "%H:%M") + timedelta(minutes=random.randint(-90, 90))
        arrival_time = departure_time - timedelta(hours=parking_time)

        time_arrive = arrival_time.strftime("%H:%M")
        time_leave = departure_time.strftime("%H:%M")

        percent_arrive = max(0, min(99, int(beta.rvs(a, b) * 100)))
        percent_leave = random.choice([60,70,80,90,100])

        if percent_leave<percent_arrive: # make sure that all vehicles will require charging
           percent_leave=100

        charge_power_max = random.choice(testdata_parameters.chargepowermax)

        bev_data.append({
            "id_user": i,
            "time_arrive": time_arrive,
            "time_leave": time_leave,
            "percent_arrive": percent_arrive,
            "percent_leave": percent_leave,
            "battery_size": battery_size,
            "charge_max": charge_power_max
        })

    try:
        with open(testdata_parameters.filename, "w") as f:
            json.dump(bev_data, f, indent=4)
    except Exception as e:
        print(f"An error occurred when writing the results to the file: {e}")
        exit()

    print(f"Success! {len(bev_data)} BEVs have been written to file {testdata_parameters.filename}.")

def main():
    parser = argparse.ArgumentParser(
                    prog='generate_testdata.py',
                    description='The Solar Charging BEV Testdata Generator generates a JSON file containing test data for battery electric vehicles (BEVs). Each vehicle is assigned random attributes such as arrival time, departure time, battery size, state of charge (SoC) at arrival and departure, and maximum charging power.\n\
                        A discrete probability distribution is used to assign the maximum state of charge (SoC) for vehicle batteries based on user-defined probabilities.\n\
                        A Beta distribution is used to model the initial state of charge (SoC) of vehicles upon arrival. The mean and variance of the distribution are derived from the specified socmeanarrival parameter and socvariance parameter.\n\
                        Parking Duration: The time between vehicle arrival and departure is modeled using an Erlang distribution. The shape parameter (k) and the mean parking time are specified by the parameters meanparkingtime and parkingtimeparameter.\n\
                        A random variation of up to ±90 minutes is added to a baseline departure time of 17:00 to simulate realistic scheduling.\n\
                        The maximum allowed charging power is randomly selected from a list of power levels.')
    
    parser.add_argument('-f', '--file', type=str, help="The file path for writing the results. The specified file will be overwritten. Default: ./test/testdata.json")
    parser.add_argument('-c', '--count', type=int, help="Number of vehicles to generate. Default: 10")
    parser.add_argument('-s', '--socmaxdistribution', type=str, help="Define the destribution for SoC_max as comma seperated tuples (SoC_max (kWh),probability) e.g.: \"(60,0.5),(18,0.2),(100,0.3)\"")
    parser.add_argument('-m', '--socmeanarrival', type=float, help="The mean SoC on arrival. e.g.: 0.4 (40%% of SoC_max)")
    parser.add_argument('-v', '--socvariance', type=float, help="The variance for the Beta distributed SoC on arrival. Default: 0.04")
    parser.add_argument('-p', '--chargepowermax', type=str, help="List of maximum charging powers in kW. e.g.: [11,22,7]")
    parser.add_argument('-t', '--meanparkingtime', type=float, help="The mean time from arrival to leave in hours. Default: 8")
    parser.add_argument('-k', '--parkingtimeparameter', type=float, help="Parameter k for the Erlang distributed parking time. Default: 40")
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    
    testdata_parameters = TestdataParameters()
    if args.file is not None:
        testdata_parameters.filename = args.file
    if args.count is not None:
        testdata_parameters.vehiclecount = args.count
    if args.socmaxdistribution is not None:
        socmaxdistribution = 0
        try:
            socmaxdistribution = list(eval(args.socmaxdistribution))
        except:
            print("Error: Failed to parse SoC distribution.")
            exit()
        testdata_parameters.socmaxdistribution = socmaxdistribution
    if args.socmeanarrival is not None:
        testdata_parameters.socmeanarrival = args.socmeanarrival
    if args.socvariance is not None:
        testdata_parameters.socvariance = args.socvariance
    if args.chargepowermax is not None:
        testdata_parameters.chargepowermax = args.chargepowermax
    if args.meanparkingtime is not None:
        testdata_parameters.meanparkingtime = args.meanparkingtime
    if args.parkingtimeparameter is not None:
        testdata_parameters.parkingtimeparameter = args.parkingtimeparameter
    if args.seed is not None:
        testdata_parameters.seed = args.seed

    generate_testdata(testdata_parameters)
if __name__ == "__main__":
    main()