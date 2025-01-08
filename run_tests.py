import datetime

from scheduling_framework.parameters import SimulationParameters
from generate_testdata import generate_testdata,TestdataParameters
from run import simulate

ITERATIONS=100

def run_tests():
    simulation_parameters = SimulationParameters()
    simulation_parameters.peakSolarPower=200_000
    simulation_parameters.hideresults=True
    simulation_parameters.exportresults=True
    simulation_parameters.simulationdate=datetime.datetime(2025,1,9)


    testdata_parameters = TestdataParameters()
    testdata_parameters.vehiclecount=12
    testdata_parameters.filename="test/testdata.json"
    for i in range(0,100):
        testdata_parameters.seed=i

        generate_testdata(testdata_parameters)
        
        simulate(simulation_parameters)

if __name__ == "__main__":
    run_tests()