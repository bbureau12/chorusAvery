import sqlite3
from datetime import datetime

def insert_detection(db_path, species_code, common_name, confidence, start_time, duration, source_file, location_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ✅ Ensure source_file exists in SourceFiles
    cursor.execute("SELECT id FROM SourceFiles WHERE filename = ?", (source_file,))
    row = cursor.fetchone()

    if row:
        source_file_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO SourceFiles (filename) VALUES (?)",
            (source_file,)
        )
        source_file_id = cursor.lastrowid

    # 🔎 Try to find or insert species_code
    cursor.execute("SELECT id, species_id FROM SpeciesCodes WHERE code = ?", (species_code,))
    result = cursor.fetchone()

    if result:
        species_code_id, species_id = result
    else:
        cursor.execute(
            "INSERT INTO SpeciesCodes (code, name) VALUES (?, ?)",
            (species_code, common_name)
        )
        species_code_id = cursor.lastrowid
        species_id = None

    # 🚫 Check for exact duplicate detection
    cursor.execute(
        """
        SELECT 1 FROM Detections
        WHERE source_file_id = ?
          AND start_time = ?
          AND duration = ?
          AND species_code_id = ?
          AND location_id = ?
        """,
        (source_file_id, start_time, duration, species_code_id, location_id)
    )

    if cursor.fetchone():
        print(f"⚠️ Skipping duplicate: {source_file} @ {start_time}s for species code {species_code}")
        conn.close()
        return False

    # ✅ Insert detection
    cursor.execute(
        """
        INSERT INTO Detections (
            species_id, species_code_id, confidence, start_time,
            duration, source_file_id, location_id, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            species_id,
            species_code_id,
            confidence,
            start_time,
            duration,
            source_file_id,
            location_id,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()
    return True
