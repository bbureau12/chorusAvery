import sqlite3
import os
from pydub import AudioSegment
from scipy.signal import butter, sosfilt
import soundfile as sf
from datetime import datetime

# === SETTINGS ===
DB_PATH = './db/chorusAvery.db'
SOURCE_FOLDER = './recordings/clips'
DEST_FOLDER = './recordings/bandpass'
os.makedirs(DEST_FOLDER, exist_ok=True)

def bandpass_filter(audio_data, sr, lowcut, highcut, order=5):
    from scipy.signal import butter, sosfilt
    sos = butter(order, [lowcut, highcut], btype='bandpass', fs=sr, output='sos')
    return sosfilt(sos, audio_data)

def select_species(cursor):
    cursor.execute("SELECT id, name FROM Species ORDER BY name")
    species = cursor.fetchall()
    for sid, name in species:
        print(f"{sid}: {name}")
    return species

def fetch_overlap_clips(cursor, primary_id, filter_id):
    query = """
    SELECT DISTINCT C.id, C.clip_path
    FROM Clips C
    JOIN ClipAnnotations A1 ON A1.clip_id = C.id AND A1.species_id = ?
    JOIN ClipAnnotations A2 ON A2.clip_id = C.id AND A2.species_id = ?
    WHERE C.filtered_for_species_id IS NULL
    """
    cursor.execute(query, (primary_id, filter_id))
    return cursor.fetchall()

def process_clips(clips, primary_id, lowcut, highcut, max_items):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed = 0
    timestamp = datetime.now().strftime('%y%m%d')

    for clip_id, clip_path in clips[:max_items]:
        full_path = os.path.join(SOURCE_FOLDER, clip_path)
        if not os.path.exists(full_path):
            print(f"⚠️ Missing: {clip_path}")
            continue

        sound = AudioSegment.from_file(full_path)
        samples = sound.get_array_of_samples()
        arr = np.array(samples).astype(float)
        filtered = bandpass_filter(arr, sound.frame_rate, lowcut, highcut)
        output_name = f"{os.path.splitext(clip_path)[0]}_filter_{timestamp}.wav"
        output_path = os.path.join(DEST_FOLDER, output_name)
        sf.write(output_path, filtered, sound.frame_rate)

        cursor.execute("""
            INSERT INTO Clips (clip_path, start_time, end_time, filtered_for_species_id)
            VALUES (?, 0, 0, ?)
        """, (output_name, primary_id))
        conn.commit()

        print(f"✅ Saved: {output_name}")
        processed += 1

    conn.close()
    print(f"\n🎉 Finished processing {processed} clips!")

if __name__ == "__main__":
    import numpy as np
    import random  # 🧠 Add this for shuffling

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Select the PRIMARY species (target to extract):")
    species = select_species(cursor)
    primary_id = int(input("Primary species ID: "))

    print("\nSelect the FILTER species (species to remove):")
    filter_id = int(input("Filter species ID: "))

    lowcut = float(input("Lowcut freq (Hz): "))
    highcut = float(input("Highcut freq (Hz): "))
    max_items = int(input("How many to filter? (default 100): ") or "100")

    clips = fetch_overlap_clips(cursor, primary_id, filter_id)

    print(f"\n🔍 Found {len(clips)} overlapping clips.")
    if clips:
        random.shuffle(clips)  # 🔀 Shuffle right here!
        process_clips(clips, primary_id, lowcut, highcut, max_items)
    else:
        print("No clips found with both species.")
