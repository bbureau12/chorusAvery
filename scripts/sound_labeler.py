import random
import shutil
import sqlite3
import os
import numpy as np
from pydub import AudioSegment
import simpleaudio as sa
import datetime
import json
import re
from scipy import signal
import matplotlib.pyplot as plt
from timezonefinder import TimezoneFinder
import pytz

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
        self.tf = TimezoneFinder()

        self.species_list = self._fetch_list("Species")
        self.non_animal_list = self._fetch_list("NonAnimalSounds")

        os.makedirs(self.clips_folder, exist_ok=True)

    def _fetch_list(self, table_name):
        self.cursor.execute(f"SELECT id, name FROM {table_name} ORDER BY name ASC")
        return self.cursor.fetchall()
    
    def get_timezone_for_location(self, cursor, location_id):
        cursor.execute("SELECT latitude, longitude FROM Locations WHERE id = ?", (location_id,))
        row = cursor.fetchone()
        if row:
            lat, lon = row
            tz_name = self.tf.timezone_at(lng=lon, lat=lat)
            if tz_name:
                return pytz.timezone(tz_name)
        return pytz.utc  # Fallback

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

    def delete_sidecar(self, clip_name):
        sidecar_path = os.path.join(self.clips_folder, clip_name.replace(".wav", ".json"))

        if os.path.exists(sidecar_path):
            os.remove(sidecar_path)
            print(f"🗑️ Also deleted sidecar JSON: {os.path.basename(sidecar_path)}")
        else:
            print("ℹ️ No sidecar JSON found to delete.")


    def save_labeled_clip(self, clip_name, full_path, labels, sound, boost):
        self.delete_sidecar(clip_name)
        max_dbfs, avg_dbfs = self.compute_db_stats(sound)
        print(f"🔊 Max dBFS: {max_dbfs:.2f} | Avg dBFS: {avg_dbfs:.2f}")

        start_dt = self.parse_date_from_filename(clip_name)

        duration = len(sound) / 1000.0
        end_dt = start_dt + datetime.timedelta(seconds=duration)

        year_folder = str(start_dt.year)
        destination_dir = os.path.join(self.save_folder, year_folder)
        os.makedirs(destination_dir, exist_ok=True)
        destination_path = os.path.join(destination_dir, clip_name)
        shutil.move(full_path, destination_path)
        relative_clip_path = os.path.join(year_folder, clip_name)

        # Get source file and location ID
        source_base = self.extract_original_filename(clip_name)
        self.cursor.execute("SELECT id, LocationID FROM SourceFiles WHERE filename LIKE ?", (f"{source_base}%",))
        source_row = self.cursor.fetchone()
        if not source_row:
            print(f"❌ No SourceFile found starting with: {source_base}")
            return None

        source_id, location_id = source_row

        # Auto-detect timezone
        tz = self.get_timezone_for_location(self.cursor, location_id)
        if start_dt.tzinfo is None:
            start_dt = tz.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = tz.localize(end_dt)

        # Convert to UTC
        start_dt_utc = start_dt.astimezone(pytz.utc)
        end_dt_utc = end_dt.astimezone(pytz.utc)

        source_base = self.extract_original_filename(clip_name)

        self.cursor.execute("""
            INSERT INTO Clips (
                clip_path, start_time, end_time, source_id,
                start_date_source, end_date_source,
                start_date_utc, end_time_utc,
                max_dbfs, avg_dbfs, boost_db
            )
            VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            relative_clip_path, duration, source_id,
            start_dt.isoformat(), end_dt.isoformat(),
            start_dt_utc.isoformat(), end_dt_utc.isoformat(),
            max_dbfs, avg_dbfs, boost
        ))
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
        trim_ms = 500 
        json_path = os.path.join(self.clips_folder, clip_name.replace(".wav", ".json"))
        original_boost = 0
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as jf:
                    meta = json.load(jf)
                    original_boost = meta.get("boost_applied_db", 0)
                    print(f"📄 Found sidecar JSON: boost_applied_db = {original_boost} dB")
            except Exception as e:
                print(f"⚠️ Could not read sidecar JSON: {e}")

        boost = original_boost  # start boost with the slicer's boost
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
            search = input("Search (R=remove, +=louder, -=quieter, /=split, !=replay, *=delete, # clear labels, b trim from begining, e trim from end, undo, ENTER=done): ").strip().lower()
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
            elif search == '&':
                samples = np.array(sound.get_array_of_samples())
                sample_rate = sound.frame_rate

                frequencies, times, Sxx = signal.spectrogram(samples, fs=sample_rate)

                plt.figure(figsize=(10, 4))
                plt.pcolormesh(times, frequencies, 10 * np.log10(Sxx), shading='gouraud')
                plt.title(f"Spectrogram of {clip_name}")
                plt.ylabel('Frequency [Hz]')
                plt.xlabel('Time [sec]')
                plt.colorbar(label='dB')
                plt.ylim(0, 8000)
                plt.tight_layout()
                plt.show()
                continue
            elif search == '/':
                base, _ = os.path.splitext(clip_name)
                midpoint = len(sound) // 2
                first_half = sound[:midpoint]
                second_half = sound[midpoint:]
                clip1 = f"{base}~1.wav"
                clip2 = f"{base}~2.wav"
                clip1_path = os.path.join(self.clips_folder, clip1)
                clip2_path = os.path.join(self.clips_folder, clip2)
                first_half.export(clip1_path, format="wav")
                second_half.export(clip2_path, format="wav")
                os.remove(full_path)
                print(f"✂️ Split into: {clip1}, {clip2}")

                # Optional: copy sidecar
                original_json = os.path.join(self.clips_folder, clip_name.replace(".wav", ".json"))
                if os.path.exists(original_json):
                    shutil.copy(original_json, clip1_path.replace(".wav", ".json"))
                    shutil.copy(original_json, clip2_path.replace(".wav", ".json"))
                    print(f"📄 Duplicated sidecar JSON for split clips.")
                else:
                    print(f"ℹ️ No sidecar JSON found for original clip to copy.")

                return 'split', [clip1, clip2]
            elif search == '*':
                os.remove(full_path)
                print(f"🗑️ Deleted {clip_name}.")

                sidecar_path = os.path.join(self.clips_folder, clip_name.replace(".wav", ".json"))
                if os.path.exists(sidecar_path):
                    os.remove(sidecar_path)
                    print(f"🗑️ Also deleted sidecar JSON: {os.path.basename(sidecar_path)}")
                else:
                    print("ℹ️ No sidecar JSON found to delete.")

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
            elif search == 'b':
                # Trim from beginning
                sound = AudioSegment.from_file(full_path)
                if len(sound) > trim_ms:
                    trimmed = sound[trim_ms:]
                    trimmed.export(full_path, format="wav")
                    print(f"✂️ Trimmed {trim_ms/1000:.1f} sec from BEGINNING.")
                else:
                    print("⚠️ Clip too short to trim.")

            elif search == 'e':
                # Trim from end
                sound = AudioSegment.from_file(full_path)
                if len(sound) > trim_ms:
                    trimmed = sound[:-trim_ms]
                    trimmed.export(full_path, format="wav")
                    print(f"✂️ Trimmed {trim_ms/1000:.1f} sec from END.")
                else:
                    print("⚠️ Clip too short to trim.")
            else:
                apply_label_search(search)

        if not labels:
            self.total_files_skipped += 1
            skip_folder = './recording/test/skip'
            os.makedirs(skip_folder, exist_ok=True)
            skip_path = os.path.join(skip_folder, clip_name)
            shutil.move(full_path, skip_path)
            # Delete associated sidecar if present
            sidecar_path = os.path.join(self.clips_folder, clip_name.replace(".wav", ".json"))
            if os.path.exists(sidecar_path):
                os.remove(sidecar_path)
                print(f"🗑️ Also deleted sidecar JSON: {os.path.basename(sidecar_path)}")
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
        save_folder='./recordings/training_data'
    )
    labeler.run_labeling_session()
