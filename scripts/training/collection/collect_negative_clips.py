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
                 target_multiplier=3, snr_range_db=(-5, -15), negative_length_ms=2500,
                 # NEW:
                 export_mode="spectrograms",            # "spectrograms" | "wavs" | "none"
                 export_root=None,                      # e.g. "./data/slices_hf/other"
                 return_manifest=False):
        ...
        self.export_mode = export_mode
        self.export_root = export_root
        self.return_manifest = return_manifest
        ...

    ...
    def run(self):
        print(f"🚀 Generating negatives for model: {self.model_name}")
        species_id, species_type_id = self.get_species_id_and_type()
        positives = self.get_positive_count()
        negatives_needed = positives * self.target_multiplier
        print(f"➡️ Need ~{negatives_needed} negatives (multiplier {self.target_multiplier})")

        # Keep old cleanup only when writing to model folders + spectrograms
        if self.export_mode == "spectrograms" and self.export_root is None:
            for split in ['train', 'validation', 'test']:
                zero_folder = os.path.join(self.model_path, split, '0')
                if os.path.exists(zero_folder):
                    print(f"🗑️ Removing existing negatives folder: {zero_folder}")
                    shutil.rmtree(zero_folder)

        similar, other, non_animal = self.collect_negatives_from_db(int(species_id), species_type_id)

        manifest = self.distribute_negatives(
            similar, other, non_animal, negatives_needed,
            # when export_root is provided we write to <export_root>/<split>/
            os.path.join(self.model_path, 'train/0') if self.export_root is None else os.path.join(self.export_root, 'train'),
            os.path.join(self.model_path, 'validation/0') if self.export_root is None else os.path.join(self.export_root, 'val'),
            os.path.join(self.model_path, 'test/0') if self.export_root is None else os.path.join(self.export_root, 'test'),
        )

        if self.return_manifest:
            return manifest

    def distribute_negatives(self, similar, other, non_animal, total_needed, train_dir, val_dir, test_dir):
        splits = {
            "train": int(total_needed * 0.7),
            "val": int(total_needed * 0.15),
            "test": total_needed - int(total_needed * 0.7) - int(total_needed * 0.15),
        }
        used_log = {k: [] for k in splits}
        # NEW: track written files so we can build HF manifest
        written = {k: [] for k in splits}

        categories = [("similar", similar), ("other", other), ("non_animal", non_animal), ("augmentation", self.augmentation_clips)]

        for split_name, target_count in splits.items():
            out_dir = {"train": train_dir, "val": val_dir, "test": test_dir}[split_name]
            os.makedirs(out_dir, exist_ok=True)
            target_per_category = max(1, target_count // 4)

            for cat_name, cat_list in categories:
                if not cat_list:
                    continue
                for i in range(target_per_category):
                    base_path = random.choice(cat_list)
                    base = AudioSegment.from_file(base_path if os.path.isabs(base_path) else os.path.join(self.recordings_root, base_path))
                    overlay_path = random.choice(self.augmentation_clips + similar + other + non_animal)
                    overlay = AudioSegment.from_file(overlay_path if os.path.isabs(overlay_path) else os.path.join(self.recordings_root, overlay_path))
                    attenuation = random.uniform(*self.snr_range_db)
                    overlay = overlay + attenuation

                    # length normalize
                    if len(base) > self.negative_length_ms:
                        max_offset = len(base) - self.negative_length_ms
                        base = base[random.randint(0, max_offset):][:self.negative_length_ms]
                    else:
                        base = (base * (self.negative_length_ms // len(base) + 1))[:self.negative_length_ms]

                    negative = base.overlay(overlay)
                    stem = f"{cat_name}_{i:05d}"

                    if self.export_mode == "spectrograms":
                        out_wav = os.path.join(out_dir, f"{stem}.wav")
                        negative.export(out_wav, format="wav")
                        spec_path = out_wav.replace(".wav", ".png")
                        generate_mel_spectrogram(negative, spec_path)
                        os.remove(out_wav)
                        written[split_name].append(spec_path)
                    elif self.export_mode == "wavs":
                        out_wav = os.path.join(out_dir, f"{stem}.wav")
                        negative.export(out_wav, format="wav")
                        written[split_name].append(out_wav)
                    elif self.export_mode == "none":
                        # nothing written; just record selection metadata
                        written[split_name].append(f"{cat_name}:{base_path}|{overlay_path}")
                    else:
                        raise ValueError(f"Unknown export_mode: {self.export_mode}")

                    used_log[split_name].append({"output": written[split_name][-1], "base_clip": base_path, "overlay_clip": overlay_path, "category": cat_name})

        # keep old log behavior (write near train dir) when writing files
        if self.export_mode in ("spectrograms", "wavs"):
            log_path = os.path.join(train_dir, "..", "used_negatives_log.json")
            with open(log_path, "w") as f:
                json.dump(used_log, f, indent=2)
            print(f"📝 Balanced negatives log saved: {log_path}")

        return written
