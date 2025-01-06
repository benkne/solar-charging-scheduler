from datetime import datetime, timedelta

class SchedulingParameters:
    def __init__(self,
                 flatten = False,
                 overcharge = True,
                 reducemax = True
                ):
        self.flatten=flatten
        self.overcharge=overcharge
        self.reducemax=reducemax

    def parseSchedulingParameters(self, string: str):
        parameter_strings = string.split(",")
        for string in parameter_strings:
            keyval = string.split("=")
            key = keyval[0]
            val = keyval[1]
            if(key=='flatten'):
                self.flatten = val.lower() == 'true'
            elif(key=='overcharge'):
                self.overcharge = val.lower() == 'true'
            elif(key=='reducemax'):
                self.reducemax = val.lower() == 'true'

    def to_dict(self):
        return {
            "flatten": self.flatten,
            "overcharge": self.overcharge,
            "reducemax": self.reducemax
        }
    
    @staticmethod
    def from_dict(data: dict) -> "SchedulingParameters":
        return SchedulingParameters(
            flatten=data.get("flatten", False),
            overcharge=data.get("overcharge", True),
            reducemax=data.get("reducemax", True)
        )

class SimulationParameters:
    def __init__(self,
                 storepath = 'test\\simulation.json',
                 testdatapath = 'test\\testdata.json',
                 resultpath = 'results\\result.csv',
                 exportresults = False,
                 hideresults = False,
                 simulationdate = datetime.now() + timedelta(days=1),
                 peakSolarPower = 300_000, # 300 kWp
                 peakPowerForecast = 4_196_000_000, # 4196 MW Spitzenwert im Jahr 2024 (juni) / energy-charts.info
                 smoothForecast = True,
                 forecastapi = "https://api.energy-charts.info/public_power_forecast?country=at&production_type=solar&forecast_type=current",
                 scheduling = SchedulingParameters()
                ):
        self.storepath = storepath
        self.testdatapath = testdatapath
        self.resultpath = resultpath
        self.exportresults = exportresults
        self.hideresults = hideresults
        self.simulationdate = datetime(simulationdate.year,simulationdate.month,simulationdate.day)
        self.peakSolarPower = peakSolarPower
        self.peakPowerForecast = peakPowerForecast
        self.smoothForecast = smoothForecast
        self.forecastapi = forecastapi
        self.scheduling = scheduling

    def to_dict(self):
        return {
            "storepath": self.storepath,
            "testdatapath": self.testdatapath,
            "resultpath": self.resultpath,
            "exportresults": self.exportresults,
            "hideresults": self.hideresults,
            "simulationdate": self.simulationdate.timestamp(),
            "peakSolarPower": self.peakSolarPower,
            "peakPowerForecast": self.peakPowerForecast,
            "smoothForecast": self.smoothForecast,
            "forecastapi": self.forecastapi,
            "scheduling": self.scheduling.to_dict()
        }
    
    @staticmethod
    def from_dict(data: dict) -> "SimulationParameters":
        scheduling = SchedulingParameters.from_dict(data["scheduling"])
        simulationdate = datetime.fromtimestamp(data["simulationdate"])
        
        return SimulationParameters(
            storepath=data["storepath"],
            testdatapath=data["testdatapath"],
            resultpath=data["resultpath"],
            exportresults=data["exportresults"],
            hideresults=data["hideresults"],
            simulationdate=simulationdate,
            peakSolarPower=data["peakSolarPower"],
            peakPowerForecast=data["peakPowerForecast"],
            smoothForecast=data["smoothForecast"],
            forecastapi=data["forecastapi"],
            scheduling=scheduling
        )