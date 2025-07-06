import os
import random
import shutil
import sqlite3
import sys
from pydub import AudioSegment

from filter_existing_files import filter_existing_files
from generate_spectogram import generate_mel_spectrogram

AUG_FOLDER = "./recordings/augmentation_noise"
DB_PATH = "./db/chorusavery.db"
RECORDINGS_ROOT = "./recordings/training_data"
MODEL_ROOT = "./recordings/model"
NEGATIVE_LENGTH_MS = 2500  # 2.5 seconds
TARGET_MULTIPLIER = 3  # negatives = positives * multiplier
SNR_RANGE_DB = (-5, -15)  # softer overlay in dB
SPLIT_RATIOS = (0.7, 0.15, 0.15)  # train, val, test

def load_augmentation_clips(folder):
        return [
        os.path.abspath(os.path.join(folder, f))
        for f in os.listdir(folder)
        if f.endswith(".wav")
    ]

def overlay_with_augmentation(base_sound, overlay_pool):
    overlay_path = random.choice(overlay_pool)

    # Normalize slashes for consistent comparisons
    overlay_path_norm = os.path.normpath(overlay_path)
    recordings_root_norm = os.path.normpath(RECORDINGS_ROOT)

    # If overlay path already starts with RECORDINGS_ROOT, use it directly
    if overlay_path_norm.startswith(recordings_root_norm):
        resolved_path = overlay_path_norm
    # Otherwise, resolve relative to RECORDINGS_ROOT
    elif not os.path.isabs(overlay_path_norm):
        resolved_path = os.path.join(RECORDINGS_ROOT, overlay_path_norm)
    else:
        resolved_path = overlay_path_norm

    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Overlay file not found: {resolved_path}")

    overlay_clip = AudioSegment.from_file(resolved_path)

    # Choose random offset within overlay clip
    if len(overlay_clip) > NEGATIVE_LENGTH_MS:
        max_offset = len(overlay_clip) - NEGATIVE_LENGTH_MS
        overlay_clip = overlay_clip[random.randint(0, max_offset):][:NEGATIVE_LENGTH_MS]
    else:
        overlay_clip = overlay_clip[:NEGATIVE_LENGTH_MS]

    # Attenuate overlay to make it softer (SNR)
    attenuation = random.uniform(*SNR_RANGE_DB)
    overlay_clip = overlay_clip + attenuation

    return base_sound.overlay(overlay_clip)

def get_positive_count(model_path):
    """
    Counts all positive .wav files across train, validation, and test directories.
    Assumes positives are in subfolders named with non-zero species IDs.
    """
    total = 0
    for split in ["train", "validation", "test"]:
        split_dir = os.path.join(model_path, split)
        if not os.path.exists(split_dir):
            continue
        for sub in os.listdir(split_dir):
            if sub != "0" and os.path.isdir(os.path.join(split_dir, sub)):
                positive_folder = os.path.join(split_dir, sub)
                num_files = len([f for f in os.listdir(positive_folder) if f.endswith(".png")])
                total += num_files
    if total == 0:
        raise RuntimeError("❌ Could not find any positive files in train/val/test splits.")
    return total

def collect_clips_from_db(db_path, target_species_id, target_species_type_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1) Similar species
    cur.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
        JOIN Species s ON ca.species_id = s.id
        WHERE s.animal_type_id = ?
          AND s.id != ?
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              JOIN Species s2 ON ca2.species_id = s2.id
              WHERE ca2.clip_id = Clips.id AND s2.id = ?
          )
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca3
              JOIN Species s3 ON ca3.species_id = s3.id
              WHERE ca3.clip_id = Clips.id AND s3.animal_type_id = 13
          )
    """, (target_species_type_id, target_species_id, target_species_id))
    similar = [row[0] for row in cur.fetchall()]

    # 2) Other species
    cur.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
        JOIN Species s ON ca.species_id = s.id
        WHERE s.animal_type_id != ?
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              WHERE ca2.clip_id = Clips.id AND ca2.species_id = ?
          )
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca3
              JOIN Species s3 ON ca3.species_id = s3.id
              WHERE ca3.clip_id = Clips.id AND s3.animal_type_id = 13
          )
    """, (target_species_type_id, target_species_id))
    other = [row[0] for row in cur.fetchall()]

    # 3) Non-animal
    cur.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        WHERE EXISTS (SELECT 1 FROM ClipAnnotations ca WHERE ca.clip_id = Clips.id AND ca.non_animal_sound_id IS NOT NULL)
        AND NOT EXISTS (SELECT 1 FROM ClipAnnotations ca2 WHERE ca2.clip_id = Clips.id AND ca2.species_id IS NOT NULL)
    """)
    non_animal = [row[0] for row in cur.fetchall()]

    conn.close()
    return similar, other, non_animal

def synthesize_negative_clips(base_clips, augmentation_clips, needed_count, out_folder):
    os.makedirs(out_folder, exist_ok=True)
    for i in range(needed_count):
        base_path = random.choice(base_clips)
        base_sound = AudioSegment.from_file(os.path.join(RECORDINGS_ROOT, base_path))
        # Cut/loop/pad base to desired length
        if len(base_sound) >= NEGATIVE_LENGTH_MS:
            start = random.randint(0, len(base_sound) - NEGATIVE_LENGTH_MS)
            snippet = base_sound[start:start + NEGATIVE_LENGTH_MS]
        else:
            snippet = base_sound * (NEGATIVE_LENGTH_MS // len(base_sound) + 1)
            snippet = snippet[:NEGATIVE_LENGTH_MS]

        # Always overlay with augmentation
        negative = overlay_with_augmentation(snippet, augmentation_clips)

        # Save with unique name
        out_path = os.path.join(out_folder, f"neg_{i:05d}.wav")
        negative.export(out_path, format="wav")

import json

def distribute_balanced_negatives(similar, other, non_animal, total_needed, train_dir, val_dir, test_dir, augmentation_clips):
    splits = {
        "train": int(total_needed * SPLIT_RATIOS[0]),
        "val": int(total_needed * SPLIT_RATIOS[1]),
        "test": total_needed - int(total_needed * SPLIT_RATIOS[0]) - int(total_needed * SPLIT_RATIOS[1]),
    }

    used_clips_log = {k: [] for k in splits}

    for split_name, target_count in splits.items():
        out_dir = {"train": train_dir, "val": val_dir, "test": test_dir}[split_name]
        os.makedirs(out_dir, exist_ok=True)

        target_per_category = target_count // 4

        def sample_and_augment(category_list, category_name):
            # Extend category list with repeats if needed
            missing = max(0, target_per_category - len(category_list))
            if missing > 0:
                if category_list:
                    repeats = [random.choice(category_list) for _ in range(missing)]
                    extended_list = category_list + repeats
                else:
                    # fallback: sample from all categories + augmentations
                    fallback_pool = augmentation_clips + similar + other + non_animal
                    if not fallback_pool:
                        raise RuntimeError("🚨 No clips in fallback pool!")
                    extended_list = [random.choice(fallback_pool) for _ in range(target_per_category)]
            else:
                extended_list = category_list

            # Now we have enough items guaranteed
            for i in range(target_per_category):
                sample_path = extended_list[i]
                base_path = sample_path if os.path.isabs(sample_path) else os.path.join(RECORDINGS_ROOT, sample_path)
                base = AudioSegment.from_file(base_path)

                overlay_path = random.choice(augmentation_clips + similar + other + non_animal)
                overlay_clip_path = overlay_path if os.path.isabs(overlay_path) else os.path.join(RECORDINGS_ROOT, overlay_path)
                neg = overlay_with_augmentation(base, [overlay_clip_path])

                out_path = os.path.join(out_dir, f"{category_name}_{i:05d}.wav")
                neg.export(out_path, format="wav")

                spec_path = out_path.replace(".wav", ".png")
                generate_mel_spectrogram(neg, spec_path)
                os.remove(out_path)

                used_clips_log[split_name].append({
                    "output": out_path,
                    "base_clip": sample_path,
                    "overlay_clip": overlay_path,
                    "category": category_name
                })


        # Sample each category independently for this split
        sample_and_augment(similar, "similar")
        sample_and_augment(other, "other")
        sample_and_augment(non_animal, "non_animal")
        sample_and_augment(augmentation_clips, "augmentation")

    # Write log
    log_path = os.path.join(train_dir, "..", "used_negatives_log.json")
    with open(log_path, "w") as f:
        json.dump(used_clips_log, f, indent=2)
    print(f"📝 Balanced negatives log saved: {log_path}")

def main():
    print("📂 Available models:")
    models = [d for d in os.listdir(MODEL_ROOT) if os.path.isdir(os.path.join(MODEL_ROOT, d))]
    for idx, m in enumerate(models):
        print(f"{idx + 1}. {m}")
    choice = int(input("Select model by number: ")) - 1
    species_name = models[choice]
    model_path = os.path.join(MODEL_ROOT, species_name)
    print(f"✅ Using model: {species_name}")

    # Get species ID from non-0 folder
    for split in ['train']:
        train_dir = os.path.join(model_path, split)
        species_id = next((d for d in os.listdir(train_dir) if d != "0"), None)
        if species_id:
            break
    if not species_id:
        raise RuntimeError("❌ Could not determine species ID from model train/ directory.")

    print(f"🔎 Detected species ID: {species_id}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT animal_type_id FROM Species WHERE id = ?", (int(species_id),))
        row = cur.fetchone()
        if not row or row[0] is None:
            raise RuntimeError(f"❌ Could not find animal_type_id for species ID {species_id}")
        target_species_type_id = row[0]

    print(f"🔎 Retrieved species_type_id: {target_species_type_id}")

    positives = get_positive_count(model_path)
    negatives_needed = positives * TARGET_MULTIPLIER
    print(f"➡️ Need ~{negatives_needed} negatives (3x positives).")

    # Delete any existing 0 folders for train/val/test
    for split in ['train', 'validation', 'test']:
        zero_folder = os.path.join(model_path, split, '0')
        if os.path.exists(zero_folder):
            print(f"🗑️ Removing existing negatives folder: {zero_folder}")
            shutil.rmtree(zero_folder)

    similar, other, non_animal = collect_clips_from_db(DB_PATH, int(species_id), target_species_type_id)
    augmentation_clips = load_augmentation_clips(AUG_FOLDER)

    similar = filter_existing_files(similar, RECORDINGS_ROOT)
    other = filter_existing_files(other, RECORDINGS_ROOT)
    non_animal = filter_existing_files(non_animal, RECORDINGS_ROOT)

    # Generate negatives with overlays
    distribute_balanced_negatives(similar, other, non_animal,
                            negatives_needed,
                            os.path.join(model_path, 'train/0'),
                            os.path.join(model_path, 'validation/0'),
                            os.path.join(model_path, 'test/0'),
                            augmentation_clips)

    print("✅ Negative clips generated and distributed!")

if __name__ == "__main__":
    main()
