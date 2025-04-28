from pydub import AudioSegment
import os
import math

# Settings
input_folder = './recordings/raw'
output_folder = './recordings/clips'
chunk_size_ms = 5000  # 5 seconds
min_clip_ms = 500    # Minimum clip size to save (0.5s)
silence_thresh_relative = -14  # relative to moving window dBFS

os.makedirs(output_folder, exist_ok=True)

# Helper: Calculate dBFS of a segment safely
def safe_dbfs(segment):
    return segment.dBFS if segment.dBFS != float('-inf') else -100.0

# Moving window analysis + clipping
def slice_audio_dynamic_threshold(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    sound = AudioSegment.from_file(file_path)

    current_start = 0
    clip_index = 0

    while current_start < len(sound):
        window = sound[current_start:current_start+chunk_size_ms]
        window_dbfs = safe_dbfs(window)

        silence_thresh = window_dbfs + silence_thresh_relative

        # Detect non-silence within window
        if window.dBFS > silence_thresh:
            # Expand forward until silence or 10s max
            end = current_start + chunk_size_ms
            while end < len(sound) and (end - current_start) < 10000:
                next_chunk = sound[end:end+chunk_size_ms]
                if safe_dbfs(next_chunk) + silence_thresh_relative < silence_thresh:
                    break
                end += chunk_size_ms

            clip = sound[current_start:end]
            if len(clip) >= min_clip_ms:
                output_name = os.path.join(output_folder, f"{base_name}_{clip_index}.wav")
                clip.export(output_name, format="wav")
                print(f"✅ Saved clip: {output_name} ({len(clip)} ms)")
                clip_index += 1

            current_start = end
        else:
            current_start += chunk_size_ms

print("\n🔍 Scanning for recordings to process...")
for filename in os.listdir(input_folder):
    if filename.endswith('.wav'):
        full_path = os.path.join(input_folder, filename)
        print(f"\n🎧 Processing: {filename}")
        slice_audio_dynamic_threshold(full_path)

print("\n🏁 Done!")
