import subprocess
import sys
import os

TOOLS = [
    {
        "name": "Download audio files from a list",
        "script": "scripts/import/import_new_soundfile.py"
    },
    {
        "name": "Chunk audio into 5-minute increments",
        "script": "scripts/step_1_chunk_generator.py"
    },
    {
        "name": "Scan for sound and grab 5-second sound bites",
        "script": "scripts/step_2_clip_parserv2.py"
    },
    {
        "name": "Play sound bites and log them to the database",
        "script": "scripts/sound_labeler.py"
    },
    {
        "name": "Upload temperature recordings (CSV)",
        "script": "scripts/readings/import_temperatures.py"
    },
    {
        "name": "Upload weather readings from API",
        "script": "scripts/readings/import_readings.py"
    },
    {
        "name": "Run BirdNET scan",
        "script": "scripts/run_birdnet.py"
    }
]

def main():
    print("\nChorus Avery Toolbox — Select a tool to run:\n")
    for idx, tool in enumerate(TOOLS, 1):
        print(f"  {idx}. {tool['name']}")
    print("  0. Exit\n")
    try:
        choice = int(input("Enter number: ").strip())
    except ValueError:
        print("Invalid input. Exiting.")
        return
    if choice == 0:
        print("Goodbye!")
        return
    if 1 <= choice <= len(TOOLS):
        script = TOOLS[choice-1]["script"]
        if script is None:
            print("No script assigned for this tool yet.")
            return
        script_path = os.path.join(os.path.dirname(__file__), script)
        print(f"\nRunning: {script_path}\n{'-'*40}")
        subprocess.run([sys.executable, script_path])
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
