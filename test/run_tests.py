from generate_testdata import generate_testdata,TestdataParameters
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import simulate,SimulationParameters

ITERATIONS=100

simulation_parameters = SimulationParameters()
simulation_parameters.peakSolarPower=300_000
simulation_parameters.hideresults=True
simulation_parameters.exportresults=True
simulation_parameters.simulationdate=datetime.datetime(2024,11,30)

testdata_parameters = TestdataParameters()
testdata_parameters.vehiclecount=12
testdata_parameters.filename=".\\test\\testdata.json"
for i in range(0,100):
    testdata_parameters.seed=i

    generate_testdata(testdata_parameters)
    
    simulate(simulation_parameters)

