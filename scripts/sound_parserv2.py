from pydub import AudioSegment
import os
import math
import matplotlib.pyplot as plt

# Settings
input_folder = './recordings/chunks'
output_folder = './recordings/clips'
plot_folder = './recordings/plots'   # For optional plots
chunk_size_ms = 5000  # 5 seconds
min_clip_ms = 500     # Minimum clip size to save (0.5s)
silence_thresh_relative = -14  # dB adjustment relative to window loudness
save_plots = True     # <- Toggle plotting

os.makedirs(output_folder, exist_ok=True)
if save_plots:
    os.makedirs(plot_folder, exist_ok=True)

# Helper: Calculate dBFS of a segment safely
def safe_dbfs(segment):
    return segment.dBFS if segment.dBFS != float('-inf') else -100.0

def slice_audio_dynamic_threshold(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    sound = AudioSegment.from_file(file_path)

    current_start = 0
    clip_index = 0
    clip_times = []

    while current_start < len(sound):
        window = sound[current_start:current_start+chunk_size_ms]
        window_dbfs = safe_dbfs(window)

        silence_thresh = window_dbfs + silence_thresh_relative

        if window_dbfs > silence_thresh:
            end = current_start + chunk_size_ms
            while end < len(sound) and (end - current_start) < 10000:
                next_chunk = sound[end:end+chunk_size_ms]
                if safe_dbfs(next_chunk) + silence_thresh_relative < silence_thresh:
                    break
                end += chunk_size_ms

            clip = sound[current_start:end]
            if len(clip) >= min_clip_ms:
                output_name = os.path.join(output_folder, f"{base_name}_{clip_index}.wav")
                clip.export(output_name, format="wav", parameters=["-acodec", "pcm_s16le"])
                print(f"✅ Saved clip: {output_name} ({len(clip)} ms)")
                clip_index += 1
                clip_times.append((current_start, end))

            current_start = end
        else:
            current_start += chunk_size_ms

    # If enabled, draw a plot
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

print("\n🔍 Scanning for recordings to process...")
for filename in os.listdir(input_folder):
    if filename.endswith('.wav'):
        full_path = os.path.join(input_folder, filename)
        print(f"\n🎧 Processing: {filename}")
        slice_audio_dynamic_threshold(full_path)

print("\n🏁 Done!")
