import os
import random
import librosa
import numpy as np
import matplotlib.pyplot as plt
import librosa.display
from scipy.signal import butter, sosfilt
from pydub import AudioSegment
from pydub.playback import play
import soundfile as sf
import sqlite3

# === SETTINGS ===
DB_PATH = "./db/chorusAvery.db"
SOURCE_FOLDER = "./recordings/training_data"
DEST_FOLDER = "./recordings/filtered"
ORDER = 8
SAMPLE_PREVIEW_COUNT = 4

# === FREQUENCY SUGGESTIONS BY PRIMARY SPECIES ID ===
BANDPASS_SUGGESTIONS = {
    201: (3800, 5000),  # Spring Peeper
    202: (2200, 3600),  # Chorus Frog
    203: (900, 2800),   # Gray Tree Frog
}

os.makedirs(DEST_FOLDER, exist_ok=True)

def bandpass_filter(data, sr, lowcut, highcut, order=5):
    sos = butter(order, [lowcut, highcut], btype='bandpass', fs=sr, output='sos')
    return sosfilt(sos, data)

def play_audio(data, sr):
    temp_path = "temp_clip.wav"
    sf.write(temp_path, data, sr)
    audio = AudioSegment.from_wav(temp_path)
    play(audio)
    os.remove(temp_path)

def get_overlapping_clips(primary_species_id, filter_species_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
    SELECT DISTINCT c.id, c.clip_path
    FROM Clips c
    JOIN ClipAnnotations a1 ON a1.clip_id = c.id AND a1.species_id = ?
    JOIN ClipAnnotations a2 ON a2.clip_id = c.id AND a2.species_id = ?
    WHERE c.filtered_for_species_id IS NULL
    """
    cursor.execute(query, (primary_species_id, filter_species_id))
    result = cursor.fetchall()
    conn.close()
    return result

def load_clip(path):
    try:
        y, sr = librosa.load(path, sr=None)
        return y, sr
    except Exception as e:
        print(f"\u274c Error loading clip: {e}")
        return None, None

def show_comparison_spectrograms(original, filtered, sr, lowcut, highcut, title="Spectrogram Comparison"):
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))

    S_orig = librosa.amplitude_to_db(np.abs(librosa.stft(original)), ref=np.max)
    img1 = librosa.display.specshow(S_orig, sr=sr, x_axis='time', y_axis='hz', ax=axs[0])
    axs[0].set_title("Original")
    fig.colorbar(img1, ax=axs[0], format="%+2.0f dB")

    S_filt = librosa.amplitude_to_db(np.abs(librosa.stft(filtered)), ref=np.max)
    img2 = librosa.display.specshow(S_filt, sr=sr, x_axis='time', y_axis='hz', ax=axs[1])
    axs[1].set_title(f"Filtered ({lowcut}-{highcut} Hz)")
    fig.colorbar(img2, ax=axs[1], format="%+2.0f dB")

    fig.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.show()

def refinement_loop(sample_paths, default_lowcut, default_highcut):
    current_clip_path = random.choice(sample_paths)
    current_clip_data, current_sr = load_clip(current_clip_path)

    try:
        lowcut = float(input(f"Enter LOW cutoff frequency (suggested {default_lowcut} Hz): ") or default_lowcut)
        highcut = float(input(f"Enter HIGH cutoff frequency (suggested {default_highcut} Hz): ") or default_highcut)
    except ValueError:
        print("❌ Invalid input. Using suggested values.")
        lowcut, highcut = default_lowcut, default_highcut

    while True:
        print(f"\n\U0001f50a Currently loaded: {os.path.basename(current_clip_path)}")
        print(f"\U0001f39b️ Bandpass: {lowcut} – {highcut} Hz")

        filtered = bandpass_filter(current_clip_data, current_sr, lowcut, highcut, ORDER)
        print("▶️ Playing original...")
        play_audio(current_clip_data, current_sr)
        print("▶️ Playing filtered...")
        play_audio(filtered, current_sr)

        print("\nOptions:")
        print("1. 🔁 Retry the SAME sound with NEW filter settings")
        print("2. 🔄 Load NEW sound, same filter")
        print("3. 🧪 Load NEW sound and set NEW filter")
        print("4. 📊 Show Spectrograms")
        print("5. ✅ Confirm settings and proceed to filtering")
        print("6. ❌ Cancel")

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            try:
                lowcut = float(input("Enter new LOW cutoff frequency (Hz): "))
                highcut = float(input("Enter new HIGH cutoff frequency (Hz): "))
            except ValueError:
                print("❌ Invalid input.")
        elif choice == "2":
            current_clip_path = random.choice(sample_paths)
            current_clip_data, current_sr = load_clip(current_clip_path)
        elif choice == "3":
            try:
                lowcut = float(input("Enter new LOW cutoff frequency (Hz): "))
                highcut = float(input("Enter new HIGH cutoff frequency (Hz): "))
                current_clip_path = random.choice(sample_paths)
                current_clip_data, current_sr = load_clip(current_clip_path)
            except ValueError:
                print("❌ Invalid input.")
        elif choice == "4":
            show_comparison_spectrograms(current_clip_data, filtered, current_sr, lowcut, highcut, os.path.basename(current_clip_path))
        elif choice == "5":
            return True, lowcut, highcut
        elif choice == "6":
            return False, 0, 0
        else:
            print("❌ Invalid choice.")

def filter_and_save_clips(clips, primary_species_id, lowcut, highcut):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed = 0

    for clip_id, clip_path in clips:
        src_path = os.path.join(SOURCE_FOLDER, clip_path)
        if not os.path.exists(src_path):
            print(f"⚠️ Missing file: {clip_path}")
            continue

        base_name = os.path.splitext(os.path.basename(clip_path))[0]
        new_name = f"{base_name}_filtered_species_{primary_species_id}.wav"
        dest_path = os.path.join(DEST_FOLDER, new_name)

        try:
            y, sr = librosa.load(src_path, sr=None)
            filtered = bandpass_filter(y, sr, lowcut, highcut, ORDER)
            sf.write(dest_path, filtered, sr)

            cursor.execute("""
                INSERT OR REPLACE INTO Clips (
                    clip_path,
                    start_time,
                    end_time,
                    filtered_for_species_id
                ) VALUES (?, 0, 0, ?)
            """, (new_name, primary_species_id))

            conn.commit()
            processed += 1
            print(f"✅ Filtered and saved: {new_name}")
        except Exception as e:
            print(f"❌ Error processing {clip_path}: {e}")

    conn.close()
    print(f"\n🎉 Finished processing {processed} clips.")

if __name__ == "__main__":
    print("🎧 Bandpass Refinement + Filtering Tool")

    try:
        primary_species_id = int(input("Enter PRIMARY species ID (to extract): "))
        filter_species_id = int(input("Enter FILTER species ID (to suppress): "))
    except ValueError:
        print("❌ Invalid species ID input.")
        exit()

    overlapping_clips = get_overlapping_clips(primary_species_id, filter_species_id)
    if not overlapping_clips:
        print("⚠️ No overlapping clips found with both species.")
        exit()

    full_paths = [os.path.join(SOURCE_FOLDER, path) for _, path in overlapping_clips]

    suggested_lowcut, suggested_highcut = BANDPASS_SUGGESTIONS.get(
        primary_species_id, (3000, 5000)
    )
    print(f"🎛️ Suggested bandpass for species {primary_species_id}: {suggested_lowcut}–{suggested_highcut} Hz")

    confirmed, lowcut, highcut = refinement_loop(full_paths, suggested_lowcut, suggested_highcut)
    if not confirmed:
        print("❌ Refinement cancelled.")
        exit()

    try:
        clip_count = int(input("How many overlapping clips to process? (default 100): ") or "100")
    except ValueError:
        print("❌ Invalid clip count.")
        exit()

    random.shuffle(overlapping_clips)
    filter_and_save_clips(overlapping_clips[:clip_count], primary_species_id, lowcut, highcut)
