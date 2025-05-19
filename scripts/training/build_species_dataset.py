import os
import shutil
import sqlite3
from pydub import AudioSegment
from tqdm import tqdm
import random
import numpy as np

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
    for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
        slice = audio[i:i+SLICE_DURATION_MS]
        base = os.path.splitext(os.path.basename(path))[0]
        slice.export(os.path.join(out_folder, f"{base}_s{i}.wav"), format="wav")

def augment_clip(path, out_folder, n=3):
    audio = AudioSegment.from_file(path)
    base = os.path.splitext(os.path.basename(path))[0]
    for i in range(n):
        pitch_shift = np.random.uniform(-2, 2)
        speed_factor = np.random.uniform(0.9, 1.1)
        augmented = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * speed_factor)
        }).set_frame_rate(audio.frame_rate)
        # simple pitch shift simulation
        augmented.export(os.path.join(out_folder, f"{base}_aug{i}.wav"), format="wav")

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
            shutil.copy(src, paths['solo'])
            slice_clip(src, paths['train_solo'])
            augment_clip(src, paths['train_solo'], AUGMENTATIONS_PER_CLIP)

    print("📥 Copying and slicing mixed clips...")
    for clip in tqdm(mixed):
        src = os.path.join(TRAINING_FOLDER, clip)
        if os.path.exists(src):
            shutil.copy(src, paths['mixed'])
            slice_clip(src, paths['train_mixed'])

    print("🔀 Shuffling and splitting validation set...")
    for key in ['train_solo', 'train_mixed']:
        all_files = [f for f in os.listdir(paths[key]) if f.endswith('.wav')]
        random.shuffle(all_files)
        val_count = int(len(all_files) * VALIDATION_SPLIT)
        for f in all_files[:val_count]:
            shutil.move(os.path.join(paths[key], f), os.path.join(paths[key.replace('train', 'val')], f))

if __name__ == "__main__":
    species_id = int(input("Enter the species ID to build dataset for: "))
    build_dataset(species_id)
