import energy_charts_api
from forecast_power import Forecast
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches

simulationdate = datetime.datetime.now() + datetime.timedelta(days=1)

def visualize(forecast: Forecast):
    plt.figure(figsize=(10, 6))
    forecast.visualize(plt)

    plt.title('Solar Power Forecast (Austria)', fontsize=16)
    plt.xlabel('Time (CEST)', fontsize=12)
    plt.ylabel('Forecasted Power (W)', fontsize=12)
    plt.grid(True)
    plt.xticks(rotation=45)

    ax = plt.gca()

    time_start = simulationdate
    power_start = 0   
    width = datetime.timedelta(hours=2) 
    height = 5_000 

    rect = patches.Rectangle((time_start, power_start), width, height, linewidth=1, edgecolor='r', facecolor='none')

    ax.add_patch(rect)

    plt.tight_layout()  
    plt.show()

print(simulationdate)

forecast: Forecast = energy_charts_api.api_request()
forecast.scale(50_000, 6_395_000_000)
#print(forecast)
visualize(forecast)
