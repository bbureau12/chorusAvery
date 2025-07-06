import os
from pydub import AudioSegment

def process_ambient_noises(source_dir, output_dir, chunk_length_ms=5000, target_volume_reduction_db=15):
    files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.mp3', '.wav'))]
    if not files:
        print("🚫 No audio files found in augmentation noise folder.")
        return

    shift_intervals_ms = [0, 500, 1000]  # add more shifts if you want more diversity

    for file_name in files:
        file_path = os.path.join(source_dir, file_name)
        print(f"\n🎧 Processing: {file_name}")

        # Load and standardize
        sound = AudioSegment.from_file(file_path)
        sound = sound.set_channels(1)            # Mono
        sound = sound.set_frame_rate(16000)      # 16kHz
        sound = sound - target_volume_reduction_db  # Reduce volume for mixing

        # Process shifted chunks
        for shift in shift_intervals_ms:
            shifted_sound = sound[shift:] if shift < len(sound) else None
            if shifted_sound is None or len(shifted_sound) < chunk_length_ms // 2:
                continue  # skip if nothing left after shift

            for i in range(0, len(shifted_sound), chunk_length_ms):
                chunk = shifted_sound[i:i + chunk_length_ms]
                if len(chunk) < chunk_length_ms // 2:
                    continue  # skip very short tail chunks
                chunk_name = f"{os.path.splitext(file_name)[0]}_shift{shift}_{str(i // chunk_length_ms).zfill(4)}.wav"
                chunk_path = os.path.join(output_dir, chunk_name)
                chunk.export(chunk_path, format="wav")
                print(f"🎵 Saved shifted chunk: {chunk_name}")

        # Optionally reverse
        reverse = input(f"🔄 Reverse {file_name} for extra variety? (y/n): ").strip().lower()
        if reverse == 'y':
            reversed_sound = sound.reverse()
            for i in range(0, len(reversed_sound), chunk_length_ms):
                chunk = reversed_sound[i:i + chunk_length_ms]
                if len(chunk) < chunk_length_ms // 2:
                    continue
                chunk_name = f"{os.path.splitext(file_name)[0]}_rev_{str(i // chunk_length_ms).zfill(4)}.wav"
                chunk_path = os.path.join(output_dir, chunk_name)
                chunk.export(chunk_path, format="wav")
                print(f"🎵 Saved reversed chunk: {chunk_name}")

        # Delete original
        os.remove(file_path)
        print(f"🗑️ Deleted original file: {file_name}")

    print("\n🏁 Ambient noise processing complete!")

if __name__ == "__main__":
    process_ambient_noises(
        source_dir="./recordings/augmentation_noise",
        output_dir="./recordings/augmentation_noise"
    )
