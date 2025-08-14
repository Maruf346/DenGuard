import os, datetime
import requests
from django.conf import settings
from django.utils import timezone

API_KEY = settings.TOMORROW_API_KEY
BASE = "https://api.tomorrow.io"

# minimal city→lat/lon (add more as you like)
CITY_COORDS = {
    "Dhaka": (23.8103, 90.4125),
    "Chattogram": (22.3569, 91.7832),
    "Rajshahi": (24.3740, 88.6010),
}

def _get_coords(city_or_latlon):
    if isinstance(city_or_latlon, str):
        return CITY_COORDS.get(city_or_latlon, CITY_COORDS["Dhaka"])
    return city_or_latlon  # (lat, lon)

def _get_today_range():
    # “today” in Asia/Dhaka (start & end for daily timesteps)
    now_bd = timezone.localtime()
    start = now_bd.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + datetime.timedelta(days=1)
    return start.isoformat(), end.isoformat()

def fetch_daily_weather(lat, lon):
    """
    Weather daily forecast for today (metric units).
    We’ll request a set of fields that cover your table.
    """
    url = f"{BASE}/v4/weather/forecast"
    params = {
        "location": f"{lat},{lon}",
        "units": "metric",
        "timesteps": "1d",
        "apikey": API_KEY,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    # The daily slice is usually at data["timelines"]["daily"][0]["values"]
    try:
        daily0 = data["timelines"]["daily"][0]
        values = daily0["values"]
        # Common fields available on daily forecast:
        # temperatureMax, temperatureMin, temperatureAvg, humidityAvg,
        # precipitationAccumulation, windSpeedAvg, windDirectionAvg, uvIndexMax/Avg
        return {
            "date": daily0["time"][:10],
            "temp_min_C": values.get("temperatureMin"),
            "temp_max_C": values.get("temperatureMax"),
            "temp_mean_C": values.get("temperatureAvg"),
            "humidity_percent": values.get("humidityAvg"),
            "rainfall_mm": values.get("precipitationAccumulation"),
            "wind_speed_kph": values.get("windSpeedAvg"),
            "wind_direction_deg": values.get("windDirectionAvg"),
            "uv_index": values.get("uvIndexMax") or values.get("uvIndexAvg"),
        }
    except Exception:
        return None

def fetch_daily_air(lat, lon):
    """
    Air-quality daily forecast. If your plan doesn’t include the dedicated
    air-quality endpoint, you can also get AQ fields via the Timelines API.
    """
    # Try dedicated air-quality forecast first:
    url = f"{BASE}/v4/air-quality/forecast"
    params = {
        "location": f"{lat},{lon}",
        "timesteps": "1d",
        "apikey": API_KEY,
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code == 200:
        data = r.json()
        try:
            daily0 = data["timelines"]["daily"][0]
            v = daily0["values"]
            # Typical keys: pm10Avg, pm25Avg, epaIndexAvg (may vary by plan/region)
            return {
                "pm25": v.get("pm25Avg"),
                "pm10": v.get("pm10Avg"),
                "aqi":  v.get("epaIndexAvg") or v.get("epaHealthConcernAvg"),
            }
        except Exception:
            pass

    # Fallback: use Weather Timelines with air-quality fields if your plan allows
    url = f"{BASE}/v4/timelines"
    start, end = _get_today_range()
    params = {
        "location": f"{lat},{lon}",
        "timesteps": "1d",
        "units": "metric",
        "apikey": API_KEY,
        "fields": "pm25,pm10,epaIndex",   # field names per docs/plan
        "startTime": start,
        "endTime": end,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    try:
        daily0 = data["data"]["timelines"][0]["intervals"][0]
        v = daily0["values"]
        return {
            "pm25": v.get("pm25"),
            "pm10": v.get("pm10"),
            "aqi":  v.get("epaIndex"),
        }
    except Exception:
        return None

def risk_level(row):
    # Simple heuristic (tune for your project)
    rain = (row.get("rainfall_mm") or 0) >= 10
    humid = (row.get("humidity_percent") or 0) >= 75
    temp_ok = 25 <= (row.get("temp_mean_C") or 0) <= 33
    aqi = (row.get("aqi") or 0)
    uv = (row.get("uv_index") or 0)

    score = 0
    score += 1 if rain else 0
    score += 1 if humid else 0
    score += 1 if temp_ok else 0
    score += 1 if aqi >= 80 else 0
    score += 1 if uv >= 7 else 0

    if score >= 4: return "High"
    if score >= 2: return "Moderate"
    return "Low"

def get_today_weather_and_air(city="Dhaka"):
    lat, lon = _get_coords(city)
    w = fetch_daily_weather(lat, lon) or {}
    aq = fetch_daily_air(lat, lon) or {}
    row = {
        "date": w.get("date"),
        "location": city,
        **w, **aq
    }
    row["risk_level"] = risk_level(row)
    return row
