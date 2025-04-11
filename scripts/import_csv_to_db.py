import csv
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.insert_detections import insert_detection

def import_csv_to_db():
    db_path = Path(__file__).resolve().parent.parent / "db/chorusAvery.db"
    data_dir = Path(__file__).resolve().parent.parent / "data"

    print("📂 Available CSV files:")
    csv_files = list(data_dir.glob("*.csv"))
    for i, f in enumerate(csv_files):
        print(f"  {i+1}. {f.name}")

    choice = input("Enter the number of the file to import: ").strip()
    try:
        selected_file = csv_files[int(choice) - 1]
    except (IndexError, ValueError):
        print("❌ Invalid choice.")
        return

    location_id = input("🌎 Enter location ID for this import: ").strip()
    try:
        location_id = int(location_id)
    except ValueError:
        print("❌ Location ID must be an integer.")
        return

    print(f"📥 Importing from: {selected_file.name}")
    with selected_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count_inserted = 0
        count_skipped = 0

        for row in reader:
            success = insert_detection(
                db_path=db_path,
                species_code=row["species_code"],
                common_name=row["common_name"],
                confidence=float(row["confidence"]),
                start_time=float(row["adjusted_start_time"]),
                duration=float(row["duration"]),
                source_file=row["original_file"],
                location_id=location_id
            )
            if success:
                count_inserted += 1
            else:
                count_skipped += 1

    print(f"✅ Done! Inserted: {count_inserted}, Skipped: {count_skipped}")

if __name__ == "__main__":
    import_csv_to_db()
