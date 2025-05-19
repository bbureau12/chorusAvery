import os
from pydub import AudioSegment
import simpleaudio as sa
import shutil

SOURCE_FOLDER = './recordings/bandpass'
DEST_FOLDER = './recordings/training'
os.makedirs(DEST_FOLDER, exist_ok=True)

def play_clip(file_path):
    sound = AudioSegment.from_file(file_path)
    playback = sa.play_buffer(
        sound.raw_data,
        num_channels=sound.channels,
        bytes_per_sample=sound.sample_width,
        sample_rate=sound.frame_rate
    )
    playback.wait_done()

def review_clips():
    clips = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith('.wav')])
    for clip in clips:
        full_path = os.path.join(SOURCE_FOLDER, clip)
        print(f"\n▶️ Reviewing: {clip}")
        play_clip(full_path)

        choice = input("[Y] keep / [N] delete / [R] replay: ").strip().lower()
        if choice == 'y':
            shutil.move(full_path, os.path.join(DEST_FOLDER, clip))
            print(f"✅ Moved to training: {clip}")
        elif choice == 'n':
            os.remove(full_path)
            print(f"🗑️ Deleted: {clip}")
        elif choice == 'r':
            play_clip(full_path)
        else:
            print("⏭️ Skipping.")

if __name__ == "__main__":
    review_clips()
