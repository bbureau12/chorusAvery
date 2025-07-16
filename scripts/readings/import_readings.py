import requests
import json
import sqlite3
from datetime import datetime, timezone
import os

# Resolve script directory for consistent paths
script_dir = os.path.dirname(os.path.abspath(__file__))

# Paths: go two levels up
base_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
settings_path = os.path.join(base_dir, 'settings.json')
db_path = os.path.join(base_dir, 'db', 'chorusAvery.db')
print(db_path)
# Load settings
with open(settings_path, 'r') as f:
    settings = json.load(f)

api_key = settings["ambient-api-key"]
app_key = settings["ambient-app-key"]
mac_address = settings["ambient-api-mac-address"]
location_id = settings["ambient-api-loc-id"]

# Define endpoint
endpoint = f"https://api.ambientweather.net/v1/devices/{mac_address}"
params = {
    "apiKey": api_key,
    "applicationKey": app_key,
    "limit": 576  # 2 days of 5-minute intervals
}

# Fetch data from API
response = requests.get(endpoint, params=params)
data = response.json()

# Prepare records
records = []
for entry in data:
    dt_utc = datetime.utcfromtimestamp(entry["dateutc"] / 1000).replace(tzinfo=timezone.utc)
    records.append((
        location_id,
        dt_utc.isoformat(),
        round(entry.get("tempf", 0)),
        entry.get("eventrainin", 0.0),
        entry.get("windspeedmph", 0.0),
        round(entry.get("maxdailygust", 0)),
        entry.get("uv", 0),
        entry.get("solarradiation", 0.0),
        entry.get("hourlyrainin", 0.0),
        entry.get("winddir", 0),
        entry.get("humidity", 0),
        entry.get("dewPoint", 0.0),
        entry.get("baromrelin", 0.0),
        entry.get("baromabsin", 0.0)
    ))

# Insert into SQLite
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.executemany("""
INSERT OR IGNORE INTO Location_Temperature (
    LocationID, DateTime_UTC, Temp_F, Rain_In, Windspeed_mph, Max_daily_gust_mph,
    UV, SolarRadiation, Hourly_Rain_in, Wind_dir, Humidity, Dewpoint,
    Barometer_RelIn, Barometer_AbsIn
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", records)

conn.commit()
conn.close()

print(f"✅ Inserted {len(records)} records into Location_Temperature")
