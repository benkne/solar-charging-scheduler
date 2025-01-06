from forecast_power import Forecast
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import List
import numpy as np

class Production:
    def __init__(self, forecast: Forecast, timestamp: datetime, smooth: bool = True):
        self.day = datetime(timestamp.year, timestamp.month, timestamp.day)
        forecast = forecast.getDailyForecast(timestamp)
        self.production: list[float] = []
        time = self.day
        while time < self.day+timedelta(days=1):
            self.production.append(forecast.get_forecast_by_timestamp(time, smooth))
            time=time+timedelta(minutes=1)
    def __str__(self) -> str:
        return str(self.production)
    
    def getEnergy(self) -> float:
        return sum(self.production)/60
    
    def visualize(self, plt: plt):
        times = [self.day+timedelta(minutes=t) for t in range(0,60*24)]
        plt.step(times, self.production, where='post', marker='', linestyle='-', color='y',linewidth=2.0,label="scaled solar power forecast")

    @staticmethod
    def renewable_available(production: List[float], powerUsage: List[float]):
        assert(len(production)==len(powerUsage))

        renewable_power = production
        renewable_power = np.subtract(renewable_power,powerUsage)
        renewable_power = np.maximum(renewable_power,0)
        return renewable_power