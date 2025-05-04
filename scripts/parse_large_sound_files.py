import os
from pydub import AudioSegment

# SETTINGS
input_folder = './recordings/chunks'
output_folder = './recordings/clips'
chunk_length_ms = 5 * 60 * 1000  # 5 minutes

os.makedirs(output_folder, exist_ok=True)

def split_and_delete(file_path, chunk_length=chunk_length_ms):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    audio = AudioSegment.from_wav(file_path)
    total_length = len(audio)

    part = 0
    for start in range(0, total_length, chunk_length):
        end = min(start + chunk_length, total_length)
        chunk = audio[start:end]
        output_name = f"{base_name}_part{part}.wav"
        output_path = os.path.join(output_folder, output_name)
        chunk.export(output_path, format="wav")
        print(f"✅ Wrote: {output_name} ({(end-start)/1000:.1f}s)")
        part += 1

    # Delete original file after processing
    os.remove(file_path)
    print(f"🗑️ Deleted original: {file_path}")

# MAIN
print("\n🔍 Looking for .wav files to split...")
for filename in os.listdir(input_folder):
    if filename.endswith('.wav'):
        file_path = os.path.join(input_folder, filename)
        print(f"\n🎧 Splitting: {filename}")
        split_and_delete(file_path)

print("\n🏁 All files processed.")
