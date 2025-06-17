import random
import shutil
import sqlite3
import os
import numpy as np
from pydub import AudioSegment
import simpleaudio as sa
import datetime
import re

class ChorusAveryLabeler:
    def __init__(self, db_path, clips_folder, save_folder, skip_file_limit=1500):
        self.db_path = db_path
        self.clips_folder = clips_folder
        self.save_folder = save_folder
        self.skip_file_limit = skip_file_limit
        self.total_files_processed = 0
        self.total_files_skipped = 0

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.species_list = self._fetch_list("Species")
        self.non_animal_list = self._fetch_list("NonAnimalSounds")

        os.makedirs(self.clips_folder, exist_ok=True)

    def _fetch_list(self, table_name):
        self.cursor.execute(f"SELECT id, name FROM {table_name} ORDER BY name ASC")
        return self.cursor.fetchall()

    def extract_original_filename(self, clip_filename):
        match = re.match(r'^(\d{6}_\d{4})', clip_filename)
        if match:
            return match.group(1)
        raise ValueError(f"❌ Could not determine original file base from: {clip_filename}")

    def parse_date_from_filename(self, filename):
        base = os.path.splitext(filename)[0]
        try:
            main_part, split_index = base.split('~', 1) if '~' in base else (base, None)
            parts = main_part.split('_')
            if len(parts) < 4:
                raise ValueError("Filename does not contain enough parts")
            date_str = parts[0]
            time_str = '_'.join(parts[-3:])
            dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H_%M_%S")
            if split_index == '2':
                dt += datetime.timedelta(seconds=2)
            return dt
        except Exception as e:
            print(f"⚠️ Could not parse datetime from filename: {filename} — {e}")
            return None

    def play_clip(self, file_path):
        sound = AudioSegment.from_file(file_path)
        playback = sa.play_buffer(sound.raw_data, sound.channels, sound.sample_width, sound.frame_rate)
        playback.wait_done()

    def search_items(self, query, items):
        query = query.lower()
        return [(id_, name) for id_, name in items if query in name.lower()]

    def save_labeled_clip(self, clip_name, full_path, labels, sound, boost):
        destination_path = os.path.join(self.save_folder, clip_name)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(full_path, destination_path)
        print(f"📦 Moved labeled file to: {destination_path}")
        max_dbfs, avg_dbfs = self.compute_db_stats(sound)
        print(f"🔊 Max dBFS: {max_dbfs:.2f} | Avg dBFS: {avg_dbfs:.2f}")

        start_dt = self.parse_date_from_filename(clip_name) or datetime.datetime.now()
        duration = len(sound) / 1000.0
        end_dt = start_dt + datetime.timedelta(seconds=duration)

        try:
            source_base = self.extract_original_filename(clip_name)
            self.cursor.execute("SELECT id FROM SourceFiles WHERE filename LIKE ?", (f"{source_base}%",))
            source_row = self.cursor.fetchone()
            if not source_row:
                raise ValueError(f"❌ No SourceFile found starting with: {source_base}")
            source_id = source_row[0]
        except Exception as e:
            print(e)
            return None

        self.cursor.execute("""
            INSERT INTO Clips (clip_path, start_time, end_time, source_id, start_date_source, end_date_source, max_dbfs, avg_dbfs, boost_db)
            VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?)
        """, (clip_name, duration, source_id, start_dt, end_dt, max_dbfs, avg_dbfs, boost))
        clip_id = self.cursor.lastrowid

        for id_, name in labels:
            is_species = (id_, name) in self.species_list
            self.cursor.execute("""
                INSERT INTO ClipAnnotations (clip_id, species_id, non_animal_sound_id, verified, notes)
                VALUES (?, ?, ?, 1, NULL)
            """, (
                clip_id,
                id_ if is_species else None,
                id_ if not is_species else None
            ))

        self.conn.commit()
        return clip_id

    def undo_last_label(self):
        self.cursor.execute("SELECT id, clip_path FROM Clips ORDER BY id DESC LIMIT 1")
        row = self.cursor.fetchone()
        if not row:
            print("🚫 No previous labels to undo.")
            return

        clip_id, clip_name = row
        self.cursor.execute("DELETE FROM ClipAnnotations WHERE clip_id = ?", (clip_id,))
        self.cursor.execute("DELETE FROM Clips WHERE id = ?", (clip_id,))
        self.conn.commit()

        clip_path = os.path.join(self.save_folder, clip_name)
        restore_path = os.path.join(self.clips_folder, clip_name)
        if os.path.exists(clip_path):
            shutil.move(clip_path, restore_path)
            print(f"↩️ Undid last label. Restored: {clip_name}")
        else:
            print(f"⚠️ Labeled file not found: {clip_path}")

    def close(self):
        self.conn.close()
        print("🔒 Database connection closed.")

    def list_clips(self):
        return sorted([f for f in os.listdir(self.clips_folder) if f.endswith('.wav')])
    
    def label_clip(self, clip_name, labels, names):
        boost = 0
        self.total_files_processed += 1
        self.cursor.execute("SELECT id FROM Clips WHERE clip_path = ?", (clip_name,))
        if self.cursor.fetchone():
            print(f"⏭️ Skipping {clip_name} — already labeled.")
            return labels, names

        print(f"\n🎵 Now labeling: {clip_name}")
        full_path = os.path.join(self.clips_folder, clip_name)
        sound = AudioSegment.from_file(full_path)
        duration_seconds = len(sound) / 1000.0
        print(f"⏱️ Clip duration: {duration_seconds:.2f} sec")
        self.play_clip(full_path)

        def apply_label_search(term):
            matches = self.search_items(term, self.species_list + self.non_animal_list)
            if not matches:
                print("No matches found.")
                return
            for idx, (_, name) in enumerate(matches):
                print(f"{idx + 1}. {name}")
            choice = input("Select number(s) separated by commas: ").strip()
            try:
                selected = [int(x) - 1 for x in choice.split(',')]
                for s in selected:
                    if 0 <= s < len(matches) and matches[s] not in labels:
                        labels.append(matches[s])
                        names.append(matches[s][1])
                        print(f"✅ Added: {matches[s][1]}")
            except Exception as e:
                print(f"⚠️ Invalid selection: {e}")

        while True:
            print(f"\n🎯 Selected: {', '.join(names) if names else 'None'}")
            search = input("Search (R=remove, +=louder, -=quieter, /=split, !=replay, *=delete, # clear labels, undo, ENTER=done): ").strip().lower()
            if search == '!':
                self.play_clip(full_path)
            if search == '+':
                sound = AudioSegment.from_file(full_path)
                (sound + 5).export(full_path, format="wav")
                boost += 5
                print("🌟 Volume increased.")
                continue
            if search == '-':
                sound = AudioSegment.from_file(full_path)
                (sound - 5).export(full_path, format="wav")
                boost -= 5
                print("🔇 Volume decreased.")
            elif search == '/':
                base, _ = os.path.splitext(clip_name)
                midpoint = len(sound) // 2
                first_half = sound[:midpoint]
                second_half = sound[midpoint:]
                clip1 = f"{base}~1.wav"
                clip2 = f"{base}~2.wav"
                first_half.export(os.path.join(self.clips_folder, clip1), format="wav")
                second_half.export(os.path.join(self.clips_folder, clip2), format="wav")
                os.remove(full_path)
                print(f"✂️ Split into: {clip1}, {clip2}")
                return 'split', [clip1, clip2]
            elif search == '*':
                os.remove(full_path)
                print(f"🗑️ Deleted {clip_name}.")
                return labels, names
            elif search == 'undo':
                self.undo_last_label()
                return labels, names
            elif search == '':
                break
            elif search == '#':
                labels.clear()
                names.clear()
                print("🔄 Cleared all selected labels.")
            elif search == 'r':
                if not labels:
                    print("🚫 No sounds to remove.")
                    continue
                for idx, (_, name) in enumerate(labels):
                    print(f"{idx + 1}. {name}")
                choice = input("Select number(s) to remove: ").strip()
                try:
                    selected = [int(x) - 1 for x in choice.split(',')]
                    for s in sorted(selected, reverse=True):
                        removed = names.pop(s)
                        labels.pop(s)
                        print(f"❌ Removed: {removed}")
                except Exception as e:
                    print(f"⚠️ Invalid removal: {e}")
            else:
                apply_label_search(search)

        if not labels:
            self.total_files_skipped += 1
            skip_folder = './recording/test/skip'
            os.makedirs(skip_folder, exist_ok=True)
            skip_path = os.path.join(skip_folder, clip_name)
            shutil.move(full_path, skip_path)
            print(f"🚫 Moved unlabeled file to skip folder: {skip_path}")

            skip_files = sorted(
                [f for f in os.listdir(skip_folder) if f.endswith('.wav')],
                key=lambda x: os.path.getctime(os.path.join(skip_folder, x))
            )
            if len(skip_files) > self.skip_file_limit:
                random.shuffle(skip_files)
                for f in skip_files[:-self.skip_file_limit]:
                    os.remove(os.path.join(skip_folder, f))
                    print(f"🗑️ Deleted skip file: {f}")
        else:
            self.save_labeled_clip(clip_name, full_path, labels, sound, boost)

        return labels, names
        
    def compute_db_stats(self, sound):
        samples = np.array(sound.get_array_of_samples())
        peak_amplitude = np.max(np.abs(samples))
        # protect against log(0)
        if peak_amplitude == 0:
            max_dbfs = -float('inf')
        else:
            max_dbfs = 20 * np.log10(peak_amplitude / float(2 ** (8 * sound.sample_width - 1)))
        avg_dbfs = sound.dBFS
        return max_dbfs, avg_dbfs

    def run_labeling_session(self):
        clips = self.list_clips()
        labels = []
        names = []
        i = 0
        while i < len(clips):
            print(f"\n📊 Session Progress: {self.total_files_processed} total processed | {self.total_files_skipped} skipped.")
            clip = clips[i]
            result = self.label_clip(clip, labels, names)
            if isinstance(result, tuple) and result[0] == 'split':
                clips.pop(i)
                for new_clip in reversed(result[1]):
                    clips.insert(i, new_clip)
            else:
                i += 1
        self.close()
        print("\n🏁 All clips labeled.")

if __name__ == "__main__":
    labeler = ChorusAveryLabeler(
        db_path='./db/chorusAvery.db',
        clips_folder='./recordings/clips',
        save_folder='./recording/training_data'
    )
    labeler.run_labeling_session()
