import os
import random
import sys
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc as roc_auc
import seaborn as sns
import itertools
import shutil
from datetime import datetime
import json 

import os
import json
# === Import project utilities
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from utils.trainer_spec_writer import write_trainer_specs

# === SETTINGS ===
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 20

# === 1️⃣ Prompt for dataset ===
model_root = './recordings/model'
available_species = [
    d for d in os.listdir(model_root) if os.path.isdir(os.path.join(model_root, d))
]

if not available_species:
    raise RuntimeError("❌ No species folders found under ./recordings/model/")

print("\n📦 Available species datasets:")
for idx, sp in enumerate(available_species):
    print(f" {idx+1}. {sp}")
sel = int(input("Select dataset number: ")) - 1
species_name = available_species[sel]
species_dir = os.path.join(model_root, species_name)
print(f"✅ Using dataset: {species_name}")

# === 2️⃣ Get species ID ===
train_path = os.path.join(model_root, species_name, 'train')
train_subdirs = sorted([
    d for d in os.listdir(train_path)
    if os.path.isdir(os.path.join(train_path, d))
])

# Prefer numeric species IDs if available
species_ids = [d for d in train_subdirs if d.isdigit() and d != '0']

if species_ids:
    # Binary classification using numeric species ID
    species_id = species_ids[0]
    class_names = ['negative_0', f'species_{species_id}']
    print(f"✅ Detected numeric species ID: {species_id}")
else:
    # Multi-class setup using folder names
    class_names = train_subdirs
    print(f"✅ Using folder names as class labels: {class_names}")

# === 3️⃣ Find next model version ===
existing_models = [
    f for f in os.listdir('./models') if f.startswith(f"{species_name}_v") and f.endswith('.keras')
]
versions = [
    int(f.split('_v')[-1].split('.')[0]) for f in existing_models if f.split('_v')[-1].split('.')[0].isdigit()
]
next_version = max(versions, default=0) + 1

model_basename = f"{species_name}_v{next_version}"
model_filename = f"{model_basename}.keras"
MODEL_SAVE_PATH = os.path.join('./models', model_filename)
BEST_MODEL_PATH = os.path.join('./models', f"{model_basename}_best.keras")
DATA_DIR = os.path.join('./recordings/model', species_name)

# === 4️⃣ Prepare results dir ===
results_dir = os.path.join('./models/results', model_basename)
os.makedirs(results_dir, exist_ok=True)

print(f"📁 Model will be saved as: {model_filename}")
print(f"📂 Results will be saved in: {results_dir}")

# === 5️⃣ Create class names including species_id ===
# class_names = [
#     f"{species_name}_{species_id}" if lbl == str(species_id) else f"negative_0"
#     for lbl in ['0', species_id]
# ]
# print(f"✅ Class names set to: {class_names}")

# === Ensure model directory exists
os.makedirs('./models', exist_ok=True)

AUTOTUNE = tf.data.AUTOTUNE

# === Load datasets
train_ds = tf.keras.preprocessing.image_dataset_from_directory(
    os.path.join(DATA_DIR, 'train'),
    label_mode='categorical',
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE
)

val_ds = tf.keras.preprocessing.image_dataset_from_directory(
    os.path.join(DATA_DIR, 'validation'),
    label_mode='categorical',
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False
)

test_ds = tf.keras.preprocessing.image_dataset_from_directory(
    os.path.join(DATA_DIR, 'test'),
    label_mode='categorical',
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False
)

class_names = train_ds.class_names
print(f"Class names: {class_names}")

# === Optional joint validation set
joint_root = os.path.join(DATA_DIR, 'validation_joint')
if os.path.exists(joint_root) and any(os.scandir(joint_root)):
    joint_ds = tf.keras.preprocessing.image_dataset_from_directory(
        joint_root,
        label_mode='categorical',
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=False
    )
    joint_ds = joint_ds.prefetch(buffer_size=AUTOTUNE)
    has_joint = True
    print("✅ Loaded joint validation dataset.")
else:
    joint_ds, has_joint = None, False
    print("ℹ️ No joint validation dataset found; skipping joint evaluation.")

train_ds, val_ds, test_ds = [ds.prefetch(AUTOTUNE) for ds in [train_ds, val_ds, test_ds]]

# === Build model
model = models.Sequential([
    layers.Rescaling(1./255, input_shape=(224, 224, 3)),
    layers.Conv2D(32, 3, activation='relu', kernel_regularizer=regularizers.l2(0.002)),
    layers.MaxPooling2D(),
    layers.Dropout(0.25),
    layers.Conv2D(64, 3, activation='relu', kernel_regularizer=regularizers.l2(0.002)),
    layers.MaxPooling2D(),
    layers.Conv2D(128, 3, activation='relu', kernel_regularizer=regularizers.l2(0.002)),
    layers.MaxPooling2D(),
    layers.Conv2D(128, 3, activation='relu'),
    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.4),
    layers.Dense(64, activation='relu'),
    layers.Dense(len(class_names), activation='softmax')
])
# model = models.Sequential([
#     layers.Rescaling(1./255, input_shape=(224, 224, 3)),
    
#     layers.Conv2D(32, 3, activation='relu', kernel_regularizer=regularizers.l2(0.001)),
#     layers.BatchNormalization(),
#     layers.MaxPooling2D(),
#     layers.Dropout(0.25),
    
#     layers.Conv2D(64, 3, activation='relu', kernel_regularizer=regularizers.l2(0.001)),
#     layers.BatchNormalization(),
#     layers.MaxPooling2D(),
    
#     layers.Conv2D(128, 3, activation='relu', kernel_regularizer=regularizers.l2(0.001)),
#     layers.BatchNormalization(),
#     layers.MaxPooling2D(),
    
#     layers.Conv2D(256, 3, activation='relu'),
#     layers.BatchNormalization(),
    
#     layers.GlobalAveragePooling2D(),
#     layers.Dropout(0.5),
#     layers.Dense(128, activation='relu'),
#     layers.Dense(len(class_names), activation='softmax')
# ])


model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
)

model.summary()

# === Callbacks
callbacks = [
    EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
    ModelCheckpoint(filepath=BEST_MODEL_PATH, monitor='val_loss', save_best_only=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, min_lr=1e-6)
]

# === Train model
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)

model.save(MODEL_SAVE_PATH)

# === Best epoch info
best_epoch = np.argmin(history.history['val_loss'])
best_val = np.min(history.history['val_loss'])
print(f"Best epoch: {best_epoch + 1} with val_loss: {best_val:.4f}")

plt.plot(history.history['accuracy'], label='Train Acc')
plt.plot(history.history['val_accuracy'], label='Val Acc')
plt.legend()
plt.title("Model Accuracy")
plt.savefig(os.path.join(results_dir, 'accuracy.png'))
plt.show()

def evaluate_and_report(ds, ds_name):
    print(f"\n🔍 Evaluating on {ds_name} set...")
    loss, acc, auc_val = model.evaluate(ds)
    print(f"✅ {ds_name} Accuracy: {acc:.4%} | AUC: {auc_val:.4f} | Loss: {loss:.4f}")

    y_true, y_pred, y_prob = [], [], []
    for images, labels in ds:
        preds = model.predict(images)
        y_true.extend(np.argmax(labels.numpy(), axis=1))
        y_pred.extend(np.argmax(preds, axis=1))
        y_prob.extend(preds)

    y_true, y_pred, y_prob = np.array(y_true), np.array(y_pred), np.array(y_prob)
    print(f"\n📊 {ds_name} Classification Report:")
    print(classification_report(y_true, y_pred, target_names=class_names))

    cm = confusion_matrix(y_true, y_pred)
    plot_confusion_matrix(cm, class_names, f"Confusion Matrix ({ds_name})")
    plot_roc_curves(y_true, y_prob, class_names, ds_name)
    return y_true, y_pred

def plot_confusion_matrix(cm, classes, title='Confusion Matrix'):
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Purples", xticklabels=classes, yticklabels=classes)
    plt.title(title)
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'confusion_matrix.png'))
    plt.show()

def plot_roc_curves(y_true, y_prob, classes, ds_name):
    plt.figure(figsize=(8, 6))
    for i, class_name in enumerate(classes):
        fpr, tpr, _ = roc_curve((y_true == i).astype(int), y_prob[:, i])
        roc_auc_val = roc_auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{class_name} (AUC={roc_auc_val:.2f})")
    plt.plot([0, 1], [0, 1], 'k--', label="Chance")
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f"ROC Curves ({ds_name})")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'roc.png'))
    plt.show()

# === Evaluate on TEST set
y_true_test, y_pred_test = evaluate_and_report(test_ds, "Test")

# === Write result!
write_trainer_specs(IMAGE_SIZE, BATCH_SIZE, EPOCHS, history, class_names, best_epoch, best_val, results_dir, species_name)
# === Misclassification Tracker on TEST set
print("\n🔍 Scanning TEST set for misclassified images...")
test_root = os.path.join(DATA_DIR, 'test')
image_paths = []
for class_name in class_names:
    class_dir = os.path.join(test_root, class_name)
    for fname in sorted(os.listdir(class_dir)):
        if fname.endswith('.png'):
            image_paths.append((os.path.join(class_dir, fname), class_name))

if len(image_paths) != len(y_true_test):
    print(f"⚠️ Mismatch: {len(image_paths)} images vs {len(y_true_test)} labels — skipping misclassification export.")
else:
    misclassified = []
    for idx, (filepath, actual_class) in enumerate(image_paths):
        predicted_class = class_names[y_pred_test[idx]]
        # Load and preprocess image properly:
        img = tf.keras.utils.load_img(filepath, target_size=IMAGE_SIZE, color_mode='rgb')
        img_array = tf.keras.utils.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)  # add batch dimension

        # Run prediction
        confidence = float(np.max(model.predict(img_array, verbose=0)))


        if predicted_class != actual_class:
            misclassified.append({
                'filename': filepath,
                'actual': actual_class,
                'predicted': predicted_class,
                'confidence': confidence
            })

    print(f"🚩 Total misclassified in TEST: {len(misclassified)}")
    for entry in misclassified:
        print(f"[{entry['confidence']:.2%}] {entry['filename']} → Predicted: {entry['predicted']}, Actual: {entry['actual']}")

    if misclassified:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        EXPORT_DIR = f'./misclassified/miss_test_{timestamp}'
        os.makedirs(EXPORT_DIR, exist_ok=True)

        for entry in misclassified:
            basename = os.path.basename(entry['filename'])
            dst_name = f"{entry['actual']}_as_{entry['predicted']}_{int(entry['confidence'] * 100)}pct_{basename}"
            shutil.copy(entry['filename'], os.path.join(EXPORT_DIR, dst_name))

        print(f"Copied misclassified TEST images to: {EXPORT_DIR}")
    else:
        print("✅ No misclassified images to export.")

# === Evaluate on JOINT VALIDATION set (if available)
if has_joint:
    evaluate_and_report(joint_ds, "Joint Validation")

# === Evaluate on JOINT VALIDATION set (if available)
if has_joint:
    evaluate_and_report(joint_ds, "Joint Validation")

# === Evaluate on KNOWN POSITIVES (any test folder ≠ '0')
print("\n🧪 Running inference on all known positives (excluding class '0')...")

total, correct = 0, 0
for pos_class_name in [c for c in class_names if c != '0']:
    pos_dir = os.path.join(DATA_DIR, 'test', pos_class_name)
    if not os.path.exists(pos_dir) or not any(os.scandir(pos_dir)):
        print(f"⚠️ No images found in: {pos_dir}")
        continue

    pos_images = [f for f in sorted(os.listdir(pos_dir)) if f.lower().endswith('.png')]
    if not pos_images:
        print(f"⚠️ No .png files found in {pos_dir}.")
        continue

    for fname in pos_images:
        img_path = os.path.join(pos_dir, fname)
        img = tf.keras.utils.load_img(img_path, target_size=IMAGE_SIZE, color_mode='rgb')
        img_array = tf.keras.utils.img_to_array(img)  # Convert to NumPy
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
        
        preds = model.predict(img_array, verbose=0)
        pred_index = int(np.argmax(preds[0]))
        confidence = float(np.max(preds[0]))
        pred_class = class_names[pred_index] if pred_index < len(class_names) else f"Unknown({pred_index})"

        is_correct = pred_class == pos_class_name
        if is_correct:
            correct += 1
        total += 1

        print(f"[{confidence:.2%}] {fname} → Predicted: {pred_class} | Expected: {pos_class_name} | {'✅ Correct' if is_correct else '❌ Incorrect'}")

if total > 0:
    print(f"\n🔎 Known Positives Summary: {correct}/{total} correct → Accuracy: {correct/total:.2%}")
else:
    print("⚠️ No known positive images found across test folders.")
# === Evaluate on KNOWN POSITIVES (any test folder = '0')
print("\n🧪 Running inference on a sample of negatives (class '0')...")

neg_dir = os.path.join(DATA_DIR, 'test', '0')
if not os.path.exists(neg_dir) or not any(os.scandir(neg_dir)):
    print(f"⚠️ No negatives found in: {neg_dir}")
else:
    neg_images = [f for f in sorted(os.listdir(neg_dir)) if f.lower().endswith('.png')]
    if not neg_images:
        print(f"⚠️ No .png files found in {neg_dir}.")
    else:
        sample_negatives = random.sample(neg_images, min(30, len(neg_images)))
        correct, total = 0, 0

        for fname in sample_negatives:
            img_path = os.path.join(neg_dir, fname)
            img = tf.keras.utils.load_img(img_path, target_size=IMAGE_SIZE, color_mode='rgb')
            img_array = tf.keras.utils.img_to_array(img)  # ⬅️ this was missing
            img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

            preds = model.predict(img_array, verbose=0)
            pred_index = int(np.argmax(preds[0]))
            confidence = float(np.max(preds[0]))
            pred_class = class_names[pred_index] if pred_index < len(class_names) else f"Unknown({pred_index})"

            is_correct = pred_class == "negative_0"
            if is_correct:
                correct += 1
            total += 1

            print(f"[{confidence:.2%}] {fname} → Predicted: {pred_class} | Expected: negative_0 | {'✅ Correct' if is_correct else '❌ Incorrect'}")

        print(f"\n🔎 Negatives Sample Summary: {correct}/{total} correct → Accuracy: {correct/total:.2%}")

