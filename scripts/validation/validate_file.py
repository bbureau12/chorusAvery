import os
import random
import tensorflow as tf
import numpy as np
import sys

# Project paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

DATA_DIR = './recordings/training_data'
MODEL_DIR = './models/complete'
IMAGE_SIZE = (224, 224)

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

    # === Load model & get class names
    model = tf.keras.models.load_model(model_path)
    class_names = getattr(model, 'class_names', ['0', '1'])
    print(f"🔎 Loaded model with class names: {class_names}")

    # === Get direct folder path for class 13
    slug = input("🔎 Enter species slug (e.g., american_toad): ").strip().lower()
    folder13 = os.path.join('./recordings/model', slug, 'test', '13')
    if not os.path.exists(folder13):
        print(f"❌ Folder does not exist: {folder13}")
        return

    all_images = [f for f in os.listdir(folder13) if f.lower().endswith('.png')]
    if not all_images:
        print(f"⚠️ No images found in: {folder13}")
        return

    print(f"📂 Found {len(all_images)} images in folder 13.")

    num = input("🔢 Number of images to test (Enter for all): ").strip()
    num = int(num) if num else len(all_images)
    clips_to_test = random.sample(all_images, min(num, len(all_images)))
    print(f"🧪 Running inference on {len(clips_to_test)} images...")

    for img_file in clips_to_test:
        img_path = os.path.join(folder13, img_file)
        if not os.path.exists(img_path):
            print(f"⚠️ Missing image: {img_file}, skipping.")
            continue

        img = tf.keras.preprocessing.image.load_img(img_path, target_size=IMAGE_SIZE)
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0

        preds = model.predict(img_array, verbose=0)
        pred_class = np.argmax(preds[0])
        conf = np.max(preds[0])
        pred_name = class_names[pred_class] if pred_class < len(class_names) else f"Unknown({pred_class})"

        print(f"\n🖼️ {img_file} → Predicted class: {pred_name} | Confidence: {conf:.2%}")
        print("📊 Class probabilities:")
        for i, prob in enumerate(preds[0]):
            class_name = class_names[i] if i < len(class_names) else f"Unknown({i})"
            print(f"    {class_name}: {prob:.2%}")

    print("\n✅ Folder-based inference complete.")

if __name__ == "__main__":
    main()
