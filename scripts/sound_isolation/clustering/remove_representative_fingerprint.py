import os
import numpy as np
from pydub import AudioSegment
import librosa
import librosa.display
import matplotlib.pyplot as plt
from io import BytesIO
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import img_to_array
import tensorflow as tf
from scipy.signal import correlate2d, butter, lfilter
from scipy.ndimage import gaussian_filter
from scipy.io.wavfile import write as wav_write
from PIL import Image

# === CONFIG ===
MODEL_PATH = './models/best_chorus_frog_model.keras'
REP_DIR = './representatives'  # Using all clusters
MIXED_AUDIO_DIR = './recordings/mixed'
OUTPUT_DIR = './recordings/cleaned'
SLICE_DURATION_MS = 2000
PREDICTION_THRESHOLD = 0.90
IMAGE_SIZE = (224, 224)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Load Keras classification model
print("📦 Loading model...")
model = load_model(MODEL_PATH)
class_names = ['chorus_frog', 'negative']

# === Load all representative spectrogram templates
def load_templates(rep_dir):
    templates = []
    for cluster in os.listdir(rep_dir):
        cluster_path = os.path.join(rep_dir, cluster)
        if os.path.isdir(cluster_path):
            for fname in os.listdir(cluster_path):
                if fname.endswith('.png'):
                    img = Image.open(os.path.join(cluster_path, fname)).convert('L').resize(IMAGE_SIZE)
                    templates.append(np.array(img) / 255.0)
    return templates

template_specs = load_templates(REP_DIR)

# === Helper: Convert audio slice to model-ready spectrogram image and return original signal and spectrogram
def slice_to_model_input(audio_slice):
    with BytesIO() as buffer:
        audio_slice.export(buffer, format='wav')
        buffer.seek(0)
        y, sr = librosa.load(buffer, sr=22050)
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
        S_DB = librosa.power_to_db(S, ref=np.max)
        fig = plt.figure(figsize=(4, 4), dpi=IMAGE_SIZE[0]//4)
        librosa.display.specshow(S_DB, sr=sr, fmax=8000)
        plt.axis('off')
        buf = BytesIO()
        plt.savefig(buf, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        img = tf.keras.preprocessing.image.load_img(buf, target_size=IMAGE_SIZE, color_mode='rgb')
        img_array = img_to_array(img) / 255.0
        return np.expand_dims(img_array, axis=0), sr, y, S_DB

# === Bandstop filter to remove chorus frog band from waveform (2-4 kHz)
def bandstop_filter(data, sr, lowcut=2000, highcut=4000, order=4):
    nyq = 0.5 * sr
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='bandstop')
    return lfilter(b, a, data)

# === Main Loop over mixed audio files
for fname in os.listdir(MIXED_AUDIO_DIR):
    if not fname.endswith('.wav'):
        continue

    print(f"\n🎧 Processing: {fname}")
    path = os.path.join(MIXED_AUDIO_DIR, fname)
    audio = AudioSegment.from_file(path).set_channels(1).set_frame_rate(22050)

    output_audio = AudioSegment.empty()
    removed_segments = 0

    for i in range(0, len(audio) - SLICE_DURATION_MS + 1, SLICE_DURATION_MS):
        segment = audio[i:i+SLICE_DURATION_MS]
        model_input, sr, raw_y, S_DB = slice_to_model_input(segment)
        prediction = model.predict(model_input)[0]
        pred_label = class_names[np.argmax(prediction)]
        confidence = float(np.max(prediction))

        if pred_label == 'chorus_frog' and confidence >= PREDICTION_THRESHOLD:
            print(f"🎯 Model detected chorus frog at {i//1000}-{(i+SLICE_DURATION_MS)//1000}s (Confidence: {confidence:.2f})")
            # Apply bandstop filter in the waveform domain
            filtered = bandstop_filter(raw_y, sr)
            # Convert to int16 for AudioSegment
            filtered_pcm = np.int16(filtered / np.max(np.abs(filtered)) * 32767)
            clean_segment = AudioSegment(
                filtered_pcm.tobytes(),
                frame_rate=sr,
                sample_width=2,
                channels=1
            )
            output_audio += clean_segment
            removed_segments += 1
        else:
            raw_pcm = np.int16(raw_y / np.max(np.abs(raw_y)) * 32767)
            clean_segment = AudioSegment(
                raw_pcm.tobytes(),
                frame_rate=sr,
                sample_width=2,
                channels=1
            )
            output_audio += clean_segment

    out_path = os.path.join(OUTPUT_DIR, fname)
    output_audio.export(out_path, format='wav')
    print(f"✅ Saved surgically cleaned audio to: {out_path} ({removed_segments} frog-positive segments masked)")
