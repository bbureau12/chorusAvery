import os
import random
import shutil
import sqlite3
from pydub.silence import detect_nonsilent
from pydub import AudioSegment, silence
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 🔹 Prevent tkinter errors on shutdown
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

def search_species(cursor, query):
    cursor.execute("SELECT id, name FROM Species")
    return [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]

def generate_spectrogram(audio, output_path):
    samples = np.array(audio.get_array_of_samples())
    freqs, times, Sxx = spectrogram(samples, fs=audio.frame_rate, nperseg=256)
    plt.figure(figsize=(2, 2))
    plt.pcolormesh(times, freqs, 10*np.log10(Sxx + 1e-10), shading='gouraud')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close()

def strip_silence(audio, silence_thresh=-40, min_silence_len=300):
    """
    Returns a new AudioSegment with silence removed based on detected nonsilent regions.
    """
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    if not nonsilent_ranges:
        return audio  # fallback: if no nonsilent parts found, return original

    stripped_audio = AudioSegment.empty()
    for start_ms, end_ms in nonsilent_ranges:
        stripped_audio += audio[start_ms:end_ms]
    return stripped_audio

def process_batch_recordings(db_path, batch_dir, clips_output_dir, clip_length_ms=2500):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    ALLOWED_EXTENSIONS = ('.wav', '.mp3')
    files = [
        f for f in os.listdir(batch_dir)
        if f.lower().endswith(ALLOWED_EXTENSIONS)
    ]
    if not files:
        print("🚫 No supported audio files (.wav or .mp3) found in batch directory.")
        return

    for file_name in files:
        file_path = os.path.join(batch_dir, file_name)
        sound = AudioSegment.from_file(file_path)
        original_duration = len(sound) / 1000.0
        print(f"\n🎧 File: {file_name} | Original duration: {original_duration:.2f}s")

        stripped = strip_silence(sound, silence_thresh=-50, min_silence_len=300)
        new_duration = len(stripped) / 1000.0
        print(f"🔇 Stripped duration: {new_duration:.2f}s")

        proceed = input("✅ Proceed with this file? (y/n): ").strip().lower()
        if proceed != 'y':
            print("⏭️ Skipped file.")
            continue

        # 🔹 MOD: Prompt species vs non-species
        mode = ""
        while mode not in ['s', 'n']:
            mode = input("🔔 Annotate with species (s) or non-species (n)?: ").strip().lower()

        annotations = []
        if mode == 's':
            # 🔹 Species selection (same as before)
            while True:
                query = input("🔎 Search species name to add (or # to finish): ").strip()
                if query == "#":
                    break
                cursor.execute("SELECT id, name FROM Species")
                matches = [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]
                if not matches:
                    print("⚠️ No matches.")
                    continue
                for idx, (_, name) in enumerate(matches):
                    print(f"{idx + 1}. {name}")
                sel = input("Select number(s) separated by commas: ").strip()
                try:
                    selected = [int(s)-1 for s in sel.split(',')]
                    for s in selected:
                        if 0 <= s < len(matches) and matches[s] not in annotations:
                            annotations.append(('species', matches[s][0], matches[s][1]))
                            print(f"✅ Added species: {matches[s][1]}")
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")

        elif mode == 'n':
            # 🔹 Non-species selection
            while True:
                query = input("🔎 Search non-species name to add (or # to finish): ").strip()
                if query == "#":
                    break
                cursor.execute("SELECT id, name FROM NonAnimalSounds")
                matches = [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]
                if not matches:
                    print("⚠️ No matches.")
                    continue
                for idx, (_, name) in enumerate(matches):
                    print(f"{idx + 1}. {name}")
                sel = input("Select number(s) separated by commas: ").strip()
                try:
                    selected = [int(s)-1 for s in sel.split(',')]
                    for s in selected:
                        if 0 <= s < len(matches) and matches[s] not in annotations:
                            annotations.append(('non_species', matches[s][0], matches[s][1]))
                            print(f"✅ Added non-species: {matches[s][1]}")
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")

        if not annotations:
            print("🚫 Nothing selected, skipping file.")
            continue

        # Log SourceFile
        cursor.execute("""
            INSERT INTO SourceFiles (filename, LocationID)
            VALUES (?, ?)
        """, (file_name, 8))
        source_id = cursor.lastrowid
        print(f"📝 Logged source file with ID {source_id}")

        num_clips = 0
        for i in range(0, len(stripped), clip_length_ms):
            clip = stripped[i:i + clip_length_ms]
            clip_name = f"{os.path.splitext(file_name)[0]}_{str(i // clip_length_ms).zfill(4)}.wav"
            clip_path = os.path.join(clips_output_dir, clip_name).replace('\\','/')
            clip.export(clip_path, format="wav")

            cursor.execute("""
                INSERT INTO Clips (clip_path, source_id)
                VALUES (?, ?)
            """, (clip_name, source_id))
            clip_id = cursor.lastrowid

            # 🔹 Insert annotations with correct field
            for kind, id_, name in annotations:
                if kind == 'species':
                    cursor.execute("""
                        INSERT INTO ClipAnnotations (clip_id, species_id, verified)
                        VALUES (?, ?, 1)
                    """, (clip_id, id_))
                elif kind == 'non_species':
                    cursor.execute("""
                        INSERT INTO ClipAnnotations (clip_id, non_animal_sound_id, verified)
                        VALUES (?, ?, 1)
                    """, (clip_id, id_))

            num_clips += 1
            print(f"🎵 Generated & logged clip: {clip_name}")

        conn.commit()
        print(f"✅ Processed {num_clips} clips for file: {file_name}")

    conn.close()
    print("\n🏁 Batch processing complete!")


if __name__ == "__main__":
    process_batch_recordings(
        db_path="./db/chorusAvery.db",
        batch_dir="./recordings/batch",
        clips_output_dir="./recordings/training_data"
    )
