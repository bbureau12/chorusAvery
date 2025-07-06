import os
import random
import sqlite3
import sys
import tensorflow as tf
import numpy as np
from pydub import AudioSegment
import matplotlib
matplotlib.use('Agg')
from tqdm import tqdm

# Add project root to import path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.generate_spectogram import generate_mel_spectrogram
from utils.model_spec_writer import SpecWriter

DATA_DIR = './recordings/training_data'
MODEL_DIR = './models/complete'
TARGET_DURATION_MS = 2500  # Ensure cohort clips match training duration

def standardize_duration(audio):
    duration = len(audio)
    if duration >= TARGET_DURATION_MS:
        return audio[:TARGET_DURATION_MS]
    pad_ms = TARGET_DURATION_MS - duration
    silence = AudioSegment.silent(duration=pad_ms)
    return audio + silence

def main():
    # === Select model
    models = [f for f in os.listdir(MODEL_DIR) if f.endswith('.keras')]
    if not models:
        print("❌ No models found in models/complete/")
        return

    print("\n📦 Available models:")
    for idx, name in enumerate(models):
        print(f"{idx + 1}. {name}")
    sel = int(input("Select model number: ")) - 1
    model_path = os.path.join(MODEL_DIR, models[sel])
    print(f"✅ Using model: {models[sel]}")

    # === Load model & class names
    model = tf.keras.models.load_model(model_path)
    class_names = getattr(model, 'class_names', ['0', '1'])
    print(f"🔎 Loaded model with class names: {class_names}")

    # === Get species ID
    species_name = input("🔎 Enter species name: ").strip().lower()
    conn = sqlite3.connect("./db/chorusAvery.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Species WHERE LOWER(name)=?", (species_name,))
    row = cursor.fetchone()
    if not row:
        print("❌ Species not found.")
        return
    species_id = row[0]
    print(f"✅ Using species ID {species_id} for cohorts.")

    # === Select cohort clips
    cursor.execute("""
        SELECT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca1 ON Clips.id=ca1.clip_id
        WHERE ca1.species_id=?
          AND EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              WHERE ca2.clip_id=Clips.id AND ca2.species_id != ?
          )
    """, (species_id, species_id))
    cohort_clips = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not cohort_clips:
        print("⚠️ No cohort clips found for this species.")
        return
    print(f"📂 Found {len(cohort_clips)} cohort clips.")

    num = input("🔢 Number of clips to test (Enter for all): ").strip()
    num = int(num) if num else len(cohort_clips)
    clips_to_test = random.sample(cohort_clips, min(num, len(cohort_clips)))
    print(f"🧪 Running inference on {len(clips_to_test)} cohort clips...")

    for clip_file in tqdm(clips_to_test, desc="🔍 Inference"):
        clip_path = os.path.join(DATA_DIR, clip_file)
        if not os.path.exists(clip_path):
            print(f"⚠️ Missing clip: {clip_file}, skipping.")
            continue

        audio = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)
        audio = standardize_duration(audio)
        spec_path = 'temp.png'
        generate_mel_spectrogram(audio, spec_path)

        img = tf.keras.preprocessing.image.load_img(spec_path, target_size=(224, 224))
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0

        preds = model.predict(img_array, verbose=0)
        pred_class = np.argmax(preds[0])
        conf = np.max(preds[0])
        pred_name = class_names[pred_class] if pred_class < len(class_names) else f"Unknown({pred_class})"

        print(f"\n🎧 {clip_file} → Predicted class: {pred_name} | Confidence: {conf:.2%}")
        print("📊 Class probabilities:")
        for i, prob in enumerate(preds[0]):
            class_name = class_names[i] if i < len(class_names) else f"Unknown({i})"
            print(f"    {class_name}: {prob:.2%}")

        os.remove(spec_path)

    print("\n✅ Cohort inference complete.")

if __name__ == "__main__":
    main()
