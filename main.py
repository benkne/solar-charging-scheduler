import energy_charts_api
from forecast_power import Forecast
import datetime
import matplotlib.pyplot as plt

simulationdate = datetime.datetime.now() + datetime.timedelta(days=1)

def visualize_forecast(forecast: Forecast):
    plt.figure(figsize=(10, 6))
    forecast.visualize(plt)

    plt.title('Solar Power Forecast', fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    plt.tight_layout()  
    plt.show()

forecast: Forecast = energy_charts_api.api_request()
forecast.scale(50_000, 6_395_000_000)
visualize_forecast(forecast)
