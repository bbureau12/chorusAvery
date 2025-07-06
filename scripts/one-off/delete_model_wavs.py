import os

def delete_wav_files(base_dir="./recordings/model"):
    removed = 0
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(".wav"):
                full_path = os.path.join(root, f)
                os.remove(full_path)
                removed += 1
                print(f"🗑️ Deleted: {full_path}")
    print(f"\n✅ Finished! Removed {removed} .wav files.")

if __name__ == "__main__":
    delete_wav_files()
