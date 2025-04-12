import sqlite3
from pathlib import Path
from pydub import AudioSegment
import simpleaudio as sa

DB_PATH = Path(__file__).resolve().parent.parent / "db/chorusAvery.db"
AUDIO_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
CLIP_DURATION_MS = 5000  # 5 seconds

def get_unmapped_species_codes(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, code, name 
        FROM SpeciesCodes 
        WHERE species_id IS NULL
    """)
    return cursor.fetchall()

def get_detections_for_code(conn, code_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Detections.id, start_time, source_file_id, SourceFiles.filename
        FROM Detections 
        JOIN SourceFiles ON Detections.source_file_id = SourceFiles.id
        WHERE Detections.species_code_id = ?
        ORDER BY start_time ASC
    """, (code_id,))
    return cursor.fetchall()

def play_audio_clip(file_path: Path, start_time: float):
    if not file_path.exists():
        print(f"❌ File not found: {file_path.name}")
        return
    audio = AudioSegment.from_wav(file_path)
    clip = audio[int(start_time * 1000):int(start_time * 1000) + CLIP_DURATION_MS]
    playback = sa.play_buffer(
        clip.raw_data,
        num_channels=clip.channels,
        bytes_per_sample=clip.sample_width,
        sample_rate=clip.frame_rate
    )
    playback.wait_done()

def main():
    conn = sqlite3.connect(DB_PATH)

    unmapped = get_unmapped_species_codes(conn)
    if not unmapped:
        print("✅ All species codes are mapped.")
        return

    print("🔎 Unmapped species codes:")
    for idx, (_, code, name) in enumerate(unmapped, 1):
        display_name = name or "Unknown"
        print(f"{idx}. {code} — {display_name}")

    choice = input("🔢 Choose a species code to review (or press Enter to cancel): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(unmapped)):
        print("❌ Invalid choice.")
        return

    selected_id, code, name = unmapped[int(choice) - 1]
    print(f"\n🎧 Reviewing detections for: {code} — {name or 'Unknown'}")

    detections = get_detections_for_code(conn, selected_id)
    if not detections:
        print("⚠️ No detections found.")
        return

    for idx, (det_id, start_time, _, filename) in enumerate(detections, 1):
        audio_path = AUDIO_DIR / filename
        print(f"\n{idx}. {filename} @ {start_time:.1f}s")
        user = input("▶️  Press Enter to play, [s]kip, [q]uit: ").strip().lower()
        if user == "q":
            break
        elif user == "s":
            continue
        else:
            play_audio_clip(audio_path, start_time)

    conn.close()
    print("\n✅ Review complete.")

if __name__ == "__main__":
    main()
