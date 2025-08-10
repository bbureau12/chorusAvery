import sqlite3
from datetime import datetime
import pytz

# === CONFIGURATION ===
DB_PATH = "./db/chorusAvery.db"
LOCAL_TIMEZONE = pytz.timezone("America/Chicago")  # change if needed
UTC = pytz.utc


# === Connect to database ===
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# === Fetch all Clips with local datetimes present ===
cursor.execute("""
    SELECT id, start_date_source, end_date_source 
    FROM Clips 
    WHERE start_date_source IS NOT NULL 
      AND end_date_source IS NOT NULL
""")
rows = cursor.fetchall()
print(f"🔍 Found {len(rows)} clips to convert.")
def parse_local_datetime(dt_str):
    try:
        # 1. ISO 8601 with tz (e.g. 2025-07-08T20:33:15-05:00)
        return datetime.fromisoformat(dt_str)
    except ValueError:
        pass
    try:
        # 2. With microseconds
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        pass
    try:
        # 3. Without microseconds
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:
        # 4. With slashes and literal T (e.g. 4/21/2025 T16:21:00)
        return datetime.strptime(dt_str, "%m/%d/%Y T%H:%M:%S")
    except ValueError as e:
        raise ValueError(f"Unrecognized date format: {dt_str}") from e
# === Iterate and update ===
for row in rows:
    try:
        # Parse local datetime string (assuming 'YYYY-MM-DD HH:MM:SS')
        local_start = parse_local_datetime(row["start_date_source"])
        local_end = parse_local_datetime(row["end_date_source"])
        # Localize and convert to UTC
        if local_start.tzinfo is None:
            local_start_dt = LOCAL_TIMEZONE.localize(local_start)
        else:
            local_start_dt = local_start

        if local_end.tzinfo is None:
            local_end_dt = LOCAL_TIMEZONE.localize(local_end)
        else:
            local_end_dt = local_end
        utc_start = local_start_dt.astimezone(UTC).isoformat()
        utc_end = local_end_dt.astimezone(UTC).isoformat()
        
        # (Optional) Clean original values to ISO format (without timezone)
        cleaned_start = local_start_dt.isoformat(timespec='seconds')
        cleaned_end = local_end_dt.isoformat(timespec='seconds')

        # Update database
        cursor.execute("""
            UPDATE Clips
            SET 
                start_date_utc = ?,
                end_time_utc = ?,
                start_date_source = ?,  -- cleaned version
                end_date_source = ?     -- cleaned version
            WHERE id = ?
        """, (utc_start, utc_end, cleaned_start, cleaned_end, row["id"]))
    
    except Exception as e:
        print(f"⚠️ Error on clip ID {row['id']}: {e}")

# === Commit changes ===
conn.commit()
conn.close()
print("✅ UTC columns and cleaned timestamps updated.")
