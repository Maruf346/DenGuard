import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import time

# -------------------------
# CONFIGURATION
# -------------------------
LOCATIONS = [
    {"name": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
]

START_DATE = "2022-08-14"
END_DATE = "2025-07-19"
TIMEZONE = "Asia/Kolkata"

# Minimum number of observed hourly values in local day to accept daily mean (e.g. 18 -> 75%)
MIN_HOURLY_FOR_DAILY = 18

# Output filename
OUTPUT_CSV = "combined_dengue_data_openmeteo.csv"

# -------------------------
# SESSION (reuse TCP conn)
# -------------------------
session = requests.Session()
session.headers.update({"User-Agent": "data-collector-script/1.0"})

# -------------------------
# HELPERS: Open-Meteo weather archive (daily) & air-quality (hourly)
# -------------------------
def fetch_open_meteo_daily(lat, lon, start_date, end_date, timezone=TIMEZONE):
    """Return Open-Meteo daily archive fields dict (same shape as earlier)."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "windspeed_10m_max",
            "winddirection_10m_dominant",
            "shortwave_radiation_sum"
        ]),
        "timezone": timezone
    }
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("daily", {})

def fetch_open_meteo_pm_hourly(lat, lon, start_date, end_date, timezone=TIMEZONE):
    """
    Use Open-Meteo air-quality endpoint to fetch hourly pm2_5 and pm10 for the given date range.
    Returns (times, pm25_list, pm10_list) where times are ISO strings in requested timezone.
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "pm2_5,pm10",
        "timezone": timezone
    }
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    hourly = j.get("hourly", {})
    return hourly.get("time", []), hourly.get("pm2_5", []), hourly.get("pm10", [])

# -------------------------
# Helpers: aggregate hourly -> daily mean, counts, max
# -------------------------
def aggregate_hourly_to_daily(times, pm25_vals, pm10_vals, min_hours=MIN_HOURLY_FOR_DAILY):
    """
    Aggregate hourly arrays to daily statistics.
    Returns:
      pm25_daily: dict date->daily_mean or None
      pm10_daily: dict date->daily_mean or None
      pm25_max_daily: dict date->daily_max or None
      pm10_max_daily: dict date->daily_max or None
      hour_counts: dict date->int (observed hour count)
    """
    daily25 = defaultdict(list)
    daily10 = defaultdict(list)
    hour_counts = defaultdict(int)

    for t, p25, p10 in zip(times, pm25_vals, pm10_vals):
        if not t:
            continue
        date_key = t[:10]  # API returns times already in timezone param
        if p25 is not None:
            try:
                daily25[date_key].append(float(p25))
            except:
                pass
        if p10 is not None:
            try:
                daily10[date_key].append(float(p10))
            except:
                pass
        # count an hour if at least one pollutant value is present
        if (p25 is not None) or (p10 is not None):
            hour_counts[date_key] += 1

    pm25_daily = {}
    pm10_daily = {}
    pm25_max = {}
    pm10_max = {}

    all_dates = sorted(set(list(daily25.keys()) + list(daily10.keys()) + list(hour_counts.keys())))
    for d in all_dates:
        hcount = hour_counts.get(d, 0)
        if hcount < min_hours:
            pm25_daily[d] = None
            pm10_daily[d] = None
            pm25_max[d] = None
            pm10_max[d] = None
            continue

        if daily25.get(d):
            pm25_daily[d] = sum(daily25[d]) / len(daily25[d])
            pm25_max[d] = max(daily25[d])
        else:
            pm25_daily[d] = None
            pm25_max[d] = None

        if daily10.get(d):
            pm10_daily[d] = sum(daily10[d]) / len(daily10[d])
            pm10_max[d] = max(daily10[d])
        else:
            pm10_daily[d] = None
            pm10_max[d] = None

    return pm25_daily, pm10_daily, pm25_max, pm10_max, hour_counts

# -------------------------
# AQI calculation (US EPA breakpoints)
# -------------------------
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]

def aqi_subindex(conc, breakpoints):
    if conc is None:
        return None
    for bp_lo, bp_hi, i_lo, i_hi in breakpoints:
        if bp_lo <= conc <= bp_hi:
            aqi = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (conc - bp_lo) + i_lo
            return int(round(aqi))
    bp_lo, bp_hi, i_lo, i_hi = breakpoints[-1]
    aqi = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (conc - bp_lo) + i_lo
    return int(round(min(aqi, 500)))

def aqi_category(aqi):
    if aqi is None:
        return None
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"

def compute_daily_aqi_from_pm(pm25_daily, pm10_daily):
    """Return dict date -> {AQI, category, dominant, subindices}"""
    out = {}
    dates = sorted(set(list(pm25_daily.keys()) + list(pm10_daily.keys())))
    for d in dates:
        c25 = pm25_daily.get(d)
        c10 = pm10_daily.get(d)
        s25 = aqi_subindex(c25, PM25_BREAKPOINTS) if c25 is not None else None
        s10 = aqi_subindex(c10, PM10_BREAKPOINTS) if c10 is not None else None
        # choose higher subindex; if tie prefer PM2.5
        candidates = []
        if s25 is not None:
            candidates.append(("PM2.5", s25, c25))
        if s10 is not None:
            candidates.append(("PM10", s10, c10))
        if not candidates:
            out[d] = {"AQI": None, "category": None, "dominant": None, "subindices": {"PM2.5": s25, "PM10": s10}}
            continue
        candidates.sort(key=lambda x: (x[1], x[0] != "PM2.5"), reverse=True)
        dom = candidates[0]
        out[d] = {
            "AQI": dom[1],
            "category": aqi_category(dom[1]),
            "dominant": dom[0],
            "dominant_value": dom[2],
            "subindices": {"PM2.5": s25, "PM10": s10}
        }
    return out

# -------------------------
# NASA POWER helper (humidity & UV)
# -------------------------
def fetch_nasa_power(lat, lon, start_date, end_date):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "latitude": lat,
        "longitude": lon,
        "community": "AG",
        "parameters": "RH2M,ALLSKY_SFC_UVB",
        "format": "JSON",
        "time-standard": "UTC"
    }
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json().get("properties", {}).get("parameter", {})

    def convert(param_dict):
        out = {}
        for k, v in (param_dict or {}).items():
            try:
                d = datetime.strptime(k, "%Y%m%d").strftime("%Y-%m-%d")
            except Exception:
                d = k
            out[d] = v
        return out

    return convert(payload.get("RH2M", {})), convert(payload.get("ALLSKY_SFC_UVB", {}))

# -------------------------
# MAIN: build CSV with one row per day
# -------------------------
all_data = []

for loc in LOCATIONS:
    name = loc["name"]
    lat = loc["lat"]
    lon = loc["lon"]
    print(f"Processing {name} ({lat}, {lon}) ...")

    # 1) fetch weather/daily archive
    try:
        meteo = fetch_open_meteo_daily(lat, lon, START_DATE, END_DATE)
    except Exception as e:
        print(f"Open-Meteo daily archive failed for {name}: {e}")
        continue

    # 2) fetch NASA POWER (humidity, UV)
    try:
        rh_data, uv_data = fetch_nasa_power(lat, lon, START_DATE, END_DATE)
    except Exception as e:
        print(f"NASA POWER failed for {name}: {e}")
        rh_data, uv_data = {}, {}

    # 3) fetch hourly PM from Open-Meteo and aggregate to daily
    try:
        times, pm25_hourly, pm10_hourly = fetch_open_meteo_pm_hourly(lat, lon, START_DATE, END_DATE, timezone=TIMEZONE)
        pm25_daily, pm10_daily, pm25_max, pm10_max, hour_counts = aggregate_hourly_to_daily(
            times, pm25_hourly, pm10_hourly, min_hours=MIN_HOURLY_FOR_DAILY
        )
        aqi_daily_struct = compute_daily_aqi_from_pm(pm25_daily, pm10_daily)
        print(f"  PM daily samples: pm25_days={len(pm25_daily)}, pm10_days={len(pm10_daily)}")
    except Exception as e:
        print(f"Open-Meteo PM fetch failed for {name}: {e}")
        pm25_daily = {}
        pm10_daily = {}
        pm25_max = {}
        pm10_max = {}
        aqi_daily_struct = {}
        hour_counts = {}

    # 4) build one row per day using meteo['time'] as canonical day list
    times_daily = meteo.get("time", [])
    n = len(times_daily)
    for i in range(n):
        date = times_daily[i]
        tmin = meteo.get('temperature_2m_min', [None]*n)[i]
        tmax = meteo.get('temperature_2m_max', [None]*n)[i]
        tmean_list = meteo.get('temperature_2m_mean', None)
        if tmean_list:
            tmean = tmean_list[i]
        else:
            tmean = (tmin + tmax)/2 if (tmin is not None and tmax is not None) else None

        pm25_val = pm25_daily.get(date) if pm25_daily else None
        pm10_val = pm10_daily.get(date) if pm10_daily else None
        pm25_peak = pm25_max.get(date) if pm25_max else None
        pm10_peak = pm10_max.get(date) if pm10_max else None
        count_hours = hour_counts.get(date, 0)
        aqi_info = aqi_daily_struct.get(date, {}) or {}
        row = {
            "date": date,
            "location": name,
            "rainfall_mm": meteo.get('precipitation_sum', [None]*n)[i],
            "humidity_percent": rh_data.get(date),
            "temp_min_C": tmin,
            "temp_max_C": tmax,
            "temp_mean_C": tmean,
            "wind_speed_kph": meteo.get('windspeed_10m_max', [None]*n)[i],
            "wind_direction_deg": meteo.get('winddirection_10m_dominant', [None]*n)[i],
            "uv_index": uv_data.get(date),
            # PMs & AQI (one value per day)
            "pm25": pm25_val,
            "pm10": pm10_val,
            #"pm25_daily_max": pm25_peak,
            #"pm10_daily_max": pm10_peak,
            #"pm_hour_count": count_hours,
            "aqi": aqi_info.get("AQI"),
            "aqi_category": aqi_info.get("category"),
            "aqi_dominant_pollutant": aqi_info.get("dominant")
        }
        all_data.append(row)

# Save CSV
df = pd.DataFrame(all_data)
df.to_csv(OUTPUT_CSV, index=False)
print(f"CSV saved as '{OUTPUT_CSV}'")
