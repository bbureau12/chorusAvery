import csv
from pathlib import Path
from pydub import AudioSegment

CHUNKS_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw" / "chunks"
RAW_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "data" / "combined_analysis.csv"
MIN_CONFIDENCE = 0.1

def get_file_durations(wav_dir):
    durations = {}
    for wav in sorted(wav_dir.glob("*.wav")):
        audio = AudioSegment.from_wav(wav)
        durations[wav.stem] = len(audio) / 1000.0  # ms → sec
    return durations

def calculate_cumulative_offsets(durations):
    offsets = {}
    current_offset = 0.0
    for name in sorted(durations):  # Sort to preserve file order
        offsets[name] = current_offset
        current_offset += durations[name]
    return offsets

def merge_outputs():
    files = list(CHUNKS_DIR.glob("*.BirdNET.selection.table.txt"))
    if not files:
        print("❌ No analysis files found.")
        return

    print(f"📄 Merging {len(files)} chunk outputs...")

    # Step 1: Load durations of each full raw WAV file
    durations = get_file_durations(RAW_DIR)
    file_offsets = calculate_cumulative_offsets(durations)

    combined_rows = []
    header = []
    print(f"📄 entering for loop...")
    for f in files:
        with open(f, newline='', encoding='utf-8') as csvfile:
            print(f"📄 entering file...")
            reader = csv.reader(csvfile, delimiter='\t')
            rows = list(reader)

            if not header:
                header = rows[0] + ["Original File", "Chunk", "Global Begin Time (s)", "Global End Time (s)"]

            for row in rows[1:]:
                try:
                    confidence = float(row[9])
                    if confidence < MIN_CONFIDENCE:
                        continue

                    offset_sec = float(row[11])  # File Offset (s)
                    begin_time = float(row[3]) + offset_sec
                    end_time = float(row[4]) + offset_sec

                    original_stem = f.stem.split("_chunk")[0]
                    recording_offset = file_offsets.get(original_stem, 0.0)

                    global_begin = begin_time + recording_offset
                    global_end = end_time + recording_offset

                    chunk_part = f.name.replace(".BirdNET.selection.table.txt", "").split("_chunk")[1]
                    chunk_index = int(chunk_part)

                    combined_rows.append(row + [
                        original_stem, 
                        chunk_index, 
                        global_begin, 
                        global_end
                    ])
                except (ValueError, IndexError) as e:
                    print(f"❌ Skipping due to error in {f.name}: {e}")
                    continue

    # Write the merged output
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as out_csv:
        writer = csv.writer(out_csv, delimiter='\t')
        writer.writerow(header)
        writer.writerows(combined_rows)

    print(f"✅ Merged {len(combined_rows)} detections → {OUTPUT_CSV.name}")

if __name__ == "__main__":
    merge_outputs()
