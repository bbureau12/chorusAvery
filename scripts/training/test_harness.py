import os
import random
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image

# === CONFIGURATION ===
MODEL_PATH = './models/species_1_classifier_v2.keras'
IMAGE_SIZE = (224, 224)
TEST_DIR = './training/species_classification/val'  # or 'train'

# === Load model (which includes Rescaling)
model = tf.keras.models.load_model(MODEL_PATH)

# === Use class names from the model directory (same order as training)
CLASS_NAMES = sorted(os.listdir(TEST_DIR))
print("Loaded class names:", CLASS_NAMES)

def run_inference(png_path):
    img = image.load_img(png_path, target_size=IMAGE_SIZE)
    img_array = image.img_to_array(img)  # <-- No manual normalization
    img_array = np.expand_dims(img_array, 0)

    predictions = model.predict(img_array, verbose=0)
    score = tf.nn.softmax(predictions[0])
    predicted_index = np.argmax(score)
    return CLASS_NAMES[predicted_index], float(np.max(score))

# === Batch evaluation (optional)
total = 0
correct = 0

print("\n🧪 Testing one random image from each class:")
for label in CLASS_NAMES:
    folder = os.path.join(TEST_DIR, label)
    png_files = [f for f in os.listdir(folder) if f.endswith('.png')]
    if not png_files:
        print(f"⚠️ No PNG files found in {folder}")
        continue

    chosen_files = random.sample(png_files, 5)
    for chosen_file in chosen_files:
        full_path = os.path.join(folder, chosen_file)

        predicted, confidence = run_inference(full_path)
        is_correct = predicted == label
        total += 1
        correct += int(is_correct)

        print(f"\n🖼️ {chosen_file} (actual: {label}) ➜ predicted: {predicted} ({confidence:.2%}) {'✅' if is_correct else '❌'}")

# === Accuracy Summary
accuracy = correct / total if total else 0
print(f"\n🔍 Accuracy on sampled images: {accuracy:.2%}")
