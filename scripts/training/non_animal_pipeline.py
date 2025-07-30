import os
import random
import shutil
import sqlite3
import sys
import argparse
from pydub import AudioSegment

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.augmentation_helpers import pad_audio, overlay_noise, polarize_volume
from utils.generate_spectogram import generate_mel_spectrogram

# === Helpers ===
def search_categories(cursor):
    cursor.execute("SELECT id, name FROM NonAnimalSoundCategories")
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

def build_overlay_pool(positives, comp_paths, min_paths, spc_paths, verbose=False):
    overlay_pool = []
    num_pos = len(positives)
    comp_needed = int(num_pos * 0.4)
    min_needed = int(num_pos * 0.1)
    spc_needed = int(num_pos * 0.5)

    selected = (
        random.sample(comp_paths, min(comp_needed, len(comp_paths))) +
        random.sample(min_paths, min(min_needed, len(min_paths))) +
        random.sample(spc_paths, min(spc_needed, len(spc_paths)))
    )
    for path in selected:
        full = os.path.join("./recordings/training_data", path)
        clip = AudioSegment.from_file(full).set_channels(1).set_frame_rate(16000)
        overlay_pool.append(clip)

    if verbose:
        print(f"🔁 Overlay pool size before shuffle: {len(overlay_pool)}")

    while len(overlay_pool) < num_pos:
        overlay_pool.append(random.choice(overlay_pool).apply_gain(-6))

    return overlay_pool

def export_augmented_versions(clip, base_name, out_dir, noises, overlay_pool=None, overlay_prob=0.25):
    outputs = []

    def save(clip_obj, suffix):
        base_fname = f"{base_name}{suffix}"
        bin_folder = base_fname[0].lower()
        out_bin_dir = os.path.join(out_dir, bin_folder)
        os.makedirs(out_bin_dir, exist_ok=True)

        wav_path = os.path.join(out_bin_dir, base_fname + ".wav")
        clip_obj.export(wav_path, format="wav")
        generate_mel_spectrogram(clip_obj, wav_path.replace('.wav', '.png'))
        os.remove(wav_path)
        outputs.append(wav_path.replace('.wav', '.png'))

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

    if isinstance(files, str) and os.path.isdir(files):
        png_files = []
        for root, _, filenames in os.walk(files):
            for fname in filenames:
                if fname.endswith(".png"):
                    png_files.append(os.path.join(root, fname))
        files = png_files

    random.shuffle(files)
    total = len(files)
    train = files[:int(total * train_ratio)]
    val = files[int(total * train_ratio):int(total * (train_ratio + val_ratio))]
    test = files[int(total * (train_ratio + val_ratio)):]
    return train, val, test

# === Main ===
def main():
    db_path = "./db/chorusAvery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    categories = search_categories(cursor)
    for i, (_, name) in enumerate(categories):
        print(f"{i+1}. {name}")
    category_choice = int(input("Select target category: ")) - 1
    category_id, category_name = categories[category_choice]

    sounds = search_sounds_by_category(cursor, category_id)
    sound_ids = [sid for sid, _ in sounds]

    slug = input(f"Slug name (default: {category_name.lower().replace(' ', '_')}): ").strip()
    slug = slug or category_name.lower().replace(' ', '_')
    base_dir = f"./recordings/model/{slug}"

    for lbl in ['0', '1']:
        for split in ['train', 'validation', 'test']:
            os.makedirs(os.path.join(base_dir, lbl, split), exist_ok=True)

    loc_input = input("📍 Location IDs (comma-separated or *): ").strip()
    location_ids = None if loc_input == "*" else list(map(int, loc_input.split(',')))

    clips = get_clip_paths(cursor, sound_ids, location_ids)
    solo = [p for p, s, n in clips if s == 0 and n == 1]
    mixed = [p for p, s, n in clips if s > 0 or n > 1]
    selected_mixed = random.sample(mixed, min(len(mixed), len(solo)//4))
    positives = solo + selected_mixed

    # Load noises
    noises = [AudioSegment.from_file(os.path.join("./recordings/augmentation_noise", f))
              for f in os.listdir("./recordings/augmentation_noise") if f.endswith('.wav')]

    # Get comparable, minority, and species paths
    cursor.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ON ClipAnnotations.clip_id = Clips.id
        JOIN NonAnimalSounds ON ClipAnnotations.non_animal_sound_id = NonAnimalSounds.id
        WHERE NonAnimalSounds.category_id = 1 AND ClipAnnotations.non_animal_sound_id NOT IN ({})
    """.format(','.join('?' * len(sound_ids))), (sound_ids))
    comparable_paths = [r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ON ClipAnnotations.clip_id = Clips.id
        JOIN NonAnimalSounds ON ClipAnnotations.non_animal_sound_id = NonAnimalSounds.id
        WHERE NonAnimalSounds.category_id = 2 AND ClipAnnotations.non_animal_sound_id NOT IN ({})
    """.format(','.join('?' * len(sound_ids))), (sound_ids))
    minority_paths = [r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ON ClipAnnotations.clip_id = Clips.id
        WHERE ClipAnnotations.species_id IS NOT NULL
        AND Clips.id NOT IN (
            SELECT clip_id FROM ClipAnnotations WHERE non_animal_sound_id IN ({})
        )
    """.format(','.join(['?'] * len(sound_ids))), sound_ids)
    species_paths = [r[0] for r in cursor.fetchall()]

    overlay_pool = build_overlay_pool(positives, comparable_paths, minority_paths, species_paths)

    # === Process positives ===
    all_pos = []
    for file in positives:
        full_path = os.path.join("./recordings/training_data", file)
        clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
        base = os.path.splitext(os.path.basename(file))[0]
        out_dir = os.path.join(base_dir, '1', 'full')
        all_pos += export_augmented_versions(clip, base, out_dir, noises, overlay_pool, overlay_prob=0.25)

    # === Final move for positives ===
    full_pos_dir = os.path.join(base_dir, '1', 'full')
    train, val, test = split_data(full_pos_dir)
    for group, folder in zip([train, val, test], ['train', 'validation', 'test']):
        for f in group:
            tgt = os.path.join(base_dir, '1', folder, os.path.basename(f))
            shutil.move(f, tgt)
    shutil.rmtree(full_pos_dir)
    print("✅ Positive samples processed.")

    # === Prepare negatives ===
    total_pos = len(all_pos)
    neg_target = total_pos * 3
    comp_n = int(neg_target * 0.4)
    min_n = int(neg_target * 0.1)
    spc_n = int(neg_target * 0.5)

    comp_samples = random.choices(comparable_paths, k=comp_n)
    min_samples = random.choices(minority_paths, k=min_n)
    spc_samples = random.choices(species_paths, k=spc_n)
    neg_samples = comp_samples + min_samples + spc_samples
    random.shuffle(neg_samples)

    neg_outs = []
    for file in neg_samples:
        full_path = os.path.join("./recordings/training_data", file)
        clip = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
        base = f"{random.choice('abcdefghijklmnopqrstuvwxyz')}_neg_{random.randint(1000,9999)}"
        out_dir = os.path.join(base_dir, '0', 'full')
        neg_outs += export_augmented_versions(clip, base, out_dir, noises, overlay_pool, overlay_prob=0)

    # === Final move for negatives ===
    full_neg_dir = os.path.join(base_dir, '0', 'full')
    neg_train, neg_val, neg_test = split_data(full_neg_dir)
    for group, folder in zip([neg_train, neg_val, neg_test], ['train', 'validation', 'test']):
        for f in group:
            tgt = os.path.join(base_dir, '0', folder, os.path.basename(f))
            shutil.move(f, tgt)
    shutil.rmtree(full_neg_dir)
    print("✅ Negative samples processed and balanced.")

if __name__ == "__main__":
    main()
