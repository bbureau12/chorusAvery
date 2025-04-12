import os
import subprocess
import csv
import sys
import uuid
from pathlib import Path
from pydub import AudioSegment
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.load_detections_from_csv import load_detections_from_csv
from utils.location_selector import choose_location
from utils.split_wav import split_wav
# Configuration
INPUT_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_DIR = INPUT_DIR / "chunks"
CHUNK_DURATION_MS = 60 * 1000  # 1 minute

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

def run_birdnet(file_path):
    print(f"🎷 Analyzing: {file_path.name}")
    cmd = [
        "python", "-m", "birdnet_analyzer.analyze",
        str(file_path),
        "--lat", "45.4",
        "--lon", "-93.0",
        "--week", "16"  # This will be replaced dynamically
    ]
    subprocess.run(cmd, check=True)

def merge_results(chunk_path, chunk_index, original_file, location_id):
    offset_seconds = (CHUNK_DURATION_MS // 1000) * chunk_index
    matching = list(chunk_path.parent.glob(f"{chunk_path.stem}*.txt"))
    if not matching:
        print(f"⚠️ Missing result for chunk: {chunk_path.name}")
        return []

    result_file = matching[0]
    detections = []
    with result_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                adjusted_start = float(row["Begin Time (s)"]) + offset_seconds
                confidence = float(row.get("Confidence", 0))
                if confidence >= 0.6:
                    detections.append({
                        "original_file": original_file.name,
                        "adjusted_start_time": adjusted_start,
                        "duration": float(row["End Time (s)"]) - float(row["Begin Time (s)"]),
                        "confidence": confidence,
                        "common_name": row.get("Common Name", ""),
                        "species_code": row.get("Species Code", "")
                    })
            except (KeyError, ValueError):
                continue
    return detections

def run_batch_analysis():
    location = choose_location()
    if not location:
        print("❌ No location selected. Exiting.")
        return
    location_id = location["id"]
    print(f"📍 Using location: {location['name']} (ID: {location_id})")
    print(f"🔍 Scanning for WAV files in: {INPUT_DIR}")
    wav_files = list(INPUT_DIR.glob("*.wav"))

    for file in wav_files:
        print(f"📁 Processing {file.name}")
        all_detections = []
        chunks = split_wav(file)
        for chunk_path, chunk_index in chunks:
            run_birdnet(chunk_path)
            detections = merge_results(chunk_path, chunk_index, file, location_id)
            all_detections.extend(detections)

        if all_detections:
            date_part = file.name[:6]  # Assumes format yymmdd_....
            final_path = OUTPUT_DIR / f"{date_part}_results.csv"

            if final_path.exists():
                unique_id = str(uuid.uuid4())[:8]
                final_path = OUTPUT_DIR / f"{date_part}_results_{unique_id}.csv"

            print(f"📂 Writing {len(all_detections)} detections to {final_path.name}")
            with final_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "original_file", "adjusted_start_time", "duration",
                    "confidence", "common_name", "species_code"
                ])
                writer.writeheader()
                writer.writerows(all_detections)
            load_detections_from_csv(final_path, location_id)

    print("✅ All done!")

if __name__ == "__main__":
    run_batch_analysis()
