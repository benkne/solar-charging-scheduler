import energy_charts_api
from forecast_power import Forecast
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches

simulationdate = datetime.datetime.now() + datetime.timedelta(days=1)

def visualize_forecast(forecast: Forecast):
    plt.figure(figsize=(10, 6))
    forecast.visualize(plt)

    plt.title('Solar Power Forecast', fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    plt.xlim(datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,0,0),datetime.datetime(simulationdate.year,simulationdate.month,simulationdate.day,23,59))
    plt.tight_layout()  
    plt.show()

print(simulationdate)

forecast: Forecast = energy_charts_api.api_request()
forecast.scale(50_000, 6_395_000_000)
#print(forecast)
visualize_forecast(forecast)
