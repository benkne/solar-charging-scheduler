import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List

from scheduling_framework.forecast_power import Forecast

# the renewable power production based on the forecast
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
    
    # returns the energy from the daily production in Watts
    def getEnergy(self) -> float:
        return sum(self.production)/60
    
    # visualizes the renewable power production
    def visualize(self, plt: plt):
        times = [self.day+timedelta(minutes=t) for t in range(0,60*24)]
        plt.step(times, self.production, where='post', marker='', linestyle='-', color='y',linewidth=2.0,label="scaled solar power forecast")

    # returns the power curve of the remaining renewable power
    @staticmethod
    def renewable_available(production: List[float], powerUsage: List[float]):
        assert(len(production)==len(powerUsage))

        renewable_power = production
        renewable_power = np.subtract(renewable_power,powerUsage)
        renewable_power = np.maximum(renewable_power,0)
        return renewable_power