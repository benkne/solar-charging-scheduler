import datetime

from scheduling_framework.parameters import SimulationParameters
from generate_testdata import generate_testdata,TestdataParameters
from run import simulate

ITERATIONS=10

YEAR=2024
MONTH=2
DAYS=29

def run_tests():
    simulation_parameters = SimulationParameters()
    simulation_parameters.peakSolarPower=150_000
    simulation_parameters.hideresults=True
    simulation_parameters.exportresults=True
    simulation_parameters.scheduling.allowgrid=False
    simulation_parameters.scheduling.flatten=False
    simulation_parameters.scheduling.overcharge=False
    simulation_parameters.scheduling.reducemax=True

    testdata_parameters = TestdataParameters()
    testdata_parameters.vehiclecount=10
    testdata_parameters.filename="test/testdata.json"
    
    for d in range(1,DAYS+1):
        for i in range(0,ITERATIONS):
            simulation_parameters.simulationdate=datetime.datetime(YEAR,MONTH,d)
            simulation_parameters.update_forecastapi()
            testdata_parameters.seed=i

            generate_testdata(testdata_parameters)
            
            simulate(simulation_parameters)

if __name__ == "__main__":
    run_tests()