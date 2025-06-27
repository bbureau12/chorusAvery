import datetime
import json
import sqlite3
import os
from pydub import AudioSegment
import simpleaudio as sa

class SpeciesAnnotationReviewer:
    def __init__(self, db_path, clips_folder, save_folder):
        self.db_path = db_path
        self.clips_folder = clips_folder  # location of original clips if needed
        self.save_folder = save_folder    # location of labeled clips
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.species_list = self._fetch_species()

    def _fetch_species(self):
        self.cursor.execute("SELECT id, name FROM Species ORDER BY name ASC")
        return self.cursor.fetchall()

    def load_progress(self):
        try:
            with open("species_progress.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_progress(self, progress):
        with open("species_progress.json", "w") as f:
            json.dump(progress, f, indent=2)
            
    def search_species(self, query):
        query = query.lower()
        return [(id_, name) for id_, name in self.species_list if query in name.lower()]

    def play_clip(self, file_path):
        file_path = file_path.replace('\\', '/')
        sound = AudioSegment.from_file(file_path)
        playback = sa.play_buffer(sound.raw_data, sound.channels, sound.sample_width, sound.frame_rate)
        playback.wait_done()

    def get_clips_for_species(self, species_id):
        self.cursor.execute("""
            SELECT DISTINCT Clips.clip_path
            FROM Clips
            JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
            WHERE ClipAnnotations.species_id = ?
        """, (species_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def review(self, species_name):
    # 🔍 1️⃣ Search species list with partial match
        matches = self.search_species(species_name)
        if not matches:
            print(f"❌ No species found matching '{species_name}'")
            return

        if len(matches) == 1:
            species_id, selected_name = matches[0]
            print(f"✅ Found single match: {selected_name}")
        else:
            print("🔍 Multiple matches found:")
            for idx, (_, name) in enumerate(matches):
                print(f"{idx + 1}. {name}")
            try:
                choice = int(input("Select species number: ")) - 1
                species_id, selected_name = matches[choice]
            except (ValueError, IndexError):
                print("⚠️ Invalid selection.")
                return

        # 📝 2️⃣ Get clips
        clips = self.get_clips_for_species(species_id)
        if not clips:
            print(f"ℹ️ No clips found for species: {selected_name}")
            return

        print(f"🔍 Found {len(clips)} clips for species: {selected_name}")
        total_clips = len(clips)

        # 🔄 Load progress and offer to resume
        progress = self.load_progress()
        species_key = str(species_id)
        start_idx = 0
        if species_key in progress:
            saved_idx = progress[species_key]
            choice = input(f"⏩ Found saved progress at clip {saved_idx + 1} of {total_clips}. Resume there? (y/n): ").strip().lower()
            if choice == "y":
                start_idx = saved_idx
                print(f"🔄 Resuming from clip {start_idx + 1}.")

        i = start_idx
        while i < total_clips:
            clip_name = clips[i]
            print(f"\n🎧 Reviewing clip {i + 1} of {total_clips}: {clip_name}")

            full_path = os.path.join(self.save_folder, clip_name)

            # ✅ Fetch and display annotations
            self.cursor.execute("""
                SELECT Species.name 
                FROM ClipAnnotations 
                JOIN Species ON ClipAnnotations.species_id = Species.id
                WHERE ClipAnnotations.clip_id = (
                    SELECT id FROM Clips WHERE clip_path = ?
                )
            """, (clip_name,))
            annotations = [row[0] for row in self.cursor.fetchall()]
            if annotations:
                print("📌 Annotations for this clip:")
                for name in annotations:
                    if name.lower() == selected_name.lower():
                        print(f"  ➤ [REVIEWING] {name}")
                    else:
                        print(f"  • {name}")
            else:
                print(f"📌 No annotations yet for this clip.")

            # Play audio
            self.play_clip(full_path)

            while True:
                action = input("Press ENTER=keep | *=delete | !=replay | r=replace | 10m/1h/1d=skip | goto N=jump: ").strip().lower()

                if action == '':
                    print("✅ Kept annotation.")
                    break

                elif action == '*':
                    self.cursor.execute("""
                        DELETE FROM ClipAnnotations 
                        WHERE species_id = ? AND clip_id = (
                            SELECT id FROM Clips WHERE clip_path = ?
                        )
                    """, (species_id, clip_name))
                    self.conn.commit()
                    print(f"🗑️ Deleted species annotation for {clip_name}")
                    break

                elif action == '!':
                    self.play_clip(full_path)

                elif action in ('10m', '1h', '1d'):
                    jump_delta = {
                        '10m': datetime.timedelta(minutes=10),
                        '1h': datetime.timedelta(hours=1),
                        '1d': datetime.timedelta(days=1)
                    }[action]

                    self.cursor.execute("""
                        SELECT end_date_source FROM Clips WHERE clip_path = ?
                    """, (clip_name,))
                    row = self.cursor.fetchone()
                    if not row or not row[0]:
                        print("⚠️ Cannot skip: clip has no end_date_source.")
                        break
                    current_end_dt = datetime.datetime.fromisoformat(row[0])
                    target_dt = current_end_dt + jump_delta

                    self.cursor.execute("""
                        SELECT clip_path, start_date_source FROM Clips
                        WHERE start_date_source >= ?
                        ORDER BY start_date_source ASC
                        LIMIT 1
                    """, (target_dt.isoformat(),))
                    next_row = self.cursor.fetchone()
                    if next_row:
                        next_clip, next_start_dt = next_row
                        print(f"⏩ Skipping to clip starting at {next_start_dt}: {next_clip}")
                        next_idx = next((idx for idx, c in enumerate(clips) if c == next_clip), None)
                        if next_idx is not None:
                            i = next_idx
                        else:
                            print("⚠️ Next clip found in DB but not in current list.")
                        break
                    else:
                        print("⚠️ No clips found that far ahead.")
                        break

                elif action.startswith("goto"):
                    try:
                        parts = action.split()
                        if len(parts) == 2:
                            target_idx = int(parts[1]) - 1
                            if 0 <= target_idx < total_clips:
                                print(f"⏩ Jumping to clip {target_idx + 1} of {total_clips}: {clips[target_idx]}")
                                i = target_idx
                                break
                            else:
                                print(f"⚠️ Invalid clip number: must be 1 to {total_clips}")
                        else:
                            print("⚠️ Usage: goto N (e.g., goto 300)")
                    except ValueError:
                        print("⚠️ Invalid number for goto command.")

                elif action == 'r':
                    new_term = input("New species name: ").strip()
                    new_matches = self.search_species(new_term)
                    if not new_matches:
                        print("❌ No match found.")
                        continue
                    for idx, (_, name) in enumerate(new_matches):
                        print(f"{idx + 1}. {name}")
                    try:
                        new_choice = int(input("Choose number: ")) - 1
                        new_id, new_species_name = new_matches[new_choice]
                    except (ValueError, IndexError):
                        print("⚠️ Invalid choice.")
                        continue

                    self.cursor.execute("""
                        UPDATE ClipAnnotations
                        SET species_id = ?
                        WHERE species_id = ? AND clip_id = (
                            SELECT id FROM Clips WHERE clip_path = ?
                        )
                    """, (new_id, species_id, clip_name))
                    self.conn.commit()
                    print(f"🔄 Replaced {selected_name} with {new_species_name} for {clip_name}")
                    break

                else:
                    print("⚠️ Invalid input.")

            # 🔒 Update and save progress after each clip
            progress[species_key] = i
            self.save_progress(progress)

            i += 1

        print("\n🏁 Done reviewing this species!")





    def close(self):
        self.conn.close()
        print("🔒 Database connection closed.")

if __name__ == "__main__":
    reviewer = SpeciesAnnotationReviewer(
        db_path='./db/chorusAvery.db',
        clips_folder='./recordings/clips',
        save_folder='./recordings/training_data'
    )

    species_name = input("Species to review: ").strip()
    reviewer.review(species_name)
    reviewer.close()
