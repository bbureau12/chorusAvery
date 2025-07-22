import os
import sys
from tensorflow.keras.models import load_model
from tensorflow.keras import Model, Input
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt
import numpy as np
import cv2

import tensorflow as tf
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from utils.load_model import list_models, choose_model, extract_species_id
from utils.grad_cam import compute_gradcam, overlay_gradcam
import os
import random
import sqlite3
from pydub import AudioSegment
from utils.generate_spectogram import generate_mel_spectrogram
from utils.grad_cam import compute_gradcam  # your existing method

def load_solo_clip_for_species(db_path, species_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Clips.clip_path
        FROM Clips
        JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
        WHERE ClipAnnotations.species_id = ?
        GROUP BY Clips.id
        HAVING COUNT(DISTINCT ClipAnnotations.species_id) = 1
    """, (species_id,))
    rows = cursor.fetchall()
    if not rows:
        raise ValueError("No solo clips found for this species.")
    return os.path.join("./recordings/training_data", random.choice(rows)[0])

def main():
    results_root = "./models"
    models_root = "./"
    db_path = "./db/chorusAvery.db"

    models = list_models(results_root)
    chosen = choose_model(models)
    print(f"✅ Selected: {chosen}")

    model_path = os.path.join(models_root, f"{chosen}.keras")
    results_path = os.path.join(results_root, chosen)
    species_id = extract_species_id(results_path)

    # Load model
    model = load_model(results_path)

    # Load example clip
    clip_path = load_solo_clip_for_species(db_path, species_id)
    audio = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)

    # Create temporary spectrogram
    spectro_path = "./temp_example.png"
    generate_mel_spectrogram(audio, spectro_path)

    # Load and preprocess spectrogram as image
    img = image.load_img(spectro_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # shape (1, 224, 224, 3)
    loaded_model = load_model(results_path)

    # 🔁 Create new input
    inputs = Input(shape=(224, 224, 3), name="gradcam_input")

    # 🔀 Call the model to get traced output
    outputs = loaded_model(inputs)

    # 🎯 Wrap in new functional model (safe)
    model = Model(inputs=inputs, outputs=outputs, name="gradcam_model")

    # ✅ Model now has input/output
    inspect_model(model)
    # 🔑 Call it ONCE to activate model.input and model.output
    #model(img_array, training=False)

    # Proceed as-is
    heatmap = compute_gradcam(model, img_array, 1)

    result = overlay_gradcam(heatmap, img_array)

    # Save result
    cv2.imwrite("./gradcam_result.png", result)
    print("✅ Grad-CAM image saved to gradcam_result.png")

def inspect_model(model, indent=0):
    spacer = "  " * indent
    print(f"{spacer}- Model type: {type(model)}")
    
    # Check if it's a Sequential or Functional model
    if hasattr(model, 'layers'):
        print(f"{spacer}- Layers ({len(model.layers)}):")
        for i, layer in enumerate(model.layers):
            print(f"{spacer}  [{i}] {layer.name} ({type(layer)})")
            # Recursively inspect nested models
            if isinstance(layer, tf.keras.Model):
                inspect_model(layer, indent + 2)
    
    # Check if input/output tensors exist
    try:
        print(f"{spacer}- Input: {model.input}")
    except Exception as e:
        print(f"{spacer}- Input: ❌ {e}")

    try:
        print(f"{spacer}- Output: {model.output}")
    except Exception as e:
        print(f"{spacer}- Output: ❌ {e}")

if __name__ == "__main__":
    main()
