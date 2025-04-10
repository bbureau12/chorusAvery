import os
import subprocess
import csv
from pathlib import Path
from pydub import AudioSegment

# Configuration
INPUT_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_DIR = INPUT_DIR / "chunks"
CHUNK_DURATION_MS = 60 * 1000  # 1 minute
FINAL_CSV = OUTPUT_DIR / "detections.csv"

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

def split_wav(file_path):
    print(f"🔪 Splitting: {file_path.name}")
    audio = AudioSegment.from_wav(file_path)
    chunks = []
    for i, start in enumerate(range(0, len(audio), CHUNK_DURATION_MS)):
        chunk = audio[start:start + CHUNK_DURATION_MS]
        chunk_name = f"{file_path.stem}_chunk{i:03d}.wav"
        chunk_path = CHUNKS_DIR / chunk_name
        chunk.export(chunk_path, format="wav")
        chunks.append((chunk_path, i))
    print(f"🧩 Created {len(chunks)} chunks.\n")
    return chunks

def run_birdnet(file_path):
    print(f"🎧 Analyzing: {file_path.name}")
    cmd = [
        "python", "-m", "birdnet_analyzer.analyze",
        str(file_path),
        "--lat", "45.4",
        "--lon", "-93.0",
        "--week", "16"
    ]
    subprocess.run(cmd, check=True)

def merge_results(chunk_path, chunk_index, original_file):
    offset_seconds = (CHUNK_DURATION_MS // 1000) * chunk_index

    # Look for any file starting with chunk name and ending in .txt
    matching = list(chunk_path.parent.glob(f"{chunk_path.stem}*.txt"))
    if not matching:
        print(f"⚠️ Missing result for chunk: {chunk_path.name}")
        return []

    result_file = matching[0]  # Assume the first match is the correct result

    detections = []
    with result_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                adjusted_start = float(row["Begin Time (s)"]) + offset_seconds
                detections.append({
                    "original_file": original_file.name,
                    "adjusted_start_time": adjusted_start,
                    "duration": float(row["End Time (s)"]) - float(row["Begin Time (s)"]),
                    "confidence": row.get("Confidence", ""),
                    "common_name": row.get("Common Name", ""),
                    "species_code": row.get("Species Code", "")
                })
            except (KeyError, ValueError):
                continue
    return detections


def write_merged_csv(all_detections):
    if not all_detections:
        print("🚫 No detections to write.")
        return

    print(f"📝 Writing {len(all_detections)} detections to {FINAL_CSV.name}")
    with FINAL_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "original_file", "adjusted_start_time", "duration",
            "confidence", "common_name", "species_code"
        ])

        writer.writeheader()
        writer.writerows(all_detections)

def run_batch_analysis():
    print(f"🔍 Scanning for WAV files in: {INPUT_DIR}")
    all_detections = []

    for file in INPUT_DIR.glob("*.wav"):
        chunks = split_wav(file)
        for chunk_path, chunk_index in chunks:
            run_birdnet(chunk_path)
            detections = merge_results(chunk_path, chunk_index, file)
            all_detections.extend(detections)

    write_merged_csv(all_detections)
    print("✅ All done!")

if __name__ == "__main__":
    run_batch_analysis()
