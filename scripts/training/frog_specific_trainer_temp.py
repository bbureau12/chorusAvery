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
VALIDATION_SPLIT = 0.2

INPUT_RANDOM_WAV = 'D:/Projects/Sounds/Summer All Nighter/New folder/240903_0315.wav'
CHORUS_PNG_PATHS = [
    './training/species/1/final/train/solo',
    './training/species/1/final/train/mixed',
    './training/species/1/final/val/solo',
    './training/species/1/final/val/mixed'
]
OUTPUT_BASE = './training/species_classification'


def convert_to_spectrogram(wav_path):
    y, sr = librosa.load(wav_path, sr=None)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_DB = librosa.power_to_db(S, ref=np.max)
    fig = plt.figure(figsize=(4, 4), dpi=150)
    librosa.display.specshow(S_DB, sr=sr, fmax=8000)
    plt.axis('off')
    png_path = wav_path.replace('.wav', '.png')
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def step1_copy_chorus_images():
    for path in CHORUS_PNG_PATHS:
        set_type = 'val' if 'val' in path else 'train'
        dest = os.path.join(OUTPUT_BASE, set_type, 'chorus_frog')
        os.makedirs(dest, exist_ok=True)
        for f in os.listdir(path):
            if f.endswith('.png'):
                shutil.copy(os.path.join(path, f), os.path.join(dest, f))


def step2_generate_no_frog_images():
    train_chorus_path = os.path.join(OUTPUT_BASE, 'train', 'chorus_frog')
    val_chorus_path = os.path.join(OUTPUT_BASE, 'val', 'chorus_frog')

    train_count = len([f for f in os.listdir(train_chorus_path) if f.endswith('.png')])
    val_count = len([f for f in os.listdir(val_chorus_path) if f.endswith('.png')])

    total_needed = train_count + val_count
    audio = AudioSegment.from_file(INPUT_RANDOM_WAV)
    audio = audio.set_channels(1).set_frame_rate(22050)

    slices = []
    for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
        clip = audio[i:i+SLICE_DURATION_MS]
        base = f"nofrog_{i}"
        path = os.path.join('./temp_nofrog', f"{base}.wav")
        os.makedirs('./temp_nofrog', exist_ok=True)
        clip.export(path, format='wav')
        convert_to_spectrogram(path)
        slices.append(path.replace('.wav', '.png'))
        if len(slices) >= total_needed:
            break

    random.shuffle(slices)
    os.makedirs(os.path.join(OUTPUT_BASE, 'train', 'no_frog'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_BASE, 'val', 'no_frog'), exist_ok=True)

    for i, img in enumerate(slices):
        if i < train_count:
            shutil.move(img, os.path.join(OUTPUT_BASE, 'train', 'no_frog', os.path.basename(img)))
        else:
            shutil.move(img, os.path.join(OUTPUT_BASE, 'val', 'no_frog', os.path.basename(img)))

    shutil.rmtree('./temp_nofrog')


if __name__ == '__main__':
    step1_copy_chorus_images()
    step2_generate_no_frog_images()
    print("✅ Binary classification dataset prepared.")
