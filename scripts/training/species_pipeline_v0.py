import os
import random
import shutil
import sqlite3
from pydub import AudioSegment
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 🔹 Prevent tkinter errors on shutdown
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

def search_species(cursor, query):
    cursor.execute("SELECT id, name FROM Species")
    return [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]

def generate_spectrogram(audio, output_path):
    samples = np.array(audio.get_array_of_samples())
    freqs, times, Sxx = spectrogram(samples, fs=audio.frame_rate, nperseg=256)
    plt.figure(figsize=(2, 2))
    plt.pcolormesh(times, freqs, 10*np.log10(Sxx + 1e-10), shading='gouraud')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close()

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
    train_dir = os.path.join(base_dir, "train", str(species_id))
    val_dir = os.path.join(base_dir, "validation", str(species_id))
    test_dir = os.path.join(base_dir, "test", str(species_id))
    for d in [train_dir, val_dir, test_dir]:
        os.makedirs(d, exist_ok=True)

    location_input = input("📍 Location IDs (comma-separated or * for all): ").strip()
    if location_input == "*":
        cursor.execute("""
        SELECT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca1 ON Clips.id = ca1.clip_id
        WHERE ca1.species_id=?
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              WHERE ca2.clip_id=Clips.id
                AND ca2.species_id != ?
          )
        """, (species_id,species_id,))
    else:
        loc_ids = tuple(map(int, location_input.split(',')))
        placeholders = ','.join(['?']*len(loc_ids))
        cursor.execute(f"""
            SELECT Clips.clip_path FROM Clips
            JOIN ClipAnnotations ON Clips.id=ClipAnnotations.clip_id
            JOIN SourceFiles ON Clips.source_id=SourceFiles.id
            WHERE ClipAnnotations.species_id=? AND SourceFiles.LocationID IN ({placeholders})
        """, (species_id, *loc_ids))
    clips = [row[0] for row in cursor.fetchall()]
    print(f"🎧 Found {len(clips)} clips for species '{species_name}'.")

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
        generate_spectrogram(clip, out_path.replace('.wav', '.png'))
        processed_clips.append(out_path)

        # Padding
        padded = pad_audio(clip)
        padded_out = f"{clip_basename}_pad.wav"
        padded_path = os.path.join(base_dir, padded_out)
        padded.export(padded_path, format="wav")
        generate_spectrogram(padded, padded_path.replace('.wav', '.png'))
        processed_clips.append(padded_path)
        # 🔹 Boosted augmentation (if needed)
        boosted = polarize_volume(clip, -22.0)
        if boosted:
            boosted_out = f"{clip_basename}_boosted.wav"
            boosted_path = os.path.join(base_dir, boosted_out)
            boosted.export(boosted_path, format="wav")
            generate_spectrogram(boosted, boosted_path.replace('.wav', '.png'))
            processed_clips.append(boosted_path)
            
        # Augmentations
        for i in range(3):
            noise = random.choice(noises)
            augmented = overlay_noise(clip, noise, clip.dBFS)
            aug_out = f"{clip_basename}_aug{i}.wav"
            aug_path = os.path.join(base_dir, aug_out)
            augmented.export(aug_path, format="wav")
            generate_spectrogram(augmented, aug_path.replace('.wav', '.png'))
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

    neg_train_dir = os.path.join(base_dir, "train", "0")
    neg_val_dir   = os.path.join(base_dir, "validation", "0")
    neg_test_dir  = os.path.join(base_dir, "test", "0")

    neg_clips = []

    cursor.execute("""
        SELECT DISTINCT Clips.clip_path
        FROM Clips
        JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
        WHERE ClipAnnotations.species_id != ?
        AND Clips.id NOT IN (
            SELECT clip_id FROM ClipAnnotations WHERE species_id = ?
        )
    """, (species_id, species_id))
    neg_clips = [row[0] for row in cursor.fetchall()]

    random.shuffle(neg_clips)
    num_neg = len(processed_clips)

    for split_name, folder, num_samples in [
        ("train", neg_train_dir, len(train)),
        ("validation", neg_val_dir, len(val)),
        ("test", neg_test_dir, len(test))
    ]:
        os.makedirs(folder, exist_ok=True)
        for i in range(num_samples):
            neg_clip = neg_clips.pop() if neg_clips else None
            if not neg_clip:
                break

            clip_full_path = os.path.join("./recordings/training_data", neg_clip)
            if not os.path.exists(clip_full_path):
                print(f"⚠️ Negative clip missing, skipping: {clip_full_path}")
                continue

            clip = AudioSegment.from_file(clip_full_path).set_channels(1).set_frame_rate(16000)
            out_name = f"neg_{split_name}_{i:04d}.wav"
            out_path = os.path.join(folder, out_name)
            clip.export(out_path, format="wav")
            generate_spectrogram(clip, out_path.replace('.wav', '.png'))
            os.remove(out_path)  # 🔥 Remove wav, keep only png

    conn.close()
    print("\n🏁 Dataset preparation complete!")

if __name__ == "__main__":
    main()
