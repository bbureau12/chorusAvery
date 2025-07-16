import librosa
import librosa.display
from matplotlib import pyplot as plt
import numpy as np

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
