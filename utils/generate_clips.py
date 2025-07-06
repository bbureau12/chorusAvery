import os
import random
import shutil
import sqlite3
from pydub import AudioSegment

AUG_FOLDER = "./recordings/augmentation_noise"
RECORDINGS_ROOT = "./recordings"
MODEL_ROOT = "./recordings/model"
NEGATIVE_LENGTH_MS = 2500  # 2.5 seconds
TARGET_MULTIPLIER = 3  # negatives = positives * multiplier
SNR_RANGE_DB = (-5, -15)  # softer overlay in dB
SPLIT_RATIOS = (0.7, 0.15, 0.15)  # train, val, test

def load_augmentation_clips(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".wav")]

def overlay_with_augmentation(base_sound, augmentation_clips):
    overlay_clip = AudioSegment.from_file(random.choice(augmentation_clips))
    # Choose random offset within overlay clip to add variation
    if len(overlay_clip) > NEGATIVE_LENGTH_MS:
        max_offset = len(overlay_clip) - NEGATIVE_LENGTH_MS
        overlay_clip = overlay_clip[random.randint(0, max_offset):][:NEGATIVE_LENGTH_MS]
    else:
        overlay_clip = overlay_clip[:NEGATIVE_LENGTH_MS]

    # Attenuate overlay to make it softer (SNR)
    attenuation = random.uniform(*SNR_RANGE_DB)
    overlay_clip = overlay_clip + attenuation

    return base_sound.overlay(overlay_clip)

def get_positive_count(target_species_dir):
    positive_folder = None
    for sub in os.listdir(target_species_dir):
        if sub not in ("0",) and os.path.isdir(os.path.join(target_species_dir, sub)):
            positive_folder = os.path.join(target_species_dir, sub)
            break
    if not positive_folder:
        raise RuntimeError("Could not find positive folder with non-0 species ID.")
    return len([f for f in os.listdir(positive_folder) if f.endswith(".wav")])

def collect_clips_from_db(db_path, target_species_id, target_species_type_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1) Similar species
    cur.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
        JOIN Species s ON ca.species_id = s.id
        WHERE s.species_type_id = ? AND s.id != ?
        AND NOT EXISTS (SELECT 1 FROM ClipAnnotations ca2 WHERE ca2.clip_id = Clips.id AND ca2.species_id = ?)
    """, (target_species_type_id, target_species_id, target_species_id))
    similar = [row[0] for row in cur.fetchall()]

    # 2) Other species
    cur.execute("""
        SELECT DISTINCT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca ON Clips.id = ca.clip_id
        JOIN Species s ON ca.species_id = s.id
        WHERE s.species_type_id != ? AND NOT EXISTS (
            SELECT 1 FROM ClipAnnotations ca2 WHERE ca2.clip_id = Clips.id AND ca2.species_id = ?
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

def distribute_and_generate(negatives, total_needed, train_dir, val_dir, test_dir, augmentation_clips):
    random.shuffle(negatives)
    n_train = int(total_needed * SPLIT_RATIOS[0])
    n_val = int(total_needed * SPLIT_RATIOS[1])
    n_test = total_needed - n_train - n_val

    train, val, test = negatives[:n_train], negatives[n_train:n_train + n_val], negatives[n_train + n_val:]

    # Fill if we fall short (using overlays)
    def fill_and_save(batch, target, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        for i in range(target):
            if i < len(batch):
                base = AudioSegment.from_file(os.path.join(RECORDINGS_ROOT, batch[i]))
            else:
                base = AudioSegment.silent(duration=NEGATIVE_LENGTH_MS)  # fallback silent
            neg = overlay_with_augmentation(base, augmentation_clips)
            neg.export(os.path.join(out_dir, f"neg_{i:05d}.wav"), format="wav")

    fill_and_save(train, n_train, train_dir)
    fill_and_save(val, n_val, val_dir)
    fill_and_save(test, n_test, test_dir)

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
    # TODO: fetch species_type_id from DB based on species_id
    target_species_type_id = int(input("Enter species_type_id for target species (e.g., 2 for amphibians): "))

    positives = get_positive_count(os.path.join(model_path, 'train'))
    negatives_needed = positives * TARGET_MULTIPLIER
    print(f"➡️ Need ~{negatives_needed} negatives (3x positives).")

    similar, other, non_animal = collect_clips_from_db("./chorusAvery.db", int(species_id), target_species_type_id)
    augmentation_clips = load_augmentation_clips(AUG_FOLDER)

    # Combine negatives pool
    negatives_pool = similar + other + non_animal

    # Generate negatives with overlays
    distribute_and_generate(negatives_pool, negatives_needed,
                            os.path.join(model_path, 'train/0'),
                            os.path.join(model_path, 'validation/0'),
                            os.path.join(model_path, 'test/0'),
                            augmentation_clips)

    print("✅ Negative clips generated and distributed!")

if __name__ == "__main__":
    main()
