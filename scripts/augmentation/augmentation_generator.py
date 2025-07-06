import os
import random
import sqlite3
import csv
from pydub import AudioSegment
from utils.generate_spectogram import generate_mel_spectrogram

class AugmentedClipGenerator:
    def __init__(self, db_path, output_dir):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize CSV log
        log_path = os.path.join(output_dir, "augmentation_log.csv")
        self.log_file = open(log_path, "w", newline="", encoding="utf-8")
        self.log_writer = csv.DictWriter(self.log_file, fieldnames=[
            "species_file", "non_species_file", "spectrogram", "duration_s",
            "species_peak_dbfs", "non_species_peak_dbfs", "target_snr_db", "boost_applied_db"
        ])
        self.log_writer.writeheader()
        print(f"📓 Logging augmentations to {log_path}")

    def fetch_files(self, target_species_id, location_id=8):
        """
        Fetches species clips (only with target species) and non-species clips (with no species).
        Returns list of tuples: (species_clip_path, non_species_clip_path).
        """
        print(f"🔎 Fetching clean clips for species ID {target_species_id}...")

        # ✅ Species clips: must have target species, no other species, no non-species
        self.cursor.execute("""
            SELECT Clips.clip_path
            FROM Clips
            JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
            JOIN SourceFiles ON Clips.source_id = SourceFiles.id
            WHERE 
            ClipAnnotations.species_id = ?
            AND SourceFiles.LocationID = ?
            AND (
                SELECT COUNT(*) FROM ClipAnnotations AS ca
                WHERE ca.clip_id = Clips.id
                AND ca.species_id IS NOT NULL

                AND ca.species_id != ?
            ) = 0
            AND (
                SELECT COUNT(*) FROM ClipAnnotations AS ca
                WHERE ca.clip_id = Clips.id
                AND ca.non_animal_sound_id IS NOT NULL
            ) = 0
        """, (target_species_id, location_id, target_species_id))
        species_clips = [row[0] for row in self.cursor.fetchall()]

        print(f"✅ Found {len(species_clips)} clean species clips.")

        # ✅ Non-species clips: must have non-animal sounds marked as ambience, and no species annotations
        self.cursor.execute("""
            SELECT Clips.clip_path
            FROM Clips
            JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
            JOIN NonAnimalSounds ON ClipAnnotations.non_animal_sound_id = NonAnimalSounds.id
            WHERE ClipAnnotations.non_animal_sound_id IS NOT NULL
            AND NonAnimalSounds.is_ambience = 1
            AND (
                SELECT COUNT(*) FROM ClipAnnotations AS ca
                WHERE ca.clip_id = Clips.id
                AND ca.species_id IS NOT NULL
            ) = 0
        """)
        non_species_clips = [row[0] for row in self.cursor.fetchall()]

        print(f"✅ Found {len(non_species_clips)} clean non-species clips.")

        # Generate 4 overlay pairs for each species clip
        pairs = []
        for species_path in species_clips:
            for _ in range(4):
                non_species_path = random.choice(non_species_clips)
                pairs.append((species_path, non_species_path))

        print(f"🎯 Prepared {len(pairs)} overlay pairs for augmentation.")
        return pairs

    def overlay_clips(self, species_file, non_species_file, pad_ms=500, vol_jitter_db=3, target_ms=2500):
        """
        Overlay species audio with dynamically boosted non-species audio to achieve random target SNR.
        Pads, adjusts, and generates spectrogram. Logs augmentation details.
        """
        species = AudioSegment.from_file(os.path.join("./recordings/training_data", species_file))
        non_species = AudioSegment.from_file(os.path.join("./recordings/training_data", non_species_file))

        # 🔹 Randomly pad species
        if random.choice([True, False]):
            species = AudioSegment.silent(duration=pad_ms) + species
        else:
            species = species + AudioSegment.silent(duration=pad_ms)

        # 🔹 Random volume jitter
        jitter = random.uniform(-vol_jitter_db, vol_jitter_db)
        species = species + jitter
        print(f"🔊 Applied volume jitter of {jitter:.2f} dB")

        # 🔹 Adjust lengths: match clips to the shorter one
        min_len = min(len(species), len(non_species))
        species = species[:min_len]
        non_species = non_species[:min_len]

        # 🔹 Compute dynamic SNR boost
        species_peak = species.max_dBFS
        non_species_peak = non_species.max_dBFS
        target_snr = random.uniform(5, 10)  # target species 5–10dB louder
        required_non_species_peak = species_peak - target_snr
        boost_needed = required_non_species_peak - non_species_peak
        non_species = non_species + boost_needed
        print(f"🔊 Dynamic boost: adjusted non-species by {boost_needed:.2f} dB to get target SNR of {target_snr:.2f} dB")

        # Mix
        overlaid = species.overlay(non_species)

        # Check peaks
        if species.max_dBFS <= non_species.max_dBFS:
            print(f"🚫 Skipped overlay: species peak ({species.max_dBFS:.1f} dBFS) <= non-species peak ({non_species.max_dBFS:.1f} dBFS)")
            return None

        # 🔹 Enforce fixed length
        if len(overlaid) < target_ms:
            padding = AudioSegment.silent(duration=target_ms - len(overlaid))
            overlaid = overlaid + padding
            print(f"📏 Padded clip to {target_ms/1000:.2f}s")
        elif len(overlaid) > target_ms:
            overlaid = overlaid[:target_ms]
            print(f"✂️ Trimmed clip to {target_ms/1000:.2f}s")
        else:
            print(f"✅ Clip already at target length: {target_ms/1000:.2f}s")

        # 🔹 Generate spectrogram directly from audio
        overlaid_filename = f"aug_{os.path.splitext(os.path.basename(species_file))[0]}_{os.path.splitext(os.path.basename(non_species_file))[0]}"
        spectrogram_path = os.path.join(self.output_dir, f"{overlaid_filename}.png")
        duration_sec = len(overlaid) / 1000.0
        generate_mel_spectrogram(overlaid, spectrogram_path)
        print(f"🖼️ Saved spectrogram: {spectrogram_path}")

        # 🔹 Log augmentation details
        self.log_writer.writerow({
            "species_file": species_file,
            "non_species_file": non_species_file,
            "spectrogram": os.path.basename(spectrogram_path),
            "duration_s": round(duration_sec, 2),
            "species_peak_dbfs": round(species_peak, 2),
            "non_species_peak_dbfs": round(non_species_peak, 2),
            "target_snr_db": round(target_snr, 2),
            "boost_applied_db": round(boost_needed, 2)
        })
        self.log_file.flush()

        return spectrogram_path

    def close(self):
        self.conn.close()
        self.log_file.close()
