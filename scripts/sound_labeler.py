import shutil
import sqlite3
import os
from pydub import AudioSegment
import simpleaudio as sa
import datetime
import re

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

# === Extract original filename from chunk name ===
def extract_original_filename(clip_filename):
    match = re.match(r'^(\d{6}_\d{4})', clip_filename)
    if match:
        return match.group(1)
    raise ValueError(f"❌ Could not determine original file base from: {clip_filename}")

# === Parse date from filename ===
def parse_date_from_filename(filename):
    base = os.path.splitext(filename)[0]
    try:
        # Split off split index if present
        if '~' in base:
            main_part, split_index = base.split('~', 1)
        else:
            main_part = base
            split_index = None

        parts = main_part.split('_')

        if len(parts) < 4:
            raise ValueError("Filename does not contain enough parts")

        date_str = parts[0]  # e.g. 250513

        # Use the last three parts as hour, minute, second
        time_parts = parts[-3:]
        time_str = '_'.join(time_parts)

        dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H_%M_%S")

        # If split_index == '2', add 2 seconds to avoid overlap
        if split_index == '2':
            dt += datetime.timedelta(seconds=2)

        return dt

    except Exception as e:
        print(f"⚠️ Could not parse datetime from filename: {filename} — {e}")
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

    start_dt = parse_date_from_filename(clip_name)
    if not start_dt:
        start_dt = datetime.datetime.now()

    sound = AudioSegment.from_file(destination_path)
    duration = len(sound) / 1000.0
    end_dt = start_dt + datetime.timedelta(seconds=duration)

    try:
        source_base = extract_original_filename(clip_name)
        cursor.execute("SELECT id FROM SourceFiles WHERE filename LIKE ?", (f"{source_base}%",))
        source_row = cursor.fetchone()
        if not source_row:
            raise ValueError(f"❌ No SourceFile found starting with: {source_base}")
        source_id = source_row[0]
    except Exception as e:
        print(e)
        return None

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
    sound = AudioSegment.from_file(full_path)
    duration_seconds = len(sound) / 1000.0
    duration_str = f"{duration_seconds:.2f} sec"
    print(f"⏱️ Clip duration: {duration_str}")
    play_clip(full_path)

    if labels and names:
        while True:
            use_previous = input(f"Use previous labels ({', '.join(names)})? (Y/n/R/A): ").strip().lower()
            if use_previous == 'n':
                labels.clear()
                names.clear()
                break
            elif use_previous == 'y' or use_previous == '':
                break
            elif use_previous == 'a':
                term = input("🔍 Enter species/sound to add: ").strip()
                matches = search_items(term, species_list + non_animal_list)
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
                                print(f"✅ Added: {matches[s][1]}")
                    except Exception as e:
                        print(f"⚠️ Invalid selection: {e}")
                else:
                    print("No matches found.")
            elif use_previous == 'r':
                if not labels:
                    print("🚫 No sounds to remove.")
                    continue
                print("🔎 Currently selected sounds:")
                for idx, (_, name) in enumerate(labels):
                    print(f"{idx+1}. {name}")
                choice = input("Select number(s) to remove, separated by commas: ").strip()
                try:
                    selected = [int(x)-1 for x in choice.split(',')]
                    selected.sort(reverse=True)
                    for s in selected:
                        if 0 <= s < len(labels):
                            removed_name = names.pop(s)
                            labels.pop(s)
                            print(f"❌ Removed: {removed_name}")
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")
            elif use_previous == '+':
                sound = AudioSegment.from_file(full_path)
                (sound + 5).export(full_path, format="wav")
                print("🌟 Volume increased.")
            elif use_previous == '-':
                sound = AudioSegment.from_file(full_path)
                (sound - 5).export(full_path, format="wav")
                print("🔇 Volume decreased.")
            elif use_previous == '/':
                sound = AudioSegment.from_file(full_path)
                midpoint = len(sound) // 2
                first_half = sound[:midpoint]
                second_half = sound[midpoint:]
                base, ext = os.path.splitext(clip_name)
                clip1_name = f"{base}~1.wav"
                clip2_name = f"{base}~2.wav"
                first_half.export(os.path.join(clips_folder, clip1_name), format="wav")
                second_half.export(os.path.join(clips_folder, clip2_name), format="wav")
                os.remove(full_path)
                print(f"✂️ Split into: {clip1_name}, {clip2_name}")
                return 'split', [clip1_name, clip2_name]
            else:
                print("⚠️ Invalid option. Choose Y, N, R, A, +, -, or /.")

    if not labels:
        while True:
            print(f"\n🎯 Current sounds selected: {', '.join(names) if names else 'None'}")
            search = input("Type to search (R=remove, +=louder, -=quieter, /=split, !=replay, *=delete, undo, or ENTER to finish): ").strip().lower()

            if search == '!':
                play_clip(full_path)
                continue
            if search == '+':
                sound = AudioSegment.from_file(full_path)
                (sound + 5).export(full_path, format="wav")
                print("🌟 Volume increased.")
                continue
            if search == '-':
                sound = AudioSegment.from_file(full_path)
                (sound - 5).export(full_path, format="wav")
                print("🔇 Volume decreased.")
                continue
            if search == '/':
                sound = AudioSegment.from_file(full_path)
                midpoint = len(sound) // 2
                first_half = sound[:midpoint]
                second_half = sound[midpoint:]
                base, ext = os.path.splitext(clip_name)
                clip1_name = f"{base}~1.wav"
                clip2_name = f"{base}~2.wav"
                first_half.export(os.path.join(clips_folder, clip1_name), format="wav")
                second_half.export(os.path.join(clips_folder, clip2_name), format="wav")
                os.remove(full_path)
                print(f"✂️ Split into: {clip1_name}, {clip2_name}")
                return 'split', [clip1_name, clip2_name]
            if search == '*':
                os.remove(full_path)
                print(f"🗑️ Deleted {clip_name}.")
                return labels, names
            if search == 'undo':
                undo_last_label()
                return labels, names
            if search == '':
                break
            if search == 'r':
                if not labels:
                    print("🚫 No sounds to remove.")
                    continue
                print("🔎 Currently selected sounds:")
                for idx, (_, name) in enumerate(labels):
                    print(f"{idx+1}. {name}")
                choice = input("Select number(s) to remove, separated by commas: ").strip()
                try:
                    selected = [int(x)-1 for x in choice.split(',')]
                    selected.sort(reverse=True)
                    for s in selected:
                        if 0 <= s < len(labels):
                            removed_name = names.pop(s)
                            labels.pop(s)
                            print(f"❌ Removed: {removed_name}")
                except Exception as e:
                    print(f"⚠️ Invalid selection: {e}")
                continue

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
                            print(f"✅ Added: {matches[s][1]}")
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
