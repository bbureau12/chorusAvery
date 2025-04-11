import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db/chorusAvery.db"

def sync_species_codes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch all species with a defined code
    cursor.execute("SELECT id, name, code FROM Species WHERE code IS NOT NULL AND TRIM(code) != ''")
    species_with_codes = cursor.fetchall()

    inserted = 0
    skipped = 0

    for species_id, name, code in species_with_codes:
        code = code.strip().lower()

        # Skip if this species_code already exists
        cursor.execute("SELECT id FROM SpeciesCodes WHERE code = ?", (code,))
        if cursor.fetchone():
            skipped += 1
            continue

        cursor.execute(
            "INSERT INTO SpeciesCodes (species_id, code, name) VALUES (?, ?, ?)",
            (species_id, code, name)
        )
        inserted += 1

    conn.commit()
    conn.close()

    print(f"✅ Sync complete! Inserted: {inserted}, Skipped (already existed): {skipped}")

if __name__ == "__main__":
    sync_species_codes()
