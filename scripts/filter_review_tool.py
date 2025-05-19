import os
from pydub import AudioSegment
import simpleaudio as sa
import shutil
import sqlite3

SOURCE_FOLDER = './recordings/filtered'
DEST_FOLDER = './recordings/training'
DB_PATH = './db/chorusAvery.db'
SPECIES_ID = 1

os.makedirs(DEST_FOLDER, exist_ok=True)

def play_clip(file_path):
    sound = AudioSegment.from_file(file_path)
    playback = sa.play_buffer(
        sound.raw_data,
        num_channels=sound.channels,
        bytes_per_sample=sound.sample_width,
        sample_rate=sound.frame_rate
    )
    playback.wait_done()

def review_clips():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    clips = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith('.wav')])
    last_action = None

    for clip in clips:
        full_path = os.path.join(SOURCE_FOLDER, clip)
        print(f"\n▶️ Reviewing: {clip}")
        play_clip(full_path)

        while True:
            choice = input("[Y] keep & annotate / [N] delete / [R] replay / [Enter] repeat last: ").strip().lower()
            if choice == '':
                choice = last_action if last_action else 'r'

            if choice == 'y':
                last_action = 'y'
                # Move to training folder
                dest_path = os.path.join(DEST_FOLDER, clip)
                shutil.move(full_path, dest_path)

                # Get clip ID from database
                cursor.execute("SELECT id FROM Clips WHERE clip_path = ?", (clip,))
                result = cursor.fetchone()
                if result:
                    clip_id = result[0]
                    cursor.execute("""
                        INSERT OR IGNORE INTO ClipAnnotations (clip_id, species_id, verified, notes)
                        VALUES (?, ?, 1, 'Verified by manual review')
                    """, (clip_id, SPECIES_ID))
                    conn.commit()
                    print(f"✅ Moved and annotated: {clip}")
                else:
                    print(f"⚠️ Clip not found in DB: {clip}")
                break
            elif choice == 'n':
                last_action = 'n'
                os.remove(full_path)
                print(f"🗑️ Deleted: {clip}")
                break
            elif choice == 'r':
                last_action = 'r'
                play_clip(full_path)
            else:
                print("⏭️ Invalid choice. Try again.")

    conn.close()

if __name__ == "__main__":
    review_clips()
