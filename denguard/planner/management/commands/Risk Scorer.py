import pandas as pd

# Read and force numeric conversion
df = pd.read_csv("prediction dataset.csv")

# Convert relevant columns to numeric
numeric_cols = [
    'temp_mean_C', 'rainfall_mm', 'humidity_percent',
    'pm25', 'pm10', 'wind_speed_kph', 'uv_index'
]
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

def calculate_risk(row):
    score = 0

    # Temperature (0–25)
    temp = row['temp_mean_C']
    if temp < 20:
        temp_score = 0
    elif temp < 26:
        temp_score = (temp - 20) / 6
    elif temp <= 30:
        temp_score = 1.0
    elif temp < 33:
        temp_score = (33 - temp) / 3
    else:
        temp_score = 0
    score += 25 * temp_score

    # Rainfall (0–20)
    rain = row['rainfall_mm']
    if rain < 1:
        rain_score = 0
    elif rain <= 60:
        rain_score = rain / 60
    elif rain <= 100:
        rain_score = 1.0
    else:
        rain_score = max(0, 1 - (rain - 100) / 100)
    score += 20 * rain_score

    # Humidity (0–15)
    hum = row['humidity_percent']
    if hum < 60:
        hum_score = 0
    elif hum < 80:
        hum_score = (hum - 60) / 20
    else:
        hum_score = 1.0
    score += 15 * hum_score

    # PM2.5 (0–15)
    pm25 = row['pm25']
    if pm25 < 15:
        pm25_score = 0
    elif pm25 < 50:
        pm25_score = (pm25 - 15) / 35
    else:
        pm25_score = 1.0
    score += 15 * pm25_score

    # PM10 (0–10)
    pm10 = row['pm10']
    if pm10 < 30:
        pm10_score = 0
    elif pm10 < 100:
        pm10_score = (pm10 - 30) / 70
    else:
        pm10_score = 1.0
    score += 10 * pm10_score

    # Wind (0–10)
    wind = row['wind_speed_kph']
    if wind <= 5:
        wind_score = 1.0
    elif wind < 20:
        wind_score = (20 - wind) / 15
    else:
        wind_score = 0
    score += 10 * wind_score

    # UV (0–5)
    uv = row['uv_index']
    if uv <= 3:
        uv_score = 1.0
    elif uv < 9:
        uv_score = (9 - uv) / 6
    else:
        uv_score = 0
    score += 5 * uv_score

    # Classification
    if score <= 20:
        risk = "Very Low"
    elif score <= 40:
        risk = "Low"
    elif score <= 60:
        risk = "Moderate"
    elif score <= 80:
        risk = "High"
    else:
        risk = "Very High"

    return risk

# Apply function
df['risk'] = df.apply(calculate_risk, axis=1)

# Remove unwanted columns
df = df.drop(columns=['aqi_category', 'aqi_dominant_pollutant'], errors='ignore')

# Save to new file
df.to_csv("prediction_dataset_with_risk.csv", index=False)

print("✅ Risk column added successfully")
