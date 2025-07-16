import os
import random
import shutil
import sqlite3
import json
from pydub import AudioSegment
from utils.filter_existing_files import filter_existing_files
from utils.generate_spectogram import generate_mel_spectrogram

class NegativeClipGenerator:
    def __init__(self, model_name, 
                 db_path="./db/chorusavery.db", 
                 recordings_root="./recordings/training_data",
                 model_root="./recordings/model", 
                 aug_folder="./recordings/augmentation_noise",
                 target_multiplier=3, snr_range_db=(-5, -15), negative_length_ms=2500):
        self.model_name = model_name
        self.db_path = db_path
        self.recordings_root = recordings_root
        self.model_root = model_root
        self.aug_folder = aug_folder
        self.target_multiplier = target_multiplier
        self.snr_range_db = snr_range_db
        self.negative_length_ms = negative_length_ms
        self.model_path = os.path.join(self.model_root, self.model_name)
        self.augmentation_clips = self.load_augmentation_clips()

    def load_augmentation_clips(self):
        return [
            os.path.abspath(os.path.join(self.aug_folder, f))
            for f in os.listdir(self.aug_folder)
            if f.endswith(".wav")
        ]

    def get_species_id_and_type(self):
        train_dir = os.path.join(self.model_path, "train")
        species_id = next((d for d in os.listdir(train_dir) if d != "0"), None)
        if not species_id:
            raise RuntimeError("❌ Could not determine species ID from model train/ directory.")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT animal_type_id FROM Species WHERE id = ?", (int(species_id),))
            row = cur.fetchone()
            if not row or row[0] is None:
                raise RuntimeError(f"❌ Could not find animal_type_id for species ID {species_id}")
            species_type_id = row[0]
        print(f"🔎 Species ID: {species_id}, species_type_id: {species_type_id}")
        return species_id, species_type_id

    def get_positive_count(self):
        total = 0
        for split in ["train", "validation", "test"]:
            split_dir = os.path.join(self.model_path, split)
            if not os.path.exists(split_dir):
                continue
            for sub in os.listdir(split_dir):
                if sub != "0" and os.path.isdir(os.path.join(split_dir, sub)):
                    positive_folder = os.path.join(split_dir, sub)
                    num_files = len([f for f in os.listdir(positive_folder) if f.endswith(".png")])
                    total += num_files
        if total == 0:
            raise RuntimeError("❌ Could not find any positive files in train/val/test splits.")
        print(f"✅ Found {total} positives.")
        return total

    def collect_negatives_from_db(self, species_id, species_type_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # 1) Similar species
        cur.execute("""SELECT DISTINCT Clips.clip_path FROM Clips
            JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
            JOIN Species s ON ca.species_id = s.id
            WHERE s.animal_type_id = ? AND s.id != ?""", (species_type_id, species_id))
        similar = [row[0] for row in cur.fetchall()]
        # 2) Other species
        cur.execute("""SELECT DISTINCT Clips.clip_path FROM Clips
            JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
            JOIN Species s ON ca.species_id = s.id
            WHERE s.animal_type_id != ? AND NOT EXISTS (
                SELECT 1 FROM ClipAnnotations ca2 WHERE ca2.clip_id = Clips.id AND ca2.species_id = ?)""",
            (species_type_id, species_id))
        other = [row[0] for row in cur.fetchall()]
        # 3) Non-animal
        cur.execute("""SELECT DISTINCT Clips.clip_path FROM Clips
            WHERE EXISTS (SELECT 1 FROM ClipAnnotations ca WHERE ca.clip_id = Clips.id AND ca.non_animal_sound_id IS NOT NULL)
            AND NOT EXISTS (SELECT 1 FROM ClipAnnotations ca2 WHERE ca2.clip_id = Clips.id AND ca2.species_id IS NOT NULL)""")
        non_animal = [row[0] for row in cur.fetchall()]
        conn.close()
        return (filter_existing_files(similar, self.recordings_root),
                filter_existing_files(other, self.recordings_root),
                filter_existing_files(non_animal, self.recordings_root))

    def run(self):
        print(f"🚀 Generating negatives for model: {self.model_name}")
        species_id, species_type_id = self.get_species_id_and_type()
        positives = self.get_positive_count()
        negatives_needed = positives * self.target_multiplier
        print(f"➡️ Need ~{negatives_needed} negatives (multiplier {self.target_multiplier})")

        # Remove existing negatives
        for split in ['train', 'validation', 'test']:
            zero_folder = os.path.join(self.model_path, split, '0')
            if os.path.exists(zero_folder):
                print(f"🗑️ Removing existing negatives folder: {zero_folder}")
                shutil.rmtree(zero_folder)

        similar, other, non_animal = self.collect_negatives_from_db(int(species_id), species_type_id)

        self.distribute_negatives(similar, other, non_animal, negatives_needed,
                                  os.path.join(self.model_path, 'train/0'),
                                  os.path.join(self.model_path, 'validation/0'),
                                  os.path.join(self.model_path, 'test/0'))

    def distribute_negatives(self, similar, other, non_animal, total_needed, train_dir, val_dir, test_dir):
        splits = {
            "train": int(total_needed * 0.7),
            "val": int(total_needed * 0.15),
            "test": total_needed - int(total_needed * 0.7) - int(total_needed * 0.15),
        }
        used_log = {k: [] for k in splits}
        categories = [("similar", similar), ("other", other), ("non_animal", non_animal), ("augmentation", self.augmentation_clips)]
        for split_name, target_count in splits.items():
            out_dir = {"train": train_dir, "val": val_dir, "test": test_dir}[split_name]
            os.makedirs(out_dir, exist_ok=True)
            target_per_category = target_count // 4
            for cat_name, cat_list in categories:
                for i in range(target_per_category):
                    base_path = random.choice(cat_list)
                    base = AudioSegment.from_file(base_path if os.path.isabs(base_path) else os.path.join(self.recordings_root, base_path))
                    overlay_path = random.choice(self.augmentation_clips + similar + other + non_animal)
                    overlay = AudioSegment.from_file(overlay_path if os.path.isabs(overlay_path) else os.path.join(self.recordings_root, overlay_path))
                    attenuation = random.uniform(*self.snr_range_db)
                    overlay = overlay + attenuation
                    if len(base) > self.negative_length_ms:
                        max_offset = len(base) - self.negative_length_ms
                        base = base[random.randint(0, max_offset):][:self.negative_length_ms]
                    else:
                        base = (base * (self.negative_length_ms // len(base) + 1))[:self.negative_length_ms]
                    negative = base.overlay(overlay)
                    out_wav = os.path.join(out_dir, f"{cat_name}_{i:05d}.wav")
                    negative.export(out_wav, format="wav")
                    spec_path = out_wav.replace(".wav", ".png")
                    generate_mel_spectrogram(negative, spec_path)
                    os.remove(out_wav)
                    used_log[split_name].append({"output": spec_path, "base_clip": base_path, "overlay_clip": overlay_path, "category": cat_name})
        log_path = os.path.join(train_dir, "..", "used_negatives_log.json")
        with open(log_path, "w") as f:
            json.dump(used_log, f, indent=2)
        print(f"📝 Balanced negatives log saved: {log_path}")
