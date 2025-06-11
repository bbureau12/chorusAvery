import os
from pydub import AudioSegment

# Input folders
keep_folder = './recording/test/keep'
skip_folder = './recording/test/skip'

def safe_dbfs(segment):
    return segment.dBFS if segment.dBFS != float('-inf') else -100.0

def process_file(file_path, silence_thresh_relative, max_dBFS_threshold):
    sound = AudioSegment.from_file(file_path)

    window_dbfs = safe_dbfs(sound)
    silence_thresh = window_dbfs + silence_thresh_relative

    if window_dbfs > silence_thresh and sound.max_dBFS > max_dBFS_threshold:
        return True  # Keep entire file
    else:
        return False  # Skip entire file

def process_folder(folder, label, silence_thresh_relative, max_dBFS_threshold, results):
    print(f"\n🔍 Processing folder: {label}")
    kept = 0
    total = 0

    for filename in os.listdir(folder):
        if filename.endswith('.wav'):
            file_path = os.path.join(folder, filename)
            clip_found = process_file(file_path, silence_thresh_relative, max_dBFS_threshold)
            status = "KEPT" if clip_found else "SKIPPED"
            print(f"{status}: {filename}")
            results.append((filename, label, status))
            if clip_found:
                kept += 1
            total += 1

    print(f"✅ Summary for '{label}': {kept}/{total} files kept ({(kept/total)*100:.1f}%).")

def main():
    print("🎧 Grey Tree Frog Fine-Tuning Harness")

    while True:
        print("\n🔧 Enter parameters:")
        try:
            silence_thresh_relative = float(input("  Silence threshold relative (e.g. -14): "))
            max_dBFS_threshold = float(input("  Max dBFS threshold (e.g. -38): "))
        except ValueError:
            print("❌ Invalid input. Please enter numeric values.")
            continue

        results = []

        process_folder(keep_folder, "keep", silence_thresh_relative, max_dBFS_threshold, results)
        process_folder(skip_folder, "skip", silence_thresh_relative, max_dBFS_threshold, results)

        # Analyze results
        correct_keeps = sum(1 for r in results if r[1] == 'keep' and r[2] == 'KEPT')
        incorrect_skips = sum(1 for r in results if r[1] == 'keep' and r[2] == 'SKIPPED')
        correct_skips = sum(1 for r in results if r[1] == 'skip' and r[2] == 'SKIPPED')
        incorrect_keeps = sum(1 for r in results if r[1] == 'skip' and r[2] == 'KEPT')

        print("\n🔎 Analysis:")
        print(f"✅ Correct keeps: {correct_keeps}")
        print(f"⚠️ Incorrect skips (should have been kept): {incorrect_skips}")
        print(f"✅ Correct skips: {correct_skips}")
        print(f"⚠️ Incorrect keeps (should have been skipped): {incorrect_keeps}")

        total_files = len(results)
        accuracy = (correct_keeps + correct_skips) / total_files * 100 if total_files else 0
        print(f"\n🎯 Overall accuracy: {accuracy:.1f}%")

        cont = input("\n🔄 Would you like to test again with different parameters? (y/n): ").strip().lower()
        if cont != 'y':
            print("🏁 Exiting fine-tuning harness.")
            break

if __name__ == "__main__":
    main()
