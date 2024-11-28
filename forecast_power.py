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
        return f"{self.timestamp}, {self.forecast_value}"

class Forecast:
    def __init__(self, datapoints: list[Datapoint]):
        self.datapoints = datapoints

    def __str__(self) -> str:
        return "\n".join(str(datapoint) for datapoint in self.datapoints)

    def visualize(self, plt: plt):
        times = [datapoint.timestamp for datapoint in self.datapoints]
        forecast_values = [datapoint.forecast_value for datapoint in self.datapoints]
        plt.step(times, forecast_values, where='post', marker='', linestyle='-', color='y',linewidth=2.0,label="scaled solar power forecast")

    def scale(self, scaledpeak: float, austrianpeak: float):
        if scaledpeak<=0 or austrianpeak<=0:
            raise Exception("Scaling values must be greater than 0.")
        
        for datapoint in self.datapoints:
            scaled_value = (datapoint.forecast_value / austrianpeak) * scaledpeak
            datapoint.forecast_value = scaled_value

    def get_forecast_by_timestamp(self, time: datetime.datetime) -> float:
        for i in range(len(self.datapoints) - 1):
            current_point = self.datapoints[i]
            next_point = self.datapoints[i+1]
            if current_point.timestamp <= time and next_point.timestamp > time:
                return current_point.forecast_value+(next_point.forecast_value-current_point.forecast_value)*(time-current_point.timestamp).total_seconds()/60/15
        return 0
    
    def getDailyForecast(self, datetime: datetime.datetime):
        datapoints = []
        date = datetime.date()
        for datapoint in self.datapoints:
            if(date==datapoint.timestamp.date()):
                datapoints.append(datapoint)

        return Forecast(datapoints)
    
    def getDailyPeak(self, datetime: datetime.datetime):
        date = datetime.date()
        peak=0
        for datapoint in self.datapoints:
            if(date==datapoint.timestamp.date()):
                if peak < datapoint.forecast_value:
                    peak = datapoint.forecast_value
        return peak
    
    def getTimesteps(self) -> List[datetime.datetime]:
        return [d.timestamp for d in self.datapoints]
    
    def getValues(self) -> List[float]:
        return [d.forecast_value for d in self.datapoints]
    
    def visualizeGauss(self, plt, simulationdate):
        guesstime = datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,hour=12)
        gauss = lambda x,a,mu,sigma: a * np.exp(-(x - mu)**2 / (2 * sigma**2))
        
        day_time = [datetime.datetime.timestamp(time) for time in self.getDailyForecast(guesstime).getTimesteps()]
        day_values = self.getDailyForecast(guesstime).getValues()

        startTimeIndex = 0
        endTimeIndex = 0
        for i in range(0,len(day_time)):
            if(day_values[i]!=0 and startTimeIndex==0):
                startTimeIndex=i
            if(day_values[-i-1]!=0 and endTimeIndex==0):
                endTimeIndex=len(day_time)-i

        # extend time for 15 Minutes
        startTimeIndex=startTimeIndex-1
        endTimeIndex=endTimeIndex+1

        day_time = day_time[startTimeIndex:endTimeIndex]
        day_values = day_values[startTimeIndex:endTimeIndex]

        max_value = np.max(day_values)

        initial_guess = [max_value, datetime.datetime.timestamp(guesstime), 10000]  # Initial guess for [a, mu, sigma]
        params, covariance = curve_fit(gauss, 
                                    day_time, 
                                    day_values, 
                                    p0=initial_guess,
                                    bounds = (0, [np.inf, np.inf, np.inf]))

        a_fit, mu_fit, sigma_fit = params

        x_values = np.arange(day_time[0], day_time[-1]+1,60)
        y_values = [gauss(x, a_fit, mu_fit, sigma_fit) for x in x_values]

        plt.plot([datetime.datetime.fromtimestamp(x) for x in x_values], y_values, marker='', linestyle='--', color='b',label="gauss fit of forecast")

    def visualizeSin2(self, plt, simulationdate):
        guesstime = datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,hour=12)
        sin2 = lambda x,a,b,c: a * np.sin(np.pi*(x-c-1/b/2)*b) * np.sin(np.pi*(x-c-1/b/2)*b)

        
        day_time = [datetime.datetime.timestamp(time) for time in self.getDailyForecast(guesstime).getTimesteps()]
        day_values = self.getDailyForecast(guesstime).getValues()

        startTimeIndex = 0
        endTimeIndex = 0
        for i in range(0,len(day_time)):
            if(day_values[i]!=0 and startTimeIndex==0):
                startTimeIndex=i
            if(day_values[-i-1]!=0 and endTimeIndex==0):
                endTimeIndex=len(day_time)-i

        # extend time for 15 Minutes
        startTimeIndex=startTimeIndex-1
        endTimeIndex=endTimeIndex+1

        day_time = day_time[startTimeIndex:endTimeIndex]
        day_values = day_values[startTimeIndex:endTimeIndex]

        max_value = np.max(day_values)

        initial_guess = [max_value, 1/(60*60*10), datetime.datetime.timestamp(guesstime)]
        params, covariance = curve_fit(sin2, 
                                    day_time, 
                                    day_values, 
                                    p0=initial_guess,
                                    bounds = (0, [np.inf, np.inf, np.inf]))
        a_fit, b_fit, c_fit = params

        x_values = np.arange(day_time[0], day_time[-1]+1,60)
        y_values = [sin2(x, a_fit, b_fit, c_fit) for x in x_values]

        plt.plot([datetime.datetime.fromtimestamp(x) for x in x_values], y_values, marker='', linestyle='--', color='g',label="sin² fit of forecast")