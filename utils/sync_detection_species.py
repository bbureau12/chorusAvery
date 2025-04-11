import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "chorusAvery.db"

def sync_species_ids_from_codes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find all detections where the species_code_id exists and the species_id is NULL or mismatched
    cursor.execute("""
        SELECT D.id, SC.species_id
        FROM Detections D
        JOIN SpeciesCodes SC ON D.species_code_id = SC.id
        WHERE D.species_id IS NULL OR D.species_id != SC.species_id
    """)

    updates = cursor.fetchall()
    print(f"🔄 Found {len(updates)} detections needing updates.")

    for detection_id, correct_species_id in updates:
        cursor.execute("""
            UPDATE Detections
            SET species_id = ?
            WHERE id = ?
        """, (correct_species_id, detection_id))

    conn.commit()
    conn.close()

    print(f"✅ Synced {len(updates)} detections.")

if __name__ == "__main__":
    sync_species_ids_from_codes()
