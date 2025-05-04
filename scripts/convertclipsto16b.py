from pydub import AudioSegment
import os

# Folder with clips to convert
clips_folder = './recordings/clips'

print("\n🔄 Converting .wav files to 16-bit PCM format...")

for filename in os.listdir(clips_folder):
    if filename.lower().endswith('.wav'):
        file_path = os.path.join(clips_folder, filename)
        try:
            audio = AudioSegment.from_file(file_path)
            audio.export(file_path, format="wav", parameters=["-acodec", "pcm_s16le"])
            print(f"✅ Converted: {filename}")
        except Exception as e:
            print(f"❌ Failed to convert {filename}: {e}")

print("\n🏁 Conversion complete.")
