import os
import shutil
import sqlite3
from pydub import AudioSegment
from tqdm import tqdm
import random
import numpy as np
import librosa
import matplotlib.pyplot as plt
import librosa.display

DB_PATH = './db/chorusAvery.db'
TRAINING_FOLDER = './recordings/training_data'
DATASET_BASE = './training/species'

SLICE_DURATION_MS = 2000  # 2 seconds
AUGMENTATIONS_PER_CLIP = 3
VALIDATION_SPLIT = 0.2

os.makedirs(DATASET_BASE, exist_ok=True)

def get_solo_clips(species_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.clip_path FROM Clips c
        JOIN ClipAnnotations a ON a.clip_id = c.id
        WHERE a.species_id = ?
        AND NOT EXISTS (
            SELECT 1 FROM ClipAnnotations a2
            WHERE a2.clip_id = c.id AND a2.species_id != ?
        )
    """, (species_id, species_id))
    results = cursor.fetchall()
    conn.close()
    return [r[0] for r in results]

def get_mixed_clips(species_id, limit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.clip_path FROM Clips c
        WHERE c.id IN (
            SELECT clip_id FROM ClipAnnotations WHERE species_id = ?
        )
        AND c.id IN (
            SELECT clip_id FROM ClipAnnotations WHERE species_id != ?
        )
        LIMIT ?
    """, (species_id, species_id, limit))
    results = cursor.fetchall()
    conn.close()
    return [r[0] for r in results]

def slice_clip(path, out_folder):
    audio = AudioSegment.from_file(path)
    if len(audio) <= SLICE_DURATION_MS:
        print(f"⚠️ Skipping short clip: {path} ({len(audio)/1000:.2f}s)")
        return
    for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
        slice = audio[i:i+SLICE_DURATION_MS]
        if len(slice) != SLICE_DURATION_MS:
            print(f"⚠️ Skipping uneven slice in {path} at {i}ms ({len(slice)/1000:.2f}s)")
            continue
        base = os.path.splitext(os.path.basename(path))[0]
        slice_path = os.path.join(out_folder, f"{base}_s{i}.wav")
        slice.export(slice_path, format="wav")
        convert_to_spectrogram(slice_path)
        os.remove(slice_path)

def augment_clip(path, out_folder, n=3):
    audio = AudioSegment.from_file(path)
    base = os.path.splitext(os.path.basename(path))[0]
    for i in range(n):
        speed_factor = np.random.uniform(0.9, 1.1)
        augmented = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * speed_factor)
        }).set_frame_rate(audio.frame_rate)
        aug_path = os.path.join(out_folder, f"{base}_aug{i}.wav")
        augmented.export(aug_path, format="wav")
        convert_to_spectrogram(aug_path)
        os.remove(aug_path)

def convert_to_spectrogram(wav_path):
    if librosa.get_duration(filename=wav_path) < 2.0:
        print(f"⚠️ Skipping short audio file: {wav_path}")
        return
    y, sr = librosa.load(wav_path, sr=None)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_DB = librosa.power_to_db(S, ref=np.max)
    fig = plt.figure(figsize=(4, 4), dpi=150)
    librosa.display.specshow(S_DB, sr=sr, fmax=8000)
    plt.axis('off')
    spectrogram_path = wav_path.replace('.wav', '.png')
    plt.savefig(spectrogram_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

def build_dataset(species_id):
    base_path = os.path.join(DATASET_BASE, str(species_id))
    paths = {
        'solo': os.path.join(base_path, 'corpus/solo'),
        'mixed': os.path.join(base_path, 'corpus/mixed'),
        'train_solo': os.path.join(base_path, 'final/train/solo'),
        'train_mixed': os.path.join(base_path, 'final/train/mixed'),
        'val_solo': os.path.join(base_path, 'final/val/solo'),
        'val_mixed': os.path.join(base_path, 'final/val/mixed'),
    }

    for p in paths.values():
        os.makedirs(p, exist_ok=True)

    print("🔍 Fetching solo clips...")
    solo = get_solo_clips(species_id)
    print("🔍 Fetching mixed clips...")
    mixed = get_mixed_clips(species_id, len(solo))

    print("📥 Copying and slicing solo clips...")
    for clip in tqdm(solo):
        src = os.path.join(TRAINING_FOLDER, clip)
        if os.path.exists(src):
            slice_clip(src, paths['train_solo'])
            sliced_files = [f for f in os.listdir(paths['train_solo']) if f.endswith('.png') and f.startswith(os.path.splitext(os.path.basename(clip))[0])]
            for sf in sliced_files:
                wav_equiv = sf.replace('.png', '.wav')
                wav_path = os.path.join(paths['train_solo'], wav_equiv)
                if os.path.exists(wav_path):
                    augment_clip(wav_path, paths['train_solo'], AUGMENTATIONS_PER_CLIP)

    print("📥 Copying and slicing mixed clips...")
    for clip in tqdm(mixed):
        src = os.path.join(TRAINING_FOLDER, clip)
        if os.path.exists(src):
            slice_clip(src, paths['train_mixed'])

    print("🔀 Shuffling and splitting validation set...")
    for key in ['train_solo', 'train_mixed']:
        all_files = [f for f in os.listdir(paths[key]) if f.endswith('.png')]
        random.shuffle(all_files)
        val_count = int(len(all_files) * VALIDATION_SPLIT)
        for f in all_files[:val_count]:
            base = f.replace('.png', '.wav')
            src_wav = os.path.join(paths[key], base)
            dst_wav = os.path.join(paths[key.replace('train', 'val')], base)
            dst_png = os.path.join(paths[key.replace('train', 'val')], f)

            shutil.move(os.path.join(paths[key], f), dst_png)

            if os.path.exists(src_wav):
                shutil.move(src_wav, dst_wav)
                convert_to_spectrogram(dst_wav)
                os.remove(dst_wav)

if __name__ == "__main__":
    species_id = int(input("Enter the species ID to build dataset for: "))
    build_dataset(species_id)
