import datetime
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np
from typing import List

class Datapoint:
    def __init__(self, timestamp: datetime.datetime, forecast_value: float):
        self.timestamp: datetime.datetime = timestamp
        self.forecast_value: float = forecast_value
    def __str__(self) -> str:
        return f"{self.timestamp} {self.forecast_value}"

class Forecast:
    def __init__(self, datapoints: list[Datapoint]):
        self.datapoints = datapoints

    def __str__(self) -> str:
        return "\n".join(str(datapoint) for datapoint in self.datapoints)

    def visualize(self, plt: plt):
        times = [datapoint.timestamp for datapoint in self.datapoints]
        forecast_values = [datapoint.forecast_value for datapoint in self.datapoints]
        plt.plot(times, forecast_values, marker='o', linestyle='-', color='y')

    def scale(self, scaledpeak: float, austrianpeak: float):
        if scaledpeak<=0 or austrianpeak<=0:
            raise Exception("Scaling values must be greater than 0.")
        
        for datapoint in self.datapoints:
            scaled_value = (datapoint.forecast_value / austrianpeak) * scaledpeak
            datapoint.forecast_value = scaled_value

    def get_forecast_by_timestamp(self, time: datetime.datetime) -> float:
        for datapoint in self.datapoints:
            if datapoint.timestamp == time:
                return datapoint.forecast_value
        return None
    
    def getDailyForecast(self, datetime: datetime.datetime):
        datapoints = []
        date = datetime.date()
        for datapoint in self.datapoints:
            if(date==datapoint.timestamp.date()):
                datapoints.append(datapoint)

        return Forecast(datapoints)
    
    def getTimesteps(self) -> List[datetime.datetime]:
        return [d.timestamp for d in self.datapoints]
    
    def getValues(self) -> List[float]:
        return [d.forecast_value for d in self.datapoints]
    
    def visualizeGauss(self, plt, simulationdate):
        guesstime = datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,hour=12)
        gauss = lambda x,a,mu,sigma: a * np.exp(-(x - mu)**2 / (2 * sigma**2))

        
        day_time = [datetime.datetime.timestamp(time) for time in self.getDailyForecast(guesstime).getTimesteps()]
        day_values = self.getDailyForecast(guesstime).getValues()

        max_value = np.max(day_values)

        initial_guess = [max_value, datetime.datetime.timestamp(guesstime), 10000]  # Initial guess for [a, mu, sigma]
        params, covariance = curve_fit(gauss, 
                                    day_time, 
                                    day_values, 
                                    p0=initial_guess,
                                    bounds = (0, [np.inf, np.inf, np.inf]))

        a_fit, mu_fit, sigma_fit = params

        start_time = int(datetime.datetime(simulationdate.year, simulationdate.month, simulationdate.day).timestamp())
        end_time = int(datetime.datetime(simulationdate.year, simulationdate.month, simulationdate.day, 23, 59).timestamp())

        x_values = np.arange(start_time, end_time+1,60)
        y_values = [gauss(x, a_fit, mu_fit, sigma_fit) for x in x_values]

        plt.plot([datetime.datetime.fromtimestamp(x) for x in x_values], y_values, marker='', linestyle='--', color='b')