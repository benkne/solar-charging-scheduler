import requests
import datetime
import pytz
from forecast_power import Datapoint,Forecast

url = "https://api.energy-charts.info/public_power_forecast?country=at&production_type=solar&forecast_type=current"


def convert_unix_to_cest(unix_timestamp: int) -> datetime:
    dt_utc = datetime.datetime.utcfromtimestamp(unix_timestamp)
    
    utc_zone = pytz.utc

    dt_utc = utc_zone.localize(dt_utc)
    cest_zone = pytz.timezone('Europe/Berlin')
    dt_cest = dt_utc.astimezone(cest_zone)
    
    return dt_cest.replace(tzinfo=None)

def api_request() -> Forecast:

    try:
        response = requests.get(url, verify=True)
    except requests.exceptions.SSLError:
        print("SSL verification failed, retrying with verify=False...")
        response = requests.get(url, verify=False)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit()

    if response.status_code == 200:
        data = response.json()
        
        unix_seconds: int = data.get('unix_seconds', [])
        
        forecast_values = data.get('forecast_values', [])
        forecast_values = [value*1_000_000 for value in forecast_values] # scale MW to W

        times = [convert_unix_to_cest(seconds) for seconds in unix_seconds]

        datapoints = [Datapoint(times[i],forecast_values[i]) for i in range(0,len(times))]
        forecast = Forecast(datapoints)
        
        return forecast
    else:
        raise Exception(f"Error: {response.status_code}. Failed to fetch data.") 

if __name__ == "__main__":
    print(api_request())