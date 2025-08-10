import os
import sys
import argparse
import random
import sqlite3
import numpy as np
import cv2
import matplotlib.pyplot as plt
from pydub import AudioSegment
from tensorflow.keras.models import load_model
from tensorflow.keras import Model, Input
from tensorflow.keras.preprocessing import image

# Project setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.load_model import list_models, choose_model, extract_species_id, extract_results_folder
from utils.grad_cam import compute_gradcam, overlay_gradcam
from utils.generate_spectogram import generate_mel_spectrogram, load_spectrogram

DB_PATH = "./db/chorusAvery.db"
RECORDINGS_ROOT = "./recordings/training_data"

def fetch_unscored_species_clips(db_path, species_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Clips.id, Clips.clip_path
        FROM Clips
        JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
        WHERE ClipAnnotations.species_id = ?
          AND ClipAnnotations.relative_entity_volume IS NULL
    """, (species_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def fetch_mixed_species_clip(db_path, species_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Clips.id, Clips.clip_path
        FROM Clips
        JOIN ClipAnnotations ca2 ON Clips.id = ca2.clip_id
        GROUP BY Clips.id
        HAVING SUM(ca2.species_id = ?) > 0 AND COUNT(DISTINCT ca2.species_id) > 1
    """, (species_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        raise ValueError("No mixed-species clips found for this species.")
    return random.choice(rows)

def verify_species_presence(model, clip_path, target_class):
    audio = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)
    generate_mel_spectrogram(audio, "./temp_example.png")
    img = image.load_img("./temp_example.png", target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array, verbose=0)[0]
    return np.argmax(prediction) == target_class, audio, img_array

def estimate_species_volume_score(heatmap, audio):
    norm = (heatmap - np.min(heatmap)) / (np.max(heatmap) - np.min(heatmap) + 1e-8)
    mean_activation = np.mean(norm)
    if mean_activation < 1e-6:
        return 0.0
    estimated_dbfs = audio.dBFS + 10 * np.log10(mean_activation)
    min_dbfs, max_dbfs = -80.0, 0.0
    estimated_dbfs = np.clip(estimated_dbfs, min_dbfs, max_dbfs)
    max_volume = np.clip(audio.max_dBFS, min_dbfs, max_dbfs)
    norm_est = (estimated_dbfs - min_dbfs) / (max_dbfs - min_dbfs)
    norm_max = (max_volume - min_dbfs) / (max_dbfs - min_dbfs)
    score = norm_est / norm_max if norm_max > 0 else 0.0
    print(f"🔊 est: {estimated_dbfs:.2f} dBFS, max: {audio.max_dBFS:.2f} dBFS → score: {score:.3f}")
    return round(score, 3)

def update_db_score(clip_id, species_id, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ClipAnnotations
        SET relative_entity_volume = ?
        WHERE clip_id = ? AND species_id = ?
    """, (int(score * 1000), clip_id, species_id))
    conn.commit()
    conn.close()

def main(auto_approve):
    models = list_models("./models")
    chosen = choose_model(models)
    print(f"✅ Model selected: {chosen}")
    model_path = os.path.join("./", f"{chosen}.keras")
    results_path = os.path.join("./models", chosen)
    species_id = extract_species_id(results_path)

    model = load_model(results_path)
    # 🔁 Create new input
    inputs = Input(shape=(224, 224, 3), name="gradcam_input")

    # 🔀 Call the model to get traced output
    outputs = model(inputs)

    # 🎯 Wrap in new functional model (safe)
    model = Model(inputs=inputs, outputs=outputs, name="gradcam_model")



    all_clips = fetch_unscored_species_clips(DB_PATH, species_id)
    print(f"🔍 Found {len(all_clips)} mixed-species clips to analyze.")

    for clip_id, clip_rel_path in all_clips:
        clip_path = os.path.join(RECORDINGS_ROOT, clip_rel_path)

        if not os.path.isfile(clip_path):
            print(f"⚠️ Missing file: {clip_path}")
            continue

        verified, audio, img_array = verify_species_presence(model, clip_path, 1)
        if not verified:
            print(f"⏭️ Skipping: model did not detect species in {clip_rel_path}")
            continue

        heatmap = compute_gradcam(model, img_array, 1)
        score = estimate_species_volume_score(heatmap, audio)

        if not auto_approve:
            gradmap = overlay_gradcam(heatmap, img_array)
            cv2.imshow("Grad-CAM", gradmap)
            audio.export("temp_preview.wav", format="wav")
            os.system("start temp_preview.wav" if os.name == 'nt' else "afplay temp_preview.wav")

            confirm = input(f"{clip_rel_path}: Approve and save score {score:.3f}? (y/n): ").strip().lower()
            if confirm != 'y':
                print("⏭️ Skipped saving.")
                continue

        update_db_score(clip_id, species_id, score)
        print(f"✅ Saved score {score:.3f} for clip {clip_rel_path}")

    print("🎉 Processing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Auto approve scores without prompt")
    args = parser.parse_args()
    main(False)
