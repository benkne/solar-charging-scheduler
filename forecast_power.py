import datetime
import matplotlib.pyplot as plt

class Datapoint:
    def __init__(self, timestamp: datetime, forecast_values: float):
        self.timestamp: datetime = timestamp
        self.forecast_values: float = forecast_values
    def __str__(self) -> str:
        return f"{self.timestamp} {self.forecast_values}"

class Forecast:
    def __init__(self, datapoints: list[Datapoint]):
        self.datapoints = datapoints

    def __str__(self) -> str:
        return "\n".join(str(datapoint) for datapoint in self.datapoints)

    def visualize(self, plt: plt):
        times = [datapoint.timestamp for datapoint in self.datapoints]
        forecast_values = [datapoint.forecast_values for datapoint in self.datapoints]
        plt.plot(times, forecast_values, marker='o', linestyle='-', color='y')

    def scale(self, scaledpeak: float, austrianpeak: float):
        if scaledpeak<=0 or austrianpeak<=0:
            raise Exception("Scaling values must be greater than 0.")
        
        for datapoint in self.datapoints:
            scaled_value = (datapoint.forecast_values / austrianpeak) * scaledpeak
            datapoint.forecast_values = scaled_value