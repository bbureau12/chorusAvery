from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chorusAvery.db"

def choose_location():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, latitude, longitude FROM Locations")
    locations = cursor.fetchall()

    if not locations:
        print("❌ No locations found in the database.")
        return None

    print("\n📍 Available Locations:")
    for loc in locations:
        print(f"[{loc[0]}] {loc[1]} (Lat: {loc[2]}, Lon: {loc[3]})")

    selected = None
    while selected is None:
        try:
            selected_id = int(input("\n🔧 Enter the ID of the location to use for this batch: "))
            if any(loc[0] == selected_id for loc in locations):
                selected = selected_id
            else:
                print("❌ Invalid ID. Please choose from the list above.")
        except ValueError:
            print("⚠️ Please enter a valid number.")

    conn.close()
    print(f"\n✅ Selected location ID: {selected}")
    return selected
