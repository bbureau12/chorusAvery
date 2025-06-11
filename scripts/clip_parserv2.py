from pydub import AudioSegment
import os
import math
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Settings
input_folder = './recordings/chunks'
output_folder = './recordings/clips'
plot_folder = './recordings/plots'
chunk_size_ms = 5000  # 5 seconds
min_clip_ms = 500     # 0.5s minimum
silence_thresh_relative = -14
save_plots = False

# Boost settings
boost_threshold_dbfs = -25.0  # If max_dBFS is below this, apply boost
boost_amount_db = 15

os.makedirs(output_folder, exist_ok=True)
if save_plots:
    os.makedirs(plot_folder, exist_ok=True)

# Helpers
def safe_dbfs(segment):
    return segment.dBFS if segment.dBFS != float('-inf') else -100.0

def parse_chunk_start_time(base_name):
    """Extract datetime from chunk filename like '250511_0419_22_10_47'"""
    try:
        parts = base_name.split('_')
        if len(parts) < 5:
            raise ValueError("Filename format not valid")

        date_prefix = parts[0]  # YYMMDD
        time_code = parts[1]   # Tascam-generated code
        hour, minute, second = map(int, parts[2:5])

        dt = datetime.strptime(date_prefix, "%y%m%d")
        dt = dt.replace(hour=hour, minute=minute, second=second)
        return dt, f"{date_prefix}_{time_code}"
    except Exception as e:
        print(f"⚠️ Unable to parse timestamp from: {base_name} ({e})")
        return None, None

def generate_clip_filename(base_name, start_time):
    time_str = start_time.strftime('%H_%M_%S')
    return f"{base_name}_{time_str}.wav"


def apply_bandpass_filter(audio, lowcut=300, highcut=8000):
    """
    Apply a bandpass filter by chaining high-pass and low-pass filters.
    """
    filtered = audio.high_pass_filter(lowcut)
    filtered = filtered.low_pass_filter(highcut)
    return filtered

def slice_audio_dynamic_threshold(file_path, apply_bandpass=False, lowcut=200, highcut=12000):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    chunk_start_time, original_base = parse_chunk_start_time(base_name)
    if not chunk_start_time:
        return

    sound = AudioSegment.from_file(file_path)

    if apply_bandpass:
        print(f"🎚️ Applying bandpass filter: {lowcut}-{highcut} Hz")
        sound = apply_bandpass_filter(sound, lowcut, highcut)

    current_start = 0
    clip_times = []

    while current_start < len(sound):
        window = sound[current_start:current_start + chunk_size_ms]
        window_dbfs = safe_dbfs(window)

        silence_thresh = window_dbfs + silence_thresh_relative

        if window_dbfs > silence_thresh:
            end = current_start + chunk_size_ms
            while end < len(sound) and (end - current_start) < 5000:
                next_chunk = sound[end:end + chunk_size_ms]
                if safe_dbfs(next_chunk) + silence_thresh_relative < silence_thresh:
                    break
                end += chunk_size_ms

            clip = sound[current_start:end]
            if len(clip) >= min_clip_ms and clip.max_dBFS > -33:
                if clip.max_dBFS < boost_threshold_dbfs:
                    print(f"🔊 Boosting clip from {clip.max_dBFS:.2f} dBFS by {boost_amount_db} dB")
                    clip += boost_amount_db

                clip_start_time = chunk_start_time + timedelta(milliseconds=current_start)
                clip_filename = generate_clip_filename(original_base, clip_start_time)
                clip_path = os.path.join(output_folder, clip_filename)

                clip.export(clip_path, format="wav", parameters=["-acodec", "pcm_s16le"])
                print(f"✅ Saved clip: {clip_filename} ({len(clip)} ms)")
                clip_times.append((current_start, end))

            current_start = end
        else:
            current_start += chunk_size_ms


    if save_plots:
        try:
            samples = sound.get_array_of_samples()
            plt.figure(figsize=(12, 3))
            plt.plot(samples, color='gray', linewidth=0.5)
            for start_ms, end_ms in clip_times:
                plt.axvspan(start_ms * (len(samples) / len(sound)), end_ms * (len(samples) / len(sound)), color='green', alpha=0.3)
            plt.title(base_name)
            plt.savefig(os.path.join(plot_folder, f"{base_name}.png"))
            plt.close()
            print(f"🖼️ Saved plot: {plot_folder}/{base_name}.png")
        except Exception as e:
            print(f"⚠️ Could not plot: {e}")

# MAIN
print("\n🔍 Scanning for recordings to process...")
for filename in os.listdir(input_folder):
    if filename.endswith('.wav'):
        full_path = os.path.join(input_folder, filename)
        print(f"\n🎧 Processing: {filename}")
        slice_audio_dynamic_threshold(full_path, apply_bandpass=False)
        os.remove(full_path)
        print(f"🗑️ Deleted: {filename}")

print("\n🏁 Done!")
