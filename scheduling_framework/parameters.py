from datetime import datetime, timedelta

class SchedulingParameters:
    def __init__(self,
                 flatten = False,
                 overcharge = True,
                 reducemax = True,
                 allowgrid = False
                ):
        self.flatten=flatten
        self.overcharge=overcharge
        self.reducemax=reducemax
        self.allowgrid=allowgrid

    def to_dict(self):
        return {
            "flatten": self.flatten,
            "overcharge": self.overcharge,
            "reducemax": self.reducemax,
            "allowgrid": self.allowgrid
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
                 storepath = 'test/simulation.json',
                 testdatapath = 'test/testdata.json',
                 resultpath = 'results/result.csv',
                 exportresults = False,
                 hideresults = False,
                 simulationdate = datetime.now() + timedelta(days=1),
                 peakSolarPower = 300_000, # 300 kWp
                 peakPowerForecast = 4_196_000_000, # 4196 MW peak in June 2024 / energy-charts.info
                 smoothForecast = True,
                 forecastapi = None,
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

        self.update_forecastapi()

    def update_forecastapi(self):
        begindate = self.simulationdate - timedelta(days=1)
        enddate = self.simulationdate + timedelta(days=1)
        day_string_begin=str(begindate.year)+"-"+str(begindate.month)+"-"+str(begindate.day)
        day_string_begin=datetime.strptime(day_string_begin, "%Y-%m-%d").strftime("%Y-%m-%d")
        day_string_end=str(enddate.year)+"-"+str(enddate.month)+"-"+str(enddate.day)
        day_string_end=datetime.strptime(day_string_end, "%Y-%m-%d").strftime("%Y-%m-%d")
        self.forecastapi = f"https://api.energy-charts.info/public_power_forecast?country=at&production_type=solar&forecast_type=current&start={day_string_begin}&end={day_string_end}"

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