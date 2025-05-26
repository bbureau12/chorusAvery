import os
import sqlite3
import datetime
from pydub import AudioSegment

# === CONFIGURATION ===
RAW_FOLDER = './recordings/raw'
CHUNK_FOLDER = './recordings/chunks'
DB_PATH = './db/chorusAvery.db'
CHUNK_LENGTH_MS = 5 * 60 * 1000  # 5 minutes

os.makedirs(CHUNK_FOLDER, exist_ok=True)

# === Connect to DB ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def prompt_location_id(filename):
    while True:
        try:
            loc = input(f"\U0001F4CD Enter LocationID for '{filename}': ").strip()
            return int(loc)
        except ValueError:
            print("❌ Please enter a valid integer.")

def create_source_file_entry(filename, location_id, from_dt, to_dt):
    cursor.execute("""
        INSERT INTO SourceFiles (filename, LocationID, From_Date, To_Date)
        VALUES (?, ?, ?, ?)
    """, (filename, location_id, from_dt, to_dt))
    conn.commit()
    return cursor.lastrowid

def format_chunk_filename(base_name, start_time):
    time_str = start_time.strftime('%H_%M_%S')
    return f"{base_name}_{time_str}.wav"

def split_audio_file(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
    audio = AudioSegment.from_wav(file_path)
    duration_sec = len(audio) / 1000.0
    from_dt = mod_time - datetime.timedelta(seconds=duration_sec)
    to_dt = mod_time

    location_id = prompt_location_id(base_name)
    create_source_file_entry(base_name + ".wav", location_id, from_dt, to_dt)

    print(f"📁 Splitting '{base_name}' into chunks...")

    for start in range(0, len(audio), CHUNK_LENGTH_MS):
        end = min(start + CHUNK_LENGTH_MS, len(audio))
        chunk = audio[start:end].set_frame_rate(16000).set_channels(1).set_sample_width(2)
        chunk_start_time = from_dt + datetime.timedelta(milliseconds=start)
        chunk_filename = format_chunk_filename(base_name, chunk_start_time)
        chunk_path = os.path.join(CHUNK_FOLDER, chunk_filename)

        chunk.export(chunk_path, format='wav', parameters=['-acodec', 'pcm_s16le'])
        print(f"✅ Wrote: {chunk_filename} ({(end - start) / 1000:.1f}s)")

    os.remove(file_path)
    print(f"🗑️ Deleted original: {file_path}")

# === MAIN ===
print("\n🔍 Looking for .wav files to split...")

for filename in os.listdir(RAW_FOLDER):
    if filename.endswith('.wav'):
        file_path = os.path.join(RAW_FOLDER, filename)
        split_audio_file(file_path)

conn.close()
print("\n🏁 All files processed.")
