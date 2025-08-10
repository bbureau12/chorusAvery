import os
import random
import shutil
import sqlite3
import sys
import re
from pydub import AudioSegment

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.augmentation_helpers import pad_audio, overlay_noise, polarize_volume
from utils.generate_spectogram import generate_mel_spectrogram

STARTER_CLIP_GOAL = 1250
MAX_CLIPS_PER_CLASS = 3000

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def generate_extra_starters(selected_clips, noises, clip_dir="./recordings/training_data"):
    extra_clips = []
    temp_paths = []
    while len(selected_clips) + len(extra_clips) < STARTER_CLIP_GOAL:
        original = random.choice(selected_clips)
        full_path = os.path.join(clip_dir, original)
        base = os.path.splitext(os.path.basename(original))[0] + f"_extra{len(extra_clips)}"
        clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
        noise = random.choice(noises)
        aug_clip = overlay_noise(clip, noise, clip.dBFS)
        aug_path = os.path.join(clip_dir, base + ".wav")
        aug_clip.export(aug_path, format="wav")
        extra_clips.append(os.path.relpath(aug_path, clip_dir))
        temp_paths.append(aug_path)
    return extra_clips, temp_paths

def export_augmented_versions(clip, base_name, out_dir, noises, overlay_pool=None, overlay_prob=0.25):
    outputs = []

    def save(clip_obj, suffix):
        base_fname = f"{base_name}{suffix}"
        bin_folder = base_fname[0].lower()
        out_bin_dir = os.path.join(out_dir, bin_folder)
        os.makedirs(out_bin_dir, exist_ok=True)

        wav_path = os.path.join(out_bin_dir, base_fname + ".wav")
        clip_obj.export(wav_path, format="wav")
        spectro_path = wav_path.replace('.wav', '.png')
        generate_mel_spectrogram(clip_obj, spectro_path)
        os.remove(wav_path)
        outputs.append(spectro_path)

    save(clip, "")
    padded = pad_audio(clip)
    save(padded, "_pad")
    boosted = polarize_volume(clip, -22.0)
    if boosted:
        save(boosted, "_boosted")

    for i in range(3):
        aug = clip
        if overlay_pool and random.random() < overlay_prob:
            aug = aug.overlay(random.choice(overlay_pool).apply_gain(-8))
        noise = random.choice(noises)
        aug = overlay_noise(aug, noise, aug.dBFS)
        save(aug, f"_aug{i}")

    return outputs

def split_data(files, train_ratio=0.7, val_ratio=0.15):
    if not files:
        return [], [], []

    random.shuffle(files)
    total = len(files)
    train = files[:int(total * train_ratio)]
    val = files[int(total * train_ratio):int(total * (train_ratio + val_ratio))]
    test = files[int(total * (train_ratio + val_ratio)):]
    return train, val, test

def search_categories(cursor):
    cursor.execute("SELECT id, name FROM SoundCategories")
    return cursor.fetchall()

def search_sounds_by_category(cursor, category_id):
    cursor.execute("SELECT id, name FROM NonAnimalSounds WHERE category_id = ?", (category_id,))
    return cursor.fetchall()

def get_clip_paths(cursor, sound_ids, location_ids=None):
    placeholders = ','.join(['?'] * len(sound_ids))
    base_query = f"""
        SELECT Clips.clip_path, COUNT(DISTINCT ca2.species_id) as species_count, COUNT(DISTINCT ca2.non_animal_sound_id) as nas_count
        FROM Clips
        JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
        JOIN SourceFiles ON Clips.source_id = SourceFiles.id
        WHERE ca2.non_animal_sound_id IN ({placeholders})
    """
    params = list(sound_ids)
    if location_ids:
        base_query += f" AND SourceFiles.LocationID IN ({','.join(['?'] * len(location_ids))})"
        params += location_ids
    base_query += " GROUP BY Clips.id"
    cursor.execute(base_query, params)
    return cursor.fetchall()

def main():
    db_path = "./db/chorusAvery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Include clean animal sounds as class 0? (y/n): ", end="")
    include_animals = input().strip().lower() == 'y'

    categories = search_categories(cursor)
    print("\n📦 Available categories:")
    for i, (_, name) in enumerate(categories):
        print(f"{i+1}. {name}")

    selected = input("Select category numbers (comma-separated): ").strip().split(',')
    selected_ids = [categories[int(i.strip()) - 1][0] for i in selected]
    selected_names = [categories[int(i.strip()) - 1][1] for i in selected]

    slug = input("Slug name for output directory: ").strip()
    slug = slug or "multi_class_output"
    base_dir = f"./recordings/model/{slug}"

    loc_input = input("📍 Location IDs (comma-separated or *): ").strip()
    location_ids = None if loc_input == "*" else list(map(int, loc_input.split(',')))

    noises = [AudioSegment.from_file(os.path.join("./recordings/augmentation_noise", f))
              for f in os.listdir("./recordings/augmentation_noise") if f.endswith('.wav')]

    class_index = 0
    if include_animals:
        print("\n🔧 Processing animal sounds as class 0")
        category_slug = "animal_sounds"

        cursor.execute("""
            SELECT Clips.clip_path
            FROM Clips
            JOIN ClipAnnotations ON ClipAnnotations.clip_id = Clips.id
            WHERE ClipAnnotations.species_id IS NOT NULL
            AND Clips.id NOT IN (
                SELECT clip_id FROM ClipAnnotations WHERE non_animal_sound_id IS NOT NULL
            )
            GROUP BY Clips.id
            HAVING COUNT(DISTINCT ClipAnnotations.species_id) = 1
        """)
        animal_clips = [r[0] for r in cursor.fetchall()]
        selected_clips = random.sample(animal_clips, min(len(animal_clips), MAX_CLIPS_PER_CLASS))

        overlay_pool = []
        for file in selected_clips:
            full_path = os.path.join("./recordings/training_data", file)
            clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
            overlay_pool.append(clip)

        while len(overlay_pool) < len(selected_clips):
            overlay_pool.append(random.choice(overlay_pool).apply_gain(-6))

        out_dir = os.path.join(base_dir, category_slug, 'full')
        all_outputs = []
        for file in selected_clips:
            full_path = os.path.join("./recordings/training_data", file)
            clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
            base = os.path.splitext(os.path.basename(file))[0]
            all_outputs += export_augmented_versions(clip, base, out_dir, noises, overlay_pool)

        train, val, test = split_data(all_outputs)
        for group, folder in zip([train, val, test], ['train', 'validation', 'test']):
            for f in group:
                tgt = os.path.join(base_dir, folder, category_slug, os.path.basename(f))
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.move(f, tgt)

        shutil.rmtree(out_dir)
        print(f"🧾 Category '{category_slug}': {len(all_outputs)} spectrograms generated from {len(selected_clips)} starter clips")
        class_index += 1

    for idx, (category_id, category_name) in enumerate(zip(selected_ids, selected_names)):
        print(f"\n🔧 Processing {category_name} as class {class_index}")
        category_slug = slugify(category_name)

        cursor.execute("SELECT id FROM NonAnimalSounds WHERE category_id = ?", (category_id,))
        sound_ids = [r[0] for r in cursor.fetchall()]
        if not sound_ids:
            print(f"⚠️ No sounds found for category {category_name}. Skipping.")
            continue

        clips = get_clip_paths(cursor, sound_ids, location_ids)
        solo = [p for p, s, n in clips if s == 0 and n == 1]
        mixed = [p for p, s, n in clips if s > 0 or n > 1]
        selected_mixed = random.sample(mixed, min(len(mixed), len(solo)//4))
        positives = solo + selected_mixed

        if not positives:
            print(f"⚠️ No clips found for class {class_index}. Skipping.")
            continue

        selected_clips = random.sample(positives, min(len(positives), MAX_CLIPS_PER_CLASS))

        # === Ensure Minimum Starter Clips ===
        temp_paths = []
        if len(selected_clips) < STARTER_CLIP_GOAL:
            print(f"🔄 Only {len(selected_clips)} clips found. Augmenting to {STARTER_CLIP_GOAL}.")
            extras, temp_paths = generate_extra_starters(selected_clips, noises)
            selected_clips += extras

        overlay_pool = []
        for file in selected_clips:
            full_path = os.path.join("./recordings/training_data", file)
            clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
            overlay_pool.append(clip)

        while len(overlay_pool) < len(selected_clips):
            overlay_pool.append(random.choice(overlay_pool).apply_gain(-6))

        out_dir = os.path.join(base_dir, category_slug, 'full')
        all_outputs = []
        for file in selected_clips:
            full_path = os.path.join("./recordings/training_data", file)
            clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
            base = os.path.splitext(os.path.basename(file))[0]
            all_outputs += export_augmented_versions(clip, base, out_dir, noises, overlay_pool)

        train, val, test = split_data(all_outputs)
        for group, folder in zip([train, val, test], ['train', 'validation', 'test']):
            for f in group:
                tgt = os.path.join(base_dir, folder, category_slug, os.path.basename(f))
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.move(f, tgt)

        shutil.rmtree(out_dir)
        for temp in temp_paths:
            try:
                os.remove(temp)
            except Exception as e:
                print(f"⚠️ Failed to delete temp file {temp}: {e}")
        print(f"🧾 Category '{category_name}' ({category_slug}): {len(all_outputs)} spectrograms generated from {len(selected_clips)} starter clips")
        class_index += 1

if __name__ == "__main__":
    main()
