import os
import random
import shutil
import sqlite3
import sys
from pydub import AudioSegment
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 🔹 Prevent tkinter errors on shutdown
import matplotlib.pyplot as plt
from scipy.signal import spectrogram
# === Import project utilities
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from utils.generate_spectogram import generate_mel_spectrogram
from scripts.augmentation.species_nonspecies_augmentor import SpeciesAugmentor
from scripts.training.collection.collect_negative_clips import NegativeClipGenerator

def search_species(cursor, query):
    cursor.execute("SELECT id, name FROM Species")
    return [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]

# def generate_spectrogram(audio, output_path):
#     samples = np.array(audio.get_array_of_samples())
#     freqs, times, Sxx = spectrogram(samples, fs=audio.frame_rate, nperseg=256)
#     plt.figure(figsize=(2, 2))
#     plt.pcolormesh(times, freqs, 10*np.log10(Sxx + 1e-10), shading='gouraud')
#     plt.axis('off')
#     plt.tight_layout(pad=0)
#     plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
#     plt.close()

def pad_audio(audio, pad_ms=500):
    silence_segment = AudioSegment.silent(duration=pad_ms)
    return random.choice([silence_segment + audio, audio + silence_segment])

def overlay_noise(clip, noise, target_dbfs=None):
    if target_dbfs is not None and noise.dBFS > target_dbfs:
        diff_db = noise.dBFS - target_dbfs + 5  # keep noise slightly under
        noise = noise - diff_db
    return clip.overlay(noise)

def polarize_volume(audio, target_dbfs, factor=1.3):
    diff = target_dbfs - audio.dBFS
    adjustment = diff * factor
    # Optional: limit extremes to avoid distortion/silence
    adjustment = max(min(adjustment, 20), -20)
    if abs(adjustment) < 1.0:
        return None
    return audio + adjustment

def split_data(clips, train_ratio=0.7, val_ratio=0.2):
    random.shuffle(clips)
    total = len(clips)
    train_end = int(train_ratio * total)
    val_end = train_end + int(val_ratio * total)
    return clips[:train_end], clips[train_end:val_end], clips[val_end:]

def main():
    db_path = "./db/chorusAvery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    species_name = input("🔎 Species name: ").strip()
    matches = search_species(cursor, species_name)
    if not matches:
        print("❌ No matching species found.")
        return
    if len(matches) > 1:
        for idx, (_, name) in enumerate(matches):
            print(f"{idx+1}. {name}")
        sel = int(input("Choose species number: ")) - 1
        species_id, species_name = matches[sel]
    else:
        species_id, species_name = matches[0]
    print(f"✅ Selected species: {species_name} (ID {species_id})")

    slug = species_name.lower().replace(" ", "_")
    base_dir = f"./recordings/model/{slug}"
    if os.path.exists(base_dir):
        resp = input(f"⚠️ The model folder '{base_dir}' already exists. Delete it before continuing? (y/n): ").strip().lower()
        if resp == 'y':
            shutil.rmtree(base_dir)
            print(f"🗑️ Removed existing model folder: {base_dir}")
        else:
            print("🚫 Exiting to prevent mixing old and new datasets in this model.")
            return
    train_dir = os.path.join(base_dir, "train", str(species_id))
    val_dir = os.path.join(base_dir, "validation", str(species_id))
    test_dir = os.path.join(base_dir, "test", str(species_id))
    for d in [train_dir, val_dir, test_dir]:
        os.makedirs(d, exist_ok=True)

    location_input = input("📍 Location IDs (comma-separated or * for all): ").strip()
    if location_input == "*":
        cursor.execute("""
            SELECT Clips.clip_path, COUNT(DISTINCT ca2.species_id) as species_count
            FROM Clips
            JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
            GROUP BY Clips.id
            HAVING SUM(ca2.species_id = ?) > 0
        """, (species_id,))
    else:
        loc_ids = tuple(map(int, location_input.split(',')))
        placeholders = ','.join(['?']*len(loc_ids))
        cursor.execute(f"""
            SELECT Clips.clip_path, COUNT(DISTINCT ca2.species_id) as species_count
            FROM Clips
            JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
            JOIN SourceFiles ON Clips.source_id = SourceFiles.id
            WHERE SourceFiles.LocationID IN ({placeholders})
            GROUP BY Clips.id
            HAVING SUM(ca2.species_id = ?) > 0
        """, (*loc_ids, species_id))

    # === Common processing logic ===
    all_results = cursor.fetchall()
    random.shuffle(all_results)
    solo_clips = [path for path, count in all_results if count == 1]
    mixed_clips = [path for path, count in all_results if count > 1]
    n_mixed = min(len(mixed_clips), len(solo_clips) // 4)
    selected_mixed = random.sample(mixed_clips, n_mixed)
    clips = solo_clips + selected_mixed
    print(f"🎧 Using {len(solo_clips)} solo and {n_mixed} mixed clips. Total: {len(clips)}")

    noises = []
    for f in os.listdir("./recordings/augmentation_noise"):
        if f.endswith('.wav'):
            noises.append(AudioSegment.from_file(os.path.join("./recordings/augmentation_noise", f)))
    print(f"🎼 Loaded {len(noises)} noise files for augmentation.")

    processed_clips = []
    for clip_file in clips:
        clip_path = os.path.join("./recordings/training_data", clip_file)
        clip = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)
        clip_basename = os.path.splitext(os.path.basename(clip_file))[0]

        # Original
        out_wav = f"{clip_basename}.wav"
        out_path = os.path.join(base_dir, out_wav)
        clip.export(out_path, format="wav")
        generate_mel_spectrogram(clip, out_path.replace('.wav', '.png'))
        processed_clips.append(out_path)

        # Padding
        padded = pad_audio(clip)
        padded_out = f"{clip_basename}_pad.wav"
        padded_path = os.path.join(base_dir, padded_out)
        padded.export(padded_path, format="wav")
        generate_mel_spectrogram(padded, padded_path.replace('.wav', '.png'))
        processed_clips.append(padded_path)
        # 🔹 Boosted augmentation (if needed)
        boosted = polarize_volume(clip, -22.0)
        if boosted:
            boosted_out = f"{clip_basename}_boosted.wav"
            boosted_path = os.path.join(base_dir, boosted_out)
            boosted.export(boosted_path, format="wav")
            generate_mel_spectrogram(boosted, boosted_path.replace('.wav', '.png'))
            processed_clips.append(boosted_path)
            
        # Augmentations
        augment_count = 3
        if len(clips) < 500:
            augment_count = 5
        if len(clips) < 150:
            augment_count = 10
        for i in range(augment_count):
            noise = random.choice(noises)
            augmented = overlay_noise(clip, noise, clip.dBFS)
            aug_out = f"{clip_basename}_aug{i}.wav"
            aug_path = os.path.join(base_dir, aug_out)
            augmented.export(aug_path, format="wav")
            generate_mel_spectrogram(augmented, aug_path.replace('.wav', '.png'))
            processed_clips.append(aug_path)

    train, val, test = split_data(processed_clips, train_ratio=0.7, val_ratio=0.2)
    for dataset, folder in [(train, train_dir), (val, val_dir), (test, test_dir)]:
        for f in dataset:
            dest_wav = os.path.join(folder, os.path.basename(f))
            shutil.move(f, dest_wav)
            dest_png = dest_wav.replace('.wav', '.png')
            shutil.move(f.replace('.wav', '.png'), dest_png)
            os.remove(dest_wav)  # 🔥 Remove wav, keep only png

    print(f"✅ Data split: {len(train)} train, {len(val)} validation, {len(test)} test.")

    ## Run the augmentation
    augmentor = SpeciesAugmentor(db_path=db_path, models_root="./recordings/model")
    augmentor.run(species_name=species_name, species_id=species_id)

    ## (Finally) run the negatives

    neg_gen = NegativeClipGenerator(model_name=slug)  # slug matches your model folder name
    neg_gen.run()

if __name__ == "__main__":
    main()
