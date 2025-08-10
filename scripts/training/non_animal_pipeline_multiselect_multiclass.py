import os
import random
import shutil
import sqlite3
import sys
import re
import csv
from pydub import AudioSegment
from itertools import combinations

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.augmentation_helpers import pad_audio, overlay_noise, polarize_volume
from utils.generate_spectogram import generate_mel_spectrogram

STARTER_CLIP_GOAL = 1000
MAX_CLIPS_PER_CLASS = 3000
LABEL_CSV_HEADERS = []

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def search_all_non_animal_sounds(cursor):
    cursor.execute("""
        SELECT NAS.id, NAS.name, SC.name
        FROM NonAnimalSounds NAS
        JOIN SoundCategories SC ON NAS.category_id = SC.id
        ORDER BY SC.name, NAS.name
    """)
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

def prompt_combinations(selected_names):
    print("\n🔗 Define combinations of classes to overlay (multi-label):")
    combos = []
    while True:
        print("\nEnter sound numbers to combine (comma-separated), or '#' to finish:")
        for i, name in enumerate(selected_names):
            print(f" {i+1}. {name}")
        choice = input(" > ").strip()
        if choice == '#':
            break
        try:
            indices = [int(i.strip()) - 1 for i in choice.split(',') if i.strip().isdigit()]
            combo = tuple(sorted(set(indices)))
            if len(combo) > 1 and combo not in combos:
                combos.append(combo)
        except Exception as e:
            print(f"Invalid input: {e}")
    return combos

def generate_augmented_versions(audio, label_slugs, index, out_dir, class_slugs):
    labels = []
    for aug_idx in range(3):
        aug = audio
        if aug_idx == 1:
            aug = pad_audio(audio)
        elif aug_idx == 2:
            boosted = polarize_volume(audio, -22.0)
            if boosted:
                aug = boosted
        fname = f"{'_'.join(label_slugs)}_{index}_aug{aug_idx}.png"
        wav_path = os.path.join(out_dir, fname.replace('.png', '.wav'))
        aug.export(wav_path, format="wav")
        generate_mel_spectrogram(aug, os.path.join(out_dir, fname))
        os.remove(wav_path)
        label_row = {'filename': fname, **{slug: int(slug in label_slugs) for slug in class_slugs}}
        labels.append(label_row)
    return labels

def main():
    db_path = "./db/chorusAvery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sounds = search_all_non_animal_sounds(cursor)
    print("\n🎵 Available Non-Animal Sounds:")
    for i, (_, sound_name, category_name) in enumerate(sounds):
        print(f" {i+1}. {sound_name} ({category_name})")

    selected = input("\nSelect sound numbers (comma-separated): ").strip().split(',')
    selected_ids = [sounds[int(i.strip()) - 1][0] for i in selected]
    selected_names = [sounds[int(i.strip()) - 1][1] for i in selected]

    label_map = {slugify(name): name for name in selected_names}
    class_slugs = list(label_map.keys())

    slug = input("Slug name for output directory: ").strip() or "multi_label"
    base_dir = os.path.join("./recordings/model", slug)
    os.makedirs(os.path.join(base_dir, 'train'), exist_ok=True)

    loc_input = input("\n📍 Location IDs (comma-separated or *): ").strip()
    location_ids = None if loc_input == "*" else list(map(int, loc_input.split(',')))

    print("\n🎛️  Preparing base clips for each class...")
    class_clips = {}
    for sid, name in zip(selected_ids, selected_names):
        clips = get_clip_paths(cursor, [sid], location_ids)
        solo = [p for p, s, n in clips if s == 0 and n == 1]
        if not solo:
            print(f"⚠️ No clips found for {name}, skipping.")
            continue
        selected = random.sample(solo, min(len(solo), MAX_CLIPS_PER_CLASS))
        while len(selected) < STARTER_CLIP_GOAL:
            selected += random.choices(selected)
        class_clips[slugify(name)] = selected[:STARTER_CLIP_GOAL]

    all_labels = []
    train_dir = os.path.join(base_dir, 'train')
    noises = [AudioSegment.from_file(os.path.join("./recordings/augmentation_noise", f))
              for f in os.listdir("./recordings/augmentation_noise") if f.endswith('.wav')]

    print("\n🎨 Generating individual class examples with augmentations...")
    for cls, files in class_clips.items():
        for idx, file in enumerate(files[:100]):
            audio = AudioSegment.from_file(os.path.join("./recordings/training_data", file)).set_channels(1).set_frame_rate(16000)
            all_labels += generate_augmented_versions(audio, [cls], idx, train_dir, class_slugs)

    combos = prompt_combinations(selected_names)

    print("\n🎨 Generating overlaid clips and labels...")
    for combo in combos:
        combo_slugs = [slugify(selected_names[i]) for i in combo]
        base_class = combo_slugs[0]
        overlay_classes = combo_slugs[1:]
        base_pool = class_clips.get(base_class, [])
        overlay_pools = [class_clips.get(cls, []) for cls in overlay_classes]

        for idx in range(min(len(base_pool), 100)):
            base_file = base_pool[idx % len(base_pool)]
            base_audio = AudioSegment.from_file(os.path.join("./recordings/training_data", base_file)).set_channels(1).set_frame_rate(16000)
            overlayed = base_audio
            for cls, pool in zip(overlay_classes, overlay_pools):
                if pool:
                    ov = AudioSegment.from_file(os.path.join("./recordings/training_data", random.choice(pool))).set_channels(1).set_frame_rate(16000)
                    overlayed = overlayed.overlay(ov.apply_gain(-6))
            all_labels += generate_augmented_versions(overlayed, combo_slugs, idx, train_dir, class_slugs)

    print("\n📝 Writing labels.csv...")
    label_csv_path = os.path.join(train_dir, 'labels.csv')
    with open(label_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['filename'] + class_slugs)
        writer.writeheader()
        writer.writerows(all_labels)

    print(f"✅ Done. Spectrograms and labels.csv saved to: {train_dir}")

if __name__ == "__main__":
    main()
