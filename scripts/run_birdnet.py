import os
import subprocess
from pathlib import Path

# Path to BirdNET Analyzer CLI
BIRDNET_CLI = Path(__file__).resolve().parent.parent / "BirdNET-Analyzer" / "birdnet_analyzer" / "cli.py"

# Paths for input and output
RAW_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_analysis():
    print(f"🔍 Scanning for WAV files in: {RAW_DIR}")
    for file in RAW_DIR.glob("*.wav"):
        output_file = OUTPUT_DIR / f"{file.stem}_analysis.csv"
        print(f"🎧 Analyzing: {file.name}")
        cmd = [
            "python",
            str(BIRDNET_CLI),
            "--i", str(file),
            "--o", str(OUTPUT_DIR),
            "--sf", "0.0",
            "--ef", "1.0"
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ Saved: {output_file.name}\n")

if __name__ == "__main__":
    run_analysis()
