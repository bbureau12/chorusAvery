import sqlite3
import os
import random
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import spectrogram

def select_species_id(cursor, species_name):
    # Search species table with partial case-insensitive match
    cursor.execute("SELECT id, name FROM Species WHERE name LIKE ?", (f"%{species_name}%",))
    results = cursor.fetchall()

    if not results:
        print(f"❌ No species found matching '{species_name}'")
        return None

    if len(results) == 1:
        return results[0]

    # Multiple matches — prompt user to pick one
    print("🔍 Multiple species matched your input:")
    for idx, (_, name) in enumerate(results):
        print(f"{idx + 1}. {name}")
    try:
        choice = int(input("Enter the number of the correct species: ")) - 1
        return results[choice]
    except (ValueError, IndexError):
        print("⚠️ Invalid selection.")
        return None

def generate_species_spectrogram(db_path, clips_dir, species_name):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    species = select_species_id(cursor, species_name)
    if not species:
        return
    species_id, species_name_resolved = species

    # Find clip IDs with ONLY this species and no others
    cursor.execute("""
        SELECT c.id, c.clip_path FROM Clips c
        JOIN ClipAnnotations ca ON ca.clip_id = c.id
        WHERE ca.species_id = ?
        GROUP BY c.id
        HAVING COUNT(*) = 1
    """, (species_id,))
    valid_clips = cursor.fetchall()

    if not valid_clips:
        print(f"No clips found with only species '{species_name_resolved}'.")
        return

    # Choose a random clip
    clip_id, clip_path = random.choice(valid_clips)
    clip_file = os.path.join(clips_dir, clip_path)

    if not os.path.exists(clip_file):
        print(f"📂 Clip file not found: {clip_file}")
        return

    # Load audio and create spectrogram
    sample_rate, samples = wavfile.read(clip_file)
    frequencies, times, Sxx = spectrogram(samples, fs=sample_rate)

    # Plot the spectrogram
    plt.figure(figsize=(10, 4))
    plt.pcolormesh(times, frequencies, 10 * np.log10(Sxx), shading='gouraud')
    plt.title(f"Spectrogram of {species_name_resolved}")
    plt.ylabel('Frequency [Hz]')
    plt.xlabel('Time [sec]')
    plt.colorbar(label='dB')
    plt.ylim(0, 8000)
    plt.tight_layout()
    plt.show()

    conn.close()
