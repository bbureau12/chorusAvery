import librosa
import librosa.display
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use("Agg")
import numpy as np
import cv2

# === Parameters centralization ===
TARGET_SR = 16000
N_MELS = 128
FMAX = 8000
FIG_SIZE = (4, 4)
DPI = 150

def generate_mel_spectrogram(audio, output_path, target_sr=TARGET_SR):
    """
    Generates and saves a Mel spectrogram from a pydub AudioSegment.
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
    S = librosa.feature.melspectrogram(y=samples, sr=target_sr, n_mels=N_MELS, fmax=FMAX)
    S_DB = librosa.power_to_db(S, ref=np.max)
    fig = plt.figure(figsize=FIG_SIZE, dpi=DPI)
    librosa.display.specshow(S_DB, sr=target_sr, fmax=FMAX)
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

def get_spectrogram_settings():
    """
    Returns a dictionary with the current spectrogram generation parameters.
    """
    return {
        "type": "mel",
        "lib": "librosa",
        "n_mels": N_MELS,
        "fmax": FMAX,
        "figure_size": list(FIG_SIZE),
        "dpi": DPI,
        "target_sample_rate": TARGET_SR
    }

def load_spectrogram(image_path, resize=(224, 224), grayscale=True):
    """
    Loads a spectrogram image and returns it as a normalized array.
    
    Args:
        image_path (str): Path to the saved spectrogram image (e.g. PNG).
        resize (tuple): Target dimensions, default (224, 224).
        grayscale (bool): Whether to load the image in grayscale or color.

    Returns:
        np.ndarray: Normalized spectrogram array (0.0 - 1.0 range).
    """
    flag = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    img = cv2.imread(image_path, flag)

    if img is None:
        raise FileNotFoundError(f"❌ Could not load spectrogram at {image_path}")

    img_resized = cv2.resize(img, resize)

    # If grayscale, add channel dimension: (H, W) → (H, W, 1)
    if grayscale:
        img_resized = np.expand_dims(img_resized, axis=-1)

    # Normalize to 0–1
    img_normalized = img_resized.astype(np.float32) / 255.0

    return img_normalized
