import os
from pathlib import Path
from pydub import AudioSegment
import sqlite3

# Configuration
DB_PATH = Path(__file__).resolve().parent / "chorusAvery.db"
MYSTERY_AUDIO_DIR = Path(__file__).resolve().parent / "data" / "mystery_audio"
CLUSTER_OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "mystery_clusters"
CLUSTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
WINDOW_MS = 100               # Sliding window size
SILENCE_GAP_MS = 500          # Max silence gap before splitting cluster
VOLUME_THRESHOLD_DB = -45     # Min dBFS to consider window as sound
VOLUME_VARIANCE_DB = 6        # Allowable dBFS variance to continue grouping

def analyze_and_cluster_mystery_segments():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, source_file, start_time, end_time FROM MysterySegments WHERE reviewed = 0")
    segments = cursor.fetchall()

    cluster_id = 0
    for segment_id, source_file, start_time, end_time in segments:
        filename_hint = f"{Path(source_file).stem}_{int(start_time * 1000)}_{int(end_time * 1000)}.wav"
        audio_path = MYSTERY_AUDIO_DIR / filename_hint
        if not audio_path.exists():
            print(f"❌ Missing file: {audio_path}")
            continue

        audio = AudioSegment.from_wav(audio_path)
        segment_length = len(audio)

        clusters = []
        current_cluster = []
        last_sound_time = None
        last_volume = None

        # Sliding window analysis
        for i in range(0, segment_length - WINDOW_MS, WINDOW_MS):
            window = audio[i:i + WINDOW_MS]
            dbfs = window.dBFS if window.dBFS != float("-inf") else -100

            if dbfs >= VOLUME_THRESHOLD_DB:
                if (
                    last_sound_time is None
                    or (i - last_sound_time <= SILENCE_GAP_MS and abs(dbfs - last_volume) <= VOLUME_VARIANCE_DB)
                ):
                    current_cluster.append((i, dbfs))
                else:
                    if current_cluster:
                        clusters.append(current_cluster)
                    current_cluster = [(i, dbfs)]
                last_sound_time = i
                last_volume = dbfs
            else:
                if current_cluster and (i - last_sound_time > SILENCE_GAP_MS):
                    clusters.append(current_cluster)
                    current_cluster = []

        if current_cluster:
            clusters.append(current_cluster)

        # Export each cluster
# Export each cluster + insert into DB
    for cluster in clusters:
        start_ms = cluster[0][0]
        end_ms = cluster[-1][0] + WINDOW_MS
        clip = audio[start_ms:end_ms]
        cluster_filename = f"{Path(source_file).stem}_seg{segment_id}_cluster{cluster_id}.wav"
        cluster_path = CLUSTER_OUTPUT_DIR / cluster_filename
        clip.export(cluster_path, format="wav")
        
        # Log to DB
        cursor.execute("""
            INSERT INTO MysteryClusters (source_file, segment_id, cluster_start, cluster_end, file_path)
            VALUES (?, ?, ?, ?, ?)
        """, (
            source_file,
            segment_id,
            start_ms / 1000,
            end_ms / 1000,
            str(cluster_path)
        ))

    print(f"🎧 Saved + logged: {cluster_path.name}")
    cluster_id += 1


    conn.close()
    print(f"✅ Done. Exported {cluster_id} cluster(s).")

if __name__ == "__main__":
    analyze_and_cluster_mystery_segments()
