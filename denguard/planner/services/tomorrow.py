# services/tomorrow.py
import requests
from django.conf import settings

def get_today_weather_and_air(city):
    """
    Fetch current weather and air quality from Tomorrow.io Realtime API
    """
    api_key = settings.TOMORROW_API_KEY
    if not api_key:
        return {"error": "API key not set"}

    # You can use city name directly or latitude,longitude
    location = city  # or "23.8103,90.4125" for Dhaka coordinates

    fields = [
        "temperature",         # Current temperature
        "temperatureApparent", # Feels like
        "humidity",            # %
        "windSpeed",           # m/s
        "windDirection",       # deg
        "uvIndex",             # UV index
        "precipitationIntensity",  # mm/hr
        "particulateMatter25", # PM2.5
        "particulateMatter10", # PM10
        "epaIndex"             # AQI
    ]

    url = (
        f"https://api.tomorrow.io/v4/weather/realtime"
        f"?location={location}"
        f"&units=metric"
        f"&fields={','.join(fields)}"
        f"&apikey={api_key}"
    )

    try:
        response = requests.get(url, headers={"accept": "application/json"})
        response.raise_for_status()
        raw = response.json()

        # Extract relevant data
        values = raw.get("data", {}).get("values", {})
        data = {
            "date": raw.get("data", {}).get("time", "").split("T")[0],
            "location": city,
            "rainfall_mm": values.get("precipitationIntensity"),
            "humidity_percent": values.get("humidity"),
            "temp_min_C": values.get("temperature"),  # realtime only has current temp
            "temp_max_C": values.get("temperature"),
            "temp_mean_C": values.get("temperature"),
            "wind_speed_kph": round(values.get("windSpeed", 0) * 3.6, 2),  # m/s → km/h
            "wind_direction_deg": values.get("windDirection"),
            "uv_index": values.get("uvIndex"),
            "pm25": values.get("particulateMatter25"),
            "pm10": values.get("particulateMatter10"),
            "aqi": values.get("epaIndex"),
            "risk_level": (
                "High" if values.get("epaIndex", 0) >= 100 else "Low"
            )
        }
        return data

    except requests.RequestException as e:
        return {"error": str(e)}
