import os
import shutil
from pydub import AudioSegment
from tqdm import tqdm
import random
import librosa
import numpy as np
import matplotlib.pyplot as plt
import librosa.display

SLICE_DURATION_MS = 2000
NEGATIVE_WAV_DIR = './training/species_classification/manual_val/negative'
OUTPUT_BASE = './training/species_classification'
TEMP_DIR = './temp_negative_slices'

def convert_to_spectrogram(wav_path):
    y, sr = librosa.load(wav_path, sr=None)
    if librosa.get_duration(y=y, sr=sr) < 2.0:
        return None
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_DB = librosa.power_to_db(S, ref=np.max)
    fig = plt.figure(figsize=(4, 4), dpi=150)
    librosa.display.specshow(S_DB, sr=sr, fmax=8000)
    plt.axis('off')
    png_path = wav_path.replace('.wav', '.png')
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return png_path

def step_generate_negative_images():
    print("🔍 Slicing negatives from:", NEGATIVE_WAV_DIR)

    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    for wav_file in os.listdir(NEGATIVE_WAV_DIR):
        if not wav_file.endswith(('.wav', '.mp3')):
            continue
        full_path = os.path.join(NEGATIVE_WAV_DIR, wav_file)
        audio = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(22050)

        for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
            clip = audio[i:i+SLICE_DURATION_MS]
            base = f"{os.path.splitext(wav_file)[0]}_s{i}"
            wav_out = os.path.join(TEMP_DIR, f"{base}.wav")
            clip.export(wav_out, format='wav')
            png_path = convert_to_spectrogram(wav_out)
            os.remove(wav_out)
    
    print(f"✅ Generated {len([f for f in os.listdir(TEMP_DIR) if f.endswith('.png')])} negative spectrograms.")

def step_split_negatives():
    print("📦 Distributing negatives based on frog sample counts...")

    train_frog_path = os.path.join(OUTPUT_BASE, 'train', 'chorus_frog')
    val_frog_path = os.path.join(OUTPUT_BASE, 'val', 'chorus_frog')

    train_target = len([f for f in os.listdir(train_frog_path) if f.endswith('.png')])
    val_target = len([f for f in os.listdir(val_frog_path) if f.endswith('.png')])
    total_target = train_target + val_target

    all_negatives = [f for f in os.listdir(TEMP_DIR) if f.endswith('.png')]
    actual_total = len(all_negatives)
    random.shuffle(all_negatives)

    if actual_total < total_target:
        print(f"⚠️ Not enough negative samples ({actual_total}) to match frog count ({total_target}). Splitting proportionally.")
        train_target = int(actual_total * (train_target / total_target))
        val_target = actual_total - train_target

    os.makedirs(os.path.join(OUTPUT_BASE, 'train', 'negative'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_BASE, 'val', 'negative'), exist_ok=True)

    for i, file in enumerate(all_negatives):
        src = os.path.join(TEMP_DIR, file)
        if i < train_target:
            dst = os.path.join(OUTPUT_BASE, 'train', 'negative', file)
        else:
            dst = os.path.join(OUTPUT_BASE, 'val', 'negative', file)
        shutil.move(src, dst)

    shutil.rmtree(TEMP_DIR)
    print("✅ Negative images sorted into training/validation sets.")

if __name__ == '__main__':
    step_generate_negative_images()
    step_split_negatives()
    print("🎯 Negative dataset complete.")
