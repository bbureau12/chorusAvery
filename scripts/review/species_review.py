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

    def search_species(self, query):
        query = query.lower()
        return [(id_, name) for id_, name in self.species_list if query in name.lower()]

    def play_clip(self, file_path):
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
        # 1️⃣ Find species ID
        species_id = None
        for id_, name in self.species_list:
            if name.lower() == species_name.lower():
                species_id = id_
                break
        if not species_id:
            print(f"❌ Species '{species_name}' not found.")
            return

        # 2️⃣ Get clips
        clips = self.get_clips_for_species(species_id)
        if not clips:
            print(f"ℹ️ No clips found for species: {species_name}")
            return

        print(f"🔍 Found {len(clips)} clips for species: {species_name}")

        # 3️⃣ Review loop
        for clip_name in clips:
            full_path = os.path.join(self.save_folder, clip_name)
            print(f"\n🎧 Reviewing: {clip_name}")

            self.play_clip(full_path)

            while True:
                action = input("Press ENTER=keep | *=delete annotation | !=replay | r=replace: ").strip().lower()

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

                elif action == 'r':
                    # Replace with another species
                    new_name = input("New species name: ").strip()
                    new_matches = self.search_species(new_name)
                    if not new_matches:
                        print("❌ No match.")
                        continue
                    for idx, (_, name) in enumerate(new_matches):
                        print(f"{idx + 1}. {name}")
                    try:
                        choice = int(input("Choose number: ")) - 1
                        new_id, new_species_name = new_matches[choice]
                    except:
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
                    print(f"🔄 Replaced {species_name} with {new_species_name} for {clip_name}")
                    break

                else:
                    print("⚠️ Invalid input.")

        print("\n🏁 Done reviewing this species!")

    def close(self):
        self.conn.close()
        print("🔒 Database connection closed.")

if __name__ == "__main__":
    reviewer = SpeciesAnnotationReviewer(
        db_path='./db/chorusAvery.db',
        clips_folder='./recordings/clips',
        save_folder='./recording/training_data'
    )

    species_name = input("Species to review: ").strip()
    reviewer.review(species_name)
    reviewer.close()
