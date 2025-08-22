# services/tomorrow.py  (Now uses Open-Meteo + NASA POWER instead of Tomorrow.io)
import joblib
import requests
from datetime import datetime, timedelta
import numpy as np

def get_today_weather_and_air(city):
    """
    Fetch today's weather and air quality using Open-Meteo + NASA POWER APIs
    Returns data in the same structure as the old Tomorrow.io version.
    """
    # City → Coordinates mapping (extend as needed)
    city_coords = {
        # Bangladesh
        "Dhaka": (23.8103, 90.4125),
        "Chittagong": (22.3569, 91.7832),
        "Khulna": (22.8456, 89.5403),

        # North America
        "Toronto": (43.65107, -79.347015),
        "New York": (40.7128, -74.0060),
        "Los Angeles": (34.0522, -118.2437),
        "Chicago": (41.8781, -87.6298),
        "Mexico City": (19.4326, -99.1332),

        # Europe
        "London": (51.5074, -0.1278),
        "Paris": (48.8566, 2.3522),
        "Berlin": (52.5200, 13.4050),
        "Rome": (41.9028, 12.4964),
        "Madrid": (40.4168, -3.7038),

        # Asia
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777),
        "Tokyo": (35.6762, 139.6503),
        "Beijing": (39.9042, 116.4074),
        "Bangkok": (13.7563, 100.5018),
        "Singapore": (1.3521, 103.8198),

        # Oceania
        "Sydney": ( -33.8688, 151.2093 ),
        "Melbourne": ( -37.8136, 144.9631 ),

        # Middle East
        "Dubai": (25.276987, 55.296249),
        "Riyadh": (24.7136, 46.6753),
        "Istanbul": (41.0082, 28.9784),

        # Africa
        "Cairo": (30.0444, 31.2357),
        "Johannesburg": (-26.2041, 28.0473),
        "Nairobi": (-1.2921, 36.8219)
    }

    lat, lon = city_coords.get(city, (23.8103, 90.4125))  # Default: Dhaka

    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # 1 Open-Meteo daily weather
        meteo_url = (
            "https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
            "precipitation_sum,wind_speed_10m_max,wind_direction_10m_dominant"
            "&timezone=auto"
        )
        meteo_data = requests.get(meteo_url).json()
        daily = meteo_data.get("daily", {})

        # 2 Open-Meteo hourly air quality
        air_url = (
            "https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lat}&longitude={lon}"
            "&hourly=pm10,pm2_5,us_aqi"
            "&timezone=auto"
        )
        air_data = requests.get(air_url).json()
        hourly = air_data.get("hourly", {})

        # Use today's last available hourly value for PM & AQI
        if "time" in hourly and hourly["time"]:
            today_mask = [i for i, t in enumerate(hourly["time"]) if t.startswith(today)]
            if today_mask:
                pm25_val = sum(hourly["pm2_5"][i] for i in today_mask) / len(today_mask)
                pm10_val = sum(hourly["pm10"][i] for i in today_mask) / len(today_mask)
                aqi_val  = sum(hourly["us_aqi"][i] for i in today_mask) / len(today_mask)
            else:
                pm25_val = pm10_val = aqi_val = None
        else:
            pm25_val = pm10_val = aqi_val = None


        # 3 NASA POWER humidity & UV
        today_nasa = datetime.utcnow().strftime("%Y%m%d")

        nasa_params = {
            "parameters": "RH2M,ALLSKY_SFC_UVB",  # same params you used in historical code
            "start": today_nasa,
            "end": today_nasa,
            "latitude": lat,
            "longitude": lon,
            "community": "AG",          # add this (was in your working code)
            "format": "JSON",
            "time-standard": "UTC"      # add this too (was in your working code)
        }

        resp = requests.get(
            "https://power.larc.nasa.gov/api/temporal/daily/point",
            params=nasa_params,
            timeout=20
        )
        resp.raise_for_status()
        payload = resp.json().get("properties", {}).get("parameter", {})

        # Read by exact date key (YYYYMMDD) instead of list(...)[0]
        humidity_raw = (payload.get("RH2M", {}) or {}).get(today_nasa)
        uv_raw       = (payload.get("ALLSKY_SFC_UVB", {}) or {}).get(today_nasa)

        humidity = float(humidity_raw) if humidity_raw is not None else None
        uv_index = float(uv_raw) if uv_raw is not None else None

        # Fallback to yesterday if today's daily isn’t published yet
        if humidity is None or humidity == -999.0 and uv_index is None or uv_index == -999.0:
            yday_nasa = (datetime.utcnow() - timedelta(days=85)).strftime("%Y%m%d")
            nasa_params["start"] = nasa_params["end"] = yday_nasa
            resp = requests.get(
                "https://power.larc.nasa.gov/api/temporal/daily/point",
                params=nasa_params,
                timeout=20
            )
            resp.raise_for_status()
            payload = resp.json().get("properties", {}).get("parameter", {})
            humidity_raw = (payload.get("RH2M", {}) or {}).get(yday_nasa)
            uv_raw       = (payload.get("ALLSKY_SFC_UVB", {}) or {}).get(yday_nasa)
            humidity = float(humidity_raw) if humidity_raw is not None else None
            uv_index = float(uv_raw) if uv_raw is not None else None


        import pandas as pd

        # Load trained model
        model = joblib.load("planner/model/svm_weather_model.pkl")

        # Define column names (same as in training CSV, order matters)
        feature_columns = [
            "date", "location", "rainfall_mm", "humidity_percent",
            "temp_min_C", "temp_max_C", "temp_mean_C",
            "wind_speed_kph", "wind_direction_deg",
            "uv_index", "pm25", "pm10", "aqi"
        ]

        # Collect today's feature values
        features = [
            today,
            city,
            daily.get("precipitation_sum", [0.0])[0] or 0.2,
            humidity or 50.0,
            daily.get("temperature_2m_min", [25.0])[0] or 25.0,
            daily.get("temperature_2m_max", [30.0])[0] or 30.0,
            daily.get("temperature_2m_mean", [27.0])[0] or 27.0,
            daily.get("wind_speed_10m_max", [5.0])[0] or 10.0,
            daily.get("wind_direction_10m_dominant", [180.0])[0] or 180.0,
            uv_index or 0.02,
            pm25_val or 70.0,
            pm10_val or 84.0,
            aqi_val or 76.0,
        ]

        # Build DataFrame with correct columns
        X_today = pd.DataFrame([features], columns=feature_columns)

        # Predict risk
        risk_prediction = model.predict(X_today)[0]


        # Build result keeping the same keys as before
        data = {
            "date": today,
            "location": city,
            "rainfall_mm": daily.get("precipitation_sum", [None])[0],
            "humidity_percent": humidity,
            "temp_min_C": daily.get("temperature_2m_min", [None])[0],
            "temp_max_C": daily.get("temperature_2m_max", [None])[0],
            "temp_mean_C": daily.get("temperature_2m_mean", [None])[0],
            "wind_speed_kph": daily.get("wind_speed_10m_max", [None])[0],
            "wind_direction_deg": daily.get("wind_direction_10m_dominant", [None])[0],
            "uv_index": uv_index,
            "pm25": pm25_val,
            "pm10": pm10_val,
            "aqi": aqi_val,
            "risk_level": risk_prediction
        }
        return data

    except requests.RequestException as e:
        return {"error": str(e)}
