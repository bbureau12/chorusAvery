import shutil
import sqlite3
import os
from pydub import AudioSegment
import simpleaudio as sa
import datetime

# === SETTINGS ===
db_path = './db/chorusAvery.db'
clips_folder = './recordings/clips'
save_folder = './recording/training_data'

# === Connect to DB ===
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === Load species and sound options ===
cursor.execute("SELECT id, name FROM Species ORDER BY name ASC")
species_list = cursor.fetchall()

cursor.execute("SELECT id, name FROM NonAnimalSounds ORDER BY name ASC")
non_animal_list = cursor.fetchall()

# === Parse date from filename ===
def parse_date_from_filename(filename):
    base = os.path.splitext(filename)[0]
    try:
        parts = base.split('_')
        if len(parts) < 3:
            raise ValueError("Filename does not contain enough parts")
        
        date_str = parts[0]           # '250511'
        time_str = '_'.join(parts[2:])  # '22_14_07'
        dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H_%M_%S")
        return dt
    except Exception:
        print(f"⚠️ Could not parse datetime from filename: {filename}")
        return None
    
# === Play clip ===
def play_clip(file_path):
    sound = AudioSegment.from_file(file_path)
    playback = sa.play_buffer(
        sound.raw_data,
        num_channels=sound.channels,
        bytes_per_sample=sound.sample_width,
        sample_rate=sound.frame_rate
    )
    playback.wait_done()

# === Search helper ===
def search_items(query, items):
    query = query.lower()
    return [(id_, name) for id_, name in items if query in name.lower()]

# === Save labeled clip and metadata ===
def save_labeled_clip(clip_name, full_path, labels):
    destination_path = os.path.join(save_folder, clip_name)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    shutil.move(full_path, destination_path)
    print(f"📦 Moved labeled file to: {destination_path}")

    # Parse start time from filename
    start_dt = parse_date_from_filename(clip_name)
    if not start_dt:
        start_dt = datetime.datetime.now()

    sound = AudioSegment.from_file(destination_path)
    duration = len(sound) / 1000.0  # in seconds
    end_dt = start_dt + datetime.timedelta(seconds=duration)

    # Write to DB
    cursor.execute("""
        INSERT OR IGNORE INTO SourceFiles (filename, From_Date, To_Date)
        VALUES (?, ?, ?)
    """, (clip_name, start_dt, end_dt))
    source_id = cursor.lastrowid or cursor.execute(
        "SELECT id FROM SourceFiles WHERE filename = ?", (clip_name,)
    ).fetchone()[0]

    cursor.execute("""
        INSERT INTO Clips (clip_path, start_time, end_time, source_id, start_date_source, end_date_source)
        VALUES (?, 0, ?, ?, ?, ?)
    """, (clip_name, duration, source_id, start_dt, end_dt))
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
    return clip_id

# === Undo most recent label ===
def undo_last_label():
    cursor.execute("SELECT id, clip_path FROM Clips ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("🚫 No previous labels to undo.")
        return

    clip_id, clip_name = row
    cursor.execute("DELETE FROM ClipAnnotations WHERE clip_id = ?", (clip_id,))
    cursor.execute("DELETE FROM Clips WHERE id = ?", (clip_id,))
    conn.commit()

    clip_path = os.path.join(save_folder, clip_name)
    restore_path = os.path.join(clips_folder, clip_name)
    if os.path.exists(clip_path):
        shutil.move(clip_path, restore_path)
        print(f"↩️ Undid last label. Restored: {clip_name}")
    else:
        print(f"⚠️ Labeled file not found: {clip_path}")

# === Label single clip ===
def label_clip(clip_name, labels, names):
    cursor.execute("SELECT id FROM Clips WHERE clip_path = ?", (clip_name,))
    if cursor.fetchone():
        print(f"⏭️ Skipping {clip_name} — already labeled.")
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
            search = input("Type to search species/sounds (or '/' to split, '+' to amplify, '-' to reduce, '!' to replay, '*' to delete, 'undo', or ENTER to finish): ").strip()

            if search == '!':
                play_clip(full_path)
                continue
            if search == '*':
                os.remove(full_path)
                print(f"🗑️ Deleted {clip_name}.")
                return labels, names
            if search == 'undo':
                undo_last_label()
                return labels, names
            if search == '/':
                sound = AudioSegment.from_file(full_path)
                midpoint = len(sound) // 2
                first_half = sound[:midpoint]
                second_half = sound[midpoint:]
                base, ext = os.path.splitext(clip_name)
                clip1_name = f"{base}_1.wav"
                clip2_name = f"{base}_2.wav"
                first_half.export(os.path.join(clips_folder, clip1_name), format="wav")
                second_half.export(os.path.join(clips_folder, clip2_name), format="wav")
                os.remove(full_path)
                print(f"✂️ Split into: {clip1_name}, {clip2_name}")
                return 'split', [clip1_name, clip2_name]
            if search == '+':
                sound = AudioSegment.from_file(full_path)
                (sound + 5).export(full_path, format="wav")
                print("🌟 Volume increased.")
                continue
            if search == '-':
                sound = AudioSegment.from_file(full_path)
                (sound - 5).export(full_path, format="wav")
                print("🔇 Volume reduced.")
                continue
            if not search:
                break

            matches = search_items(search, species_list + non_animal_list)
            if matches:
                for idx, (id_, name) in enumerate(matches):
                    print(f"{idx+1}. {name}")
                choice = input("Select number(s) separated by commas: ").strip()
                try:
                    selected = [int(x)-1 for x in choice.split(',')]
                    for s in selected:
                        if 0 <= s < len(matches) and matches[s] not in labels:
                            labels.append(matches[s])
                            names.append(matches[s][1])
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")
            else:
                print("No matches found.")

    if len(labels) == 0:
        os.remove(full_path)
        print(f"🗑️ Removed unlabeled file: {clip_name}")
    else:
        save_labeled_clip(clip_name, full_path, labels)

    return labels, names

# === MAIN LOOP ===
os.makedirs(clips_folder, exist_ok=True)
clips = sorted([f for f in os.listdir(clips_folder) if f.endswith('.wav')])

labels = []
names = []
i = 0

while i < len(clips):
    clip = clips[i]
    result = label_clip(clip, labels, names)
    if isinstance(result, tuple) and result[0] == 'split':
        clips.pop(i)
        for new_clip in reversed(result[1]):
            clips.insert(i, new_clip)
    else:
        i += 1

conn.close()
print("\n🏁 All clips labeled.")
