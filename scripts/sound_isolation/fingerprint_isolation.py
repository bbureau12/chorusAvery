import numpy as np
import soundfile as sf
from scipy.signal import stft, istft

FINGERPRINT_DIR = "./fingerprints"
os.makedirs(FINGERPRINT_DIR, exist_ok=True)

def create_fingerprint(file_path, sr_target=44100):
    y, sr = sf.read(file_path)
    if y.ndim > 1:
        y = y.mean(axis=1)  # Convert to mono
    if sr != sr_target:
        raise ValueError("Sample rate mismatch. Resample your audio to 44100 Hz.")

    _, _, Zxx = stft(y, fs=sr, nperseg=1024)
    fingerprint = np.mean(np.abs(Zxx), axis=1)
    return fingerprint

def save_fingerprint(fingerprint, name):
    path = os.path.join(FINGERPRINT_DIR, f"{name}.npy")
    np.save(path, fingerprint)
    print(f"✅ Fingerprint saved to {path}")

def load_fingerprint(name):
    path = os.path.join(FINGERPRINT_DIR, f"{name}.npy")
    return np.load(path)

def subtract_fingerprint(mixed_file, fingerprint, sr_target=44100):
    y, sr = sf.read(mixed_file)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != sr_target:
        raise ValueError("Sample rate mismatch. Resample your audio to 44100 Hz.")

    f, t, Zxx = stft(y, fs=sr, nperseg=1024)
    mag = np.abs(Zxx)
    phase = np.angle(Zxx)

    fingerprint_matrix = np.tile(fingerprint[:, np.newaxis], (1, mag.shape[1]))
    subtracted_mag = np.clip(mag - fingerprint_matrix, a_min=0, a_max=None)

    Zxx_subtracted = subtracted_mag * np.exp(1j * phase)
    _, reconstructed = istft(Zxx_subtracted, fs=sr, nperseg=1024)
    return reconstructed

def save_audio(data, sr, path):
    sf.write(path, data, sr)
    print(f"🎧 Output saved to: {path}")

# Example usage:
# fp = create_fingerprint("chorus_only.wav")
# save_fingerprint(fp, "chorusfrog")
# fp = load_fingerprint("chorusfrog")
# output = subtract_fingerprint("mixed.wav", fp)
# save_audio(output, 44100, "peeper_estimate.wav")
