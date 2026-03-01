import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "chorusAvery.db"

def scan_and_insert_mystery_segments(source_file: str, min_confidence: float = 0.5, min_gap: float = 5.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all confident detections
    cursor.execute("""
        SELECT start_time, duration
        FROM Detections
        WHERE source_file = ? AND confidence >= ?
        ORDER BY start_time
    """, (source_file, min_confidence))
    detections = cursor.fetchall()

    mystery_segments = []
    previous_end = 0.0

    for start, duration in detections:
        if start - previous_end >= min_gap:
            mystery_segments.append((source_file, previous_end, start))
        previous_end = max(previous_end, start + duration)

    if mystery_segments:
        cursor.executemany("""
            INSERT INTO MysterySegments (source_file, start_time, end_time)
            VALUES (?, ?, ?)
        """, mystery_segments)
        print(f"✅ Found {len(mystery_segments)} gap(s) in {source_file}")
    else:
        print(f"🔍 No qualifying gaps in {source_file}")

    conn.commit()
    conn.close()


def scan_all_files(min_confidence: float = 0.5, min_gap: float = 5.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT source_file FROM Detections")
    files = [row[0] for row in cursor.fetchall()]
    conn.close()

    for source_file in files:
        scan_and_insert_mystery_segments(source_file, min_confidence, min_gap)


if __name__ == "__main__":
    print("🔎 Scanning database for detection gaps...")
    scan_all_files(min_confidence=0.5, min_gap=5.0)
    print("✅ Done.")
