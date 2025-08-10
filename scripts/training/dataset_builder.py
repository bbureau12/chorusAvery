from datetime import datetime
import os
import sys
import sqlite3
import json
import random
import shutil
import re
from pydub import AudioSegment

# === Setup project path for utility access ===
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.augmentation_helpers import split_data, pad_audio, overlay_noise, polarize_volume
from utils.generate_spectogram import generate_mel_spectrogram
from scripts.training.collection.collect_negative_clips import NegativeClipGenerator

# === Constants ===
AUDIO_ROOT = "./recordings/training_data"
AUG_NOISE_DIR = "./recordings/augmentation_noise"
MODEL_ROOT = "./recordings/model"
DB_PATH = "./db/chorusAvery.db"
AUDIO_DURATION_MS = 2500

# === Utility Functions ===
def slugify(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


# === Augmentation & Export ===
def generate_augmented_set(clip_path, base_name, out_dir, noises, overlay_pool=None, overlay_prob=0.25):
    outputs = []
    clip = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)
    clip = clip[:AUDIO_DURATION_MS]  # Enforce 2.5s

    def save_version(clip_obj, suffix):
        filename = f"{base_name}{suffix}.wav"
        output_path = os.path.join(out_dir, filename)
        os.makedirs(out_dir, exist_ok=True)
        clip_obj.export(output_path, format="wav")
        png_path = output_path.replace(".wav", ".png")
        generate_mel_spectrogram(clip_obj, png_path)
        os.remove(output_path)
        outputs.append(png_path)

    save_version(clip, "")
    padded = pad_audio(clip)
    save_version(padded, "_pad")
    boosted = polarize_volume(clip, -22.0)
    if boosted:
        save_version(boosted, "_boosted")

    for i in range(3):
        aug = clip
        if overlay_pool and random.random() < overlay_prob:
            aug = aug.overlay(random.choice(overlay_pool).apply_gain(-8))
        noise = random.choice(noises)
        aug = overlay_noise(aug, noise, aug.dBFS)
        save_version(aug, f"_aug{i}")

    return outputs

# === Main CLI Pipeline ===
def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # MODE SELECTION
    mode = input("\U0001F527 Dataset type (binary/multilabel): ").strip().lower()
    label_type = input("\U0001F4DA Label source (species/non-species): ").strip().lower()
    include_clean = input("\u2795 Include clean animal class 0? (y/n): ").strip().lower() == 'y'
    min_clips = int(input("\U0001F9EE Minimum clips per class (default 1200): ") or 1200)
    max_clips = int(input("\U0001F9E2 Max clips per class (default 10000): ") or 10000)
    slug = input("\U0001F4C1 Output slug (e.g. frogs_aug2025): ").strip() or f"run_{datetime.now().strftime('%Y%m%d')}"

    base_path = os.path.join(MODEL_ROOT, slug)
    for sub in ['train', 'validation', 'test']:
        os.makedirs(os.path.join(base_path, sub), exist_ok=True)

    noises = [AudioSegment.from_file(os.path.join(AUG_NOISE_DIR, f))
              for f in os.listdir(AUG_NOISE_DIR) if f.endswith('.wav')]

    class_names = {}
    class_clip_counts = {}

    if label_type == "species":
        cursor.execute("SELECT id, name FROM Species ORDER BY name")
    else:
        cursor.execute("SELECT id, name FROM NonAnimalSounds ORDER BY name")
    all_classes = cursor.fetchall()

    print("\n\U0001F50D Available classes:")
    for i, (_, name) in enumerate(all_classes):
        print(f"{i+1}. {name}")
    selected = input("Select class numbers (comma-separated): ").strip().split(',')
    selected_ids = [all_classes[int(i.strip()) - 1][0] for i in selected]
    selected_names = [all_classes[int(i.strip()) - 1][1] for i in selected]

    next_index = 0
    if include_clean:
        if mode == "binary":
            print("🧪 Generating negative class using NegativeClipGenerator...")
            neg_gen = NegativeClipGenerator(model_name=slug)
            neg_gen.run()
            class_names["0"] = "generated_negatives"
            class_clip_counts["0"] = "generated"  # You may optionally count these if needed
            next_index += 1
        else:
            print("🔨 Collecting clean class 0...")
            cursor.execute("""
                SELECT Clips.clip_path FROM Clips
                JOIN ClipAnnotations ON ClipAnnotations.clip_id = Clips.id
                WHERE ClipAnnotations.species_id IS NOT NULL
                AND ClipAnnotations.non_animal_sound_id IS NULL
                GROUP BY Clips.id
                HAVING COUNT(DISTINCT ClipAnnotations.species_id) = 1
            """)
            clean_clips = [row[0] for row in cursor.fetchall()]
            selected = random.sample(clean_clips, min(len(clean_clips), max_clips))
            label = "0"
            name = "clean_negative"
            class_names[label] = name
            overlay_pool = [AudioSegment.from_file(os.path.join(AUDIO_ROOT, path)).set_channels(1).set_frame_rate(16000)
                            for path in selected]
            while len(overlay_pool) < min_clips:
                overlay_pool.append(random.choice(overlay_pool).apply_gain(-6))

            out_dir = os.path.join(base_path, "temp", label)
            augmented = []
            for path in selected:
                full = os.path.join(AUDIO_ROOT, path)
                base = os.path.splitext(os.path.basename(path))[0]
                augmented += generate_augmented_set(full, base, out_dir, noises, overlay_pool)
            train, val, test = split_data(augmented)
            for grp, tag in zip([train, val, test], ['train', 'validation', 'test']):
                for f in grp:
                    tgt = os.path.join(base_path, tag, label, os.path.basename(f))
                    shutil.move(f, tgt)
            shutil.rmtree(out_dir)
            class_clip_counts[label] = len(augmented)
            next_index += 1

    for i, (cid, name) in enumerate(zip(selected_ids, selected_names)):
        label = str(cid if mode == "multilabel" else next_index)
        class_names[label] = name
        print(f"\n\U0001F3A7 Processing '{name}' as class {label}...")

        if label_type == "species":
            cursor.execute("""
                SELECT Clips.clip_path, COUNT(DISTINCT ca2.species_id) as species_count
                FROM Clips
                JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
                WHERE ca2.species_id = ?
                GROUP BY Clips.id
            """, (cid,))
        else:
            cursor.execute("""
                SELECT Clips.clip_path, COUNT(DISTINCT ca2.non_animal_sound_id) as nas_count
                FROM Clips
                JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
                WHERE ca2.non_animal_sound_id = ?
                GROUP BY Clips.id
            """, (cid,))

        all_results = cursor.fetchall()
        solo = [path for path, count in all_results if count == 1]
        mixed = [path for path, count in all_results if count > 1]
        n_mixed = min(len(mixed), len(solo) // 4)
        selected = solo + random.sample(mixed, n_mixed)
        selected = random.sample(selected, min(len(selected), max_clips))

        overlay_pool = [AudioSegment.from_file(os.path.join(AUDIO_ROOT, path)).set_channels(1).set_frame_rate(16000)
                        for path in selected]
        while len(overlay_pool) < min_clips:
            overlay_pool.append(random.choice(overlay_pool).apply_gain(-6))

        out_dir = os.path.join(base_path, "temp", label)
        augmented = []
        for path in selected:
            full = os.path.join(AUDIO_ROOT, path)
            base = os.path.splitext(os.path.basename(path))[0]
            augmented += generate_augmented_set(full, base, out_dir, noises, overlay_pool)

        train, val, test = split_data(augmented)
        for grp, tag in zip([train, val, test], ['train', 'validation', 'test']):
            for f in grp:
                tgt = os.path.join(base_path, tag, label, os.path.basename(f))
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.move(f, tgt)
        shutil.rmtree(out_dir)
        class_clip_counts[label] = len(augmented)
        next_index += 1

    with open(os.path.join(base_path, "class_names.json"), "w") as f:
        json.dump(class_names, f, indent=2)
    with open(os.path.join(base_path, "clip_counts.json"), "w") as f:
        json.dump(class_clip_counts, f, indent=2)

    print(f"\n\u2705 Dataset built at: {base_path}")
    print(f"\U0001F4C1 Classes: {len(class_names)} | Total clips: {sum(class_clip_counts.values())}")

    print(f"\n\u2705 Dataset built at: {base_path}")
    print(f"\U0001F4C1 Classes: {len(class_names)} | Total clips: {sum(class_clip_counts.values())}")

if __name__ == "__main__":
    main()