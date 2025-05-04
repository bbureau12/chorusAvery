import sqlite3
import os
from pydub import AudioSegment
import simpleaudio as sa

# SETTINGS
db_path = './db/chorusAvery.db'
clips_folder = './recordings/clips'

# Connect to DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch species and non-animal sounds
cursor.execute("SELECT id, name FROM Species ORDER BY name ASC")
species_list = cursor.fetchall()

cursor.execute("SELECT id, name FROM NonAnimalSounds ORDER BY name ASC")
non_animal_list = cursor.fetchall()

def play_clip(file_path):
    sound = AudioSegment.from_file(file_path)
    playback = sa.play_buffer(
        sound.raw_data,
        num_channels=sound.channels,
        bytes_per_sample=sound.sample_width,
        sample_rate=sound.frame_rate
    )
    playback.wait_done()

def search_items(query, items):
    query = query.lower()
    return [(id_, name) for id_, name in items if query in name.lower()]
def label_clip(clip_name, labels, names):
    # Skip if already in DB
    cursor.execute("SELECT id FROM Clips WHERE clip_path = ?", (clip_name,))
    if cursor.fetchone():
        print(f"⏭️  Skipping {clip_name} — already labeled.")
        return labels, names

    print(f"\n🎵 Now labeling: {clip_name}")
    full_path = os.path.join(clips_folder, clip_name)
    play_clip(full_path)

    if labels and names:
        use_previous = input(f"Use previous labels ({', '.join(names)})? (Y/n): ").strip().lower()
        if use_previous == 'n':
            labels.clear()
            names.clear()

    if not labels:
        while True:
            search = input("Type to search species or sounds (ENTER to finish): ").strip()
            if not search:
                break

            matches = search_items(search, species_list) + search_items(search, non_animal_list)
            if matches:
                for idx, (id_, name) in enumerate(matches):
                    print(f"{idx+1}. {name}")
                choice = input("Select number(s) separated by commas: ").strip()
                try:
                    selected = [int(x)-1 for x in choice.split(',')]
                    for s in selected:
                        if 0 <= s < len(matches):
                            labels.append(matches[s])
                            names.append(matches[s][1])
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")
            else:
                print("No matches found.")

    # Save to database
    cursor.execute("""
        INSERT INTO Clips (clip_path, start_time, end_time)
        VALUES (?, 0, 0)
    """, (clip_name,))
    clip_id = cursor.lastrowid

    for id_, name in labels:
        is_species = (id_, name) in species_list
        cursor.execute("""
            INSERT INTO ClipAnnotations (clip_id, species_id, non_animal_sound_id, verified, notes)
            VALUES (?, ?, ?, 1, NULL)
        """, (
            clip_id,
            id_ if is_species else None,
            id_ if not is_species else None
        ))

    conn.commit()
    print(f"✅ Labels saved for {clip_name}!\n")
    return labels, names

# MAIN
os.makedirs(clips_folder, exist_ok=True)
clips = sorted([f for f in os.listdir(clips_folder) if f.endswith('.wav')])

labels = []
names = []

for clip in clips:
    labels, names = label_clip(clip, labels, names)


conn.close()
print("\n🏁 All clips labeled!")
