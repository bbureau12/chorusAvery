import csv
import sqlite3
from pathlib import Path
from utils.db import get_db_connection

DB_PATH = Path(__file__).resolve().parent.parent / "chorusAvery.db"

def load_detections_from_csv(csv_path: Path, location_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        added = 0
        for row in reader:
            species_code = row.get("species_code")
            species_id = None

            # Look up existing species by code
            if species_code:
                cursor.execute("""
                    SELECT species_id FROM SpeciesCodes WHERE code = ?
                """, (species_code,))
                result = cursor.fetchone()
                if result:
                    species_id = result["species_id"]
                else:
                    # Add missing species code
                    cursor.execute("""
                        INSERT INTO SpeciesCodes (code) VALUES (?)
                    """, (species_code,))
                    species_code_id = cursor.lastrowid
                # Try to get code ID even if not in SpeciesCodes
                cursor.execute("""
                    SELECT id FROM SpeciesCodes WHERE code = ?
                """, (species_code,))
                code_row = cursor.fetchone()
                species_code_id = code_row["id"] if code_row else None
            else:
                species_code_id = None

            # Insert detection
            cursor.execute("""
                INSERT INTO Detections (
                    species_id, species_code_id, source_file, start_time,
                    duration, confidence, location_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                species_id,
                species_code_id,
                row["original_file"],
                float(row["adjusted_start_time"]),
                float(row["duration"]),
                float(row["confidence"]) if row["confidence"] else None,
                location_id
            ))
            added += 1

    conn.commit()
    conn.close()
    print(f"✅ Inserted {added} detections from {csv_path.name}")
