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

# === CONFIG ===
DB_PATH = './db/chorusAvery.db'
RAW_AUDIO_FOLDER = './recordings/training_data'
DATASET_BASE = './training/species'  # renamed root folder for clarity!

SLICE_DURATION_MS = 2500  # 2.5 seconds
AUGMENTATIONS_PER_CLIP = 3  # number of synthetic variants per slice (positive train only)
VAL_SPLIT = 0.2
TEST_SPLIT = 0.1

os.makedirs(DATASET_BASE, exist_ok=True)

# === DB FETCH ===
def get_all_positive_clips(species_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.clip_path
        FROM Clips c 
        JOIN ClipAnnotations a ON a.clip_id = c.id
        WHERE a.species_id = ?
    """, (species_id,))
    results = cursor.fetchall()
    conn.close()
    return [r[0] for r in results]

def get_all_negative_clips(species_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.clip_path
        FROM Clips c
        WHERE c.id NOT IN (
            SELECT clip_id FROM ClipAnnotations WHERE species_id = ?
        )
    """, (species_id,))
    results = cursor.fetchall()
    conn.close()
    clip_paths = [r[0] for r in results]
    random.shuffle(clip_paths)
    return clip_paths

# === CLEAN FOLDERS ===
def clear_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

# === SLICING ===
def slice_clip(path, out_folder):
    audio = AudioSegment.from_file(path)
    if len(audio) < SLICE_DURATION_MS:
        print(f"⚠️ Skipping short clip: {path} ({len(audio)/1000:.2f}s)")
        return []
    slice_paths = []
    for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
        chunk = audio[i:i+SLICE_DURATION_MS]
        base = os.path.splitext(os.path.basename(path))[0]
        temp_wav = os.path.join(out_folder, f"{base}_s{i}.wav")
        chunk.export(temp_wav, format="wav")
        slice_paths.append(temp_wav)
    return slice_paths

# === AUGMENTING ===
def augment_clip(wav_path, out_folder, n=3):
    audio = AudioSegment.from_file(wav_path)
    base = os.path.splitext(os.path.basename(wav_path))[0]
    for i in range(n):
        speed_factor = np.random.uniform(0.9, 1.1)
        augmented = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * speed_factor)
        }).set_frame_rate(audio.frame_rate)
        temp_wav = os.path.join(out_folder, f"{base}_aug{i}.wav")
        augmented.export(temp_wav, format="wav")
        convert_to_spectrogram(temp_wav)
        os.remove(temp_wav)

# === SPECTROGRAM ===
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

# === PROCESS SPLITS ===
def split_and_process(clips, out_paths, augment=False):
    random.shuffle(clips)
    total = len(clips)
    val_count = int(total * VAL_SPLIT)
    test_count = int(total * TEST_SPLIT)
    train_count = total - val_count - test_count

    splits = {
        'train': clips[:train_count],
        'val': clips[train_count:train_count+val_count],
        'test': clips[train_count+val_count:]
    }

    split_counts = {k: len(v) for k, v in splits.items()}
    print(f"Split counts: {split_counts}")
    
    for split, clip_list in splits.items():
        totalSpecs = 0
        for clip in tqdm(clip_list, desc=f"Processing {split}"):
            src = os.path.join(RAW_AUDIO_FOLDER, clip)
            if os.path.exists(src):
                slices = slice_clip(src, out_paths[split])
                totalSpecs += len(slices)
                for slice_wav in slices:
                    convert_to_spectrogram(slice_wav)

                if augment and split == 'train':
                    for slice_wav in slices:
                        augment_clip(slice_wav, out_paths[split], AUGMENTATIONS_PER_CLIP)

                for slice_wav in slices:
                    if os.path.exists(slice_wav):
                        os.remove(slice_wav)
        print(f"{totalSpecs} total items processed.")

    return split_counts

# === MAIN ===
def build_dataset(species_id):
    base = os.path.join(DATASET_BASE, str(species_id))
    paths = {
        'train_positive': os.path.join(base, 'train/positive'),
        'val_positive': os.path.join(base, 'val/positive'),
        'test_positive': os.path.join(base, 'test/positive'),
        'train_negative': os.path.join(base, 'train/negative'),
        'val_negative': os.path.join(base, 'val/negative'),
        'test_negative': os.path.join(base, 'test/negative'),
    }

    for p in paths.values():
        clear_folder(p)

    print("🔍 Getting positives...")
    positives = get_all_positive_clips(species_id)
    print(f"✅ Found {len(positives)} positives")

    print("🔍 Getting all negatives...")
    all_negatives = get_all_negative_clips(species_id)
    print(f"✅ Found {len(all_negatives)} negatives (before trimming)")

    print("⚙️ Processing positives with augmentation...")
    pos_split_counts = split_and_process(
        positives,
        {'train': paths['train_positive'],
         'val': paths['val_positive'],
         'test': paths['test_positive']},
        augment=True
    )

    negatives_needed = (
        pos_split_counts['train'] + pos_split_counts['val'] + pos_split_counts['test']
    )
    if len(all_negatives) < negatives_needed:
        raise ValueError("❌ Not enough negatives to match positives!")

    negatives_splits = {}
    offset = 0
    for split in ['train', 'val', 'test']:
        count = pos_split_counts[split]
        negatives_splits[split] = all_negatives[offset:offset+count]
        offset += count

    print(f"✅ Negative split counts: { {k: len(v) for k, v in negatives_splits.items()} }")

    print("⚙️ Processing negatives (no extra aug)...")
    for split in ['train', 'val', 'test']:
        for clip in tqdm(negatives_splits[split], desc=f"Processing negative {split}"):
            src = os.path.join(RAW_AUDIO_FOLDER, clip)
            if os.path.exists(src):
                slices = slice_clip(src, paths[f'{split}_negative'])
                for slice_wav in slices:
                    convert_to_spectrogram(slice_wav)
                    if os.path.exists(slice_wav):
                        os.remove(slice_wav)

    print("✅ Species dataset build complete, balanced and augmented!")

if __name__ == "__main__":
    species_id = int(input("Enter species_id to build dataset for: "))
    build_dataset(species_id)
