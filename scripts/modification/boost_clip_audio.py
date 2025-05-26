from pydub import AudioSegment
import os

# Configuration
clips_folder = './recordings/clips'
boost_db = 6  # Decibels to boost

# Ensure folder exists
if not os.path.exists(clips_folder):
    print(f"❌ Folder not found: {clips_folder}")
    exit()

# Process files
print(f"🔍 Boosting all .wav files in '{clips_folder}' by +{boost_db} dB...")

for filename in os.listdir(clips_folder):
    if filename.endswith('.wav'):
        full_path = os.path.join(clips_folder, filename)
        try:
            sound = AudioSegment.from_file(full_path)
            boosted = sound + boost_db
            boosted.export(full_path, format='wav')
            print(f"✅ Boosted: {filename}")
        except Exception as e:
            print(f"⚠️ Failed to process {filename}: {e}")

print("\n🏁 All files processed.")
