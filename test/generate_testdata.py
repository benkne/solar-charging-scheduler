import json
import random
import numpy as np
import argparse
from scipy.stats import erlang, beta
from datetime import datetime, timedelta

class TestdataParameters:
    def __init__(self,
                 filename='./testdata.json', 
                 vehiclecount=10, 
                 socmaxdistribution=[(60,0.5),(18,0.2),(100,0.3)], 
                 socmeanarrival=0.4, 
                 chargepowermax=[11,22,7], 
                 meanparkingtime=8, 
                 parkingtimeparameter=12,
                 seed=0):
        self.filename = filename

        self.vehiclecount = vehiclecount
        self.socmaxdistribution = socmaxdistribution
        self.socmeanarrival = socmeanarrival
        self.chargepowermax = chargepowermax

        self.meanparkingtime = meanparkingtime
        self.parkingtimeparameter = parkingtimeparameter

        self.seed = seed

def generate_testdata(testdata_parameters):
    random.seed(testdata_parameters.seed)
    np.random.seed(testdata_parameters.seed)

    socmaxdistribution=list(zip(*(testdata_parameters.socmaxdistribution)))

    assert(1==sum(socmaxdistribution[1]))

    mean_parking_time = testdata_parameters.meanparkingtime  # Mean arrival time before departure in hours
    soc_mean = testdata_parameters.socmeanarrival # mean SoC on arrival
    variance = 0.01 # beta distribution variance parameter

    # calculate alpha and beta for the beta distribution
    a = soc_mean * ((soc_mean * (1 - soc_mean)) / variance - 1)
    b = (1 - soc_mean) * ((soc_mean * (1 - soc_mean)) / variance - 1)

    k = testdata_parameters.parkingtimeparameter # Erlang distribution shape parameter (k)

    bev_data = []
    for i in range(1, testdata_parameters.vehiclecount+1):
        battery_size = int(np.random.choice(socmaxdistribution[0], p=socmaxdistribution[1]))

        parking_time = erlang.rvs(k, scale=mean_parking_time / k)
        print(parking_time)

        departure_time = datetime.strptime("16:30", "%H:%M") + timedelta(minutes=random.randint(-120, 120))
        arrival_time = departure_time - timedelta(hours=parking_time)

        time_arrive = arrival_time.strftime("%H:%M")
        time_leave = departure_time.strftime("%H:%M")

        percent_arrive = max(0, min(100, int(beta.rvs(a, b) * 100)))
        percent_leave = random.choice([60,70,80,90,100])

        #if percent_leave<percent_arrive: # make sure that all vehicles will require charging
        #    percent_leave=100

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


    with open(testdata_parameters.filename, "w") as f:
        json.dump(bev_data, f, indent=4)

def main():
    parser = argparse.ArgumentParser(
                    prog='Solar Charging Testdata Generator',
                    description='Generates a json file containing vehicles with distributed arrival time, leave time, battery size, battery level (arrive and leave) and max. charging power.')
    parser.add_argument('-f', '--file', type=str)
    parser.add_argument('-c', '--count', type=int)
    parser.add_argument('-s', '--socmaxdistribution', type=str)
    parser.add_argument('-m', '--socmeanarrival', type=float)
    parser.add_argument('-p', '--chargepowermax', type=str)
    parser.add_argument('-t', '--meanparkingtime', type=float)
    parser.add_argument('-k', '--parkingtimeparameter', type=float)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()

    socmaxdistribution = 0
    if(args.socmaxdistribution!=None):
        try:
            socmaxdistribution = list(eval(args.socmaxdistribution))
        except:
            print("Error: Failed to parse SoC distribution.")
            exit()
    
    testdata_parameters = TestdataParameters()
    if args.file is not None:
        testdata_parameters.filename = args.file
    if args.count is not None:
        testdata_parameters.vehiclecount = args.count
    if args.socmaxdistribution is not None:
        testdata_parameters.socmaxdistribution = socmaxdistribution
    if args.socmeanarrival is not None:
        testdata_parameters.socmeanarrival = args.socmeanarrival
    if args.chargepowermax is not None:
        testdata_parameters.chargepowermax = args.chargepowermax
    if args.meanparkingtime is not None:
        testdata_parameters.meanparkingtime = args.meanparkingtime
    if args.seed is not None:
        testdata_parameters.seed = args.seed
    if args.parkingtimeparameter is not None:
        testdata_parameters.parkingtimeparameter = args.parkingtimeparameter
    generate_testdata(testdata_parameters)
if __name__ == "__main__":
    main()