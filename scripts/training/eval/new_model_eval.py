import os
import random
import numpy as np
import tensorflow as tf

IMAGE_SIZE = (224, 224)
MODELS_DIR = "./models"
RECORDINGS_ROOT = "./recordings/model"

def list_models():
    keras_files = [f for f in os.listdir(MODELS_DIR) if f.endswith('.keras')]
    if not keras_files:
        print("❌ No .keras models found!")
        exit(1)
    print("\n📦 Available models:")
    for idx, fname in enumerate(keras_files):
        print(f" {idx+1}. {fname}")
    return keras_files

def select_model(keras_files):
    sel = int(input("Select model number: ")) - 1
    selected_model = keras_files[sel]
    model_path = os.path.join(MODELS_DIR, selected_model)
    model_basename = selected_model.split('_v')[0]  # get base name before version
    return model_path, model_basename

def sample_images(data_root, sample_size=100):
    pos_images, neg_images = [], []
    for class_name in os.listdir(data_root):
        class_dir = os.path.join(data_root, class_name)
        if not os.path.isdir(class_dir):
            continue
        images = [os.path.join(class_dir, f) for f in sorted(os.listdir(class_dir)) if f.endswith('.png')]
        if class_name == "0":
            neg_images.extend(images)
        else:
            pos_images.extend(images)
    sampled_pos = random.sample(pos_images, min(len(pos_images), sample_size))
    sampled_neg = random.sample(neg_images, min(len(neg_images), sample_size))
    return sampled_pos, sampled_neg

def run_inference(model, images, expected_label):
    correct, total = 0, 0
    for img_path in images:
        img = tf.keras.utils.load_img(img_path, target_size=IMAGE_SIZE, color_mode='rgb')
        img_array = tf.keras.utils.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        preds = model.predict(img_array, verbose=0)
        pred_idx = int(np.argmax(preds[0]))
        confidence = float(np.max(preds[0]))
        pred_class = class_names[pred_idx] if pred_idx < len(class_names) else f"Unknown({pred_idx})"
        is_correct = (pred_class == expected_label)
        print(f"[{confidence:.2%}] {os.path.basename(img_path)} → Predicted: {pred_class} | Expected: {expected_label} | {'✅ Correct' if is_correct else '❌ Incorrect'}")
        if is_correct:
            correct += 1
        total += 1
    return correct, total

if __name__ == "__main__":
    keras_files = list_models()
    model_path, model_basename = select_model(keras_files)
    data_dir = os.path.join(RECORDINGS_ROOT, model_basename, 'train')
    if not os.path.exists(data_dir):
        print(f"❌ Could not find train folder at {data_dir}")
        exit(1)
    model = tf.keras.models.load_model(model_path)
    class_names = model.output_names if hasattr(model, 'output_names') else ["negative_0", f"{model_basename}_species_id"]

    pos_images, neg_images = sample_images(data_dir, sample_size=100)
    print(f"\n🧪 Running inference on {len(pos_images)} positive samples...")
    correct_pos, total_pos = run_inference(model, pos_images, expected_label=f"{model_basename}_species_id")
    print(f"\n✅ Positive Summary: {correct_pos}/{total_pos} correct → Accuracy: {correct_pos/total_pos:.2%}")

    print(f"\n🧪 Running inference on {len(neg_images)} negative samples...")
    correct_neg, total_neg = run_inference(model, neg_images, expected_label="negative_0")
    print(f"\n✅ Negative Summary: {correct_neg}/{total_neg} correct → Accuracy: {correct_neg/total_neg:.2%}")
