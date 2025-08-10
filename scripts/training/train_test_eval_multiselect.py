from datetime import datetime
import os
import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, roc_auc_score
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import seaborn as sns
from sklearn.metrics import roc_curve, auc
from sklearn.metrics import multilabel_confusion_matrix
import json

# === CONFIGURATION ===
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 60

# === Prompt user to load dataset ===
DATA_ROOT = './recordings/model'
available = [d for d in os.listdir(DATA_ROOT) if os.path.isdir(os.path.join(DATA_ROOT, d))]
print("\n📦 Available datasets:")
for i, name in enumerate(available):
    print(f" {i+1}. {name}")
sel = int(input("Select dataset: ")) - 1
slug = available[sel]
print(f"✅ Using: {slug}")

TRAIN_DIR = os.path.join(DATA_ROOT, slug, 'train')
LABEL_PATH = os.path.join(TRAIN_DIR, 'labels.csv')

# === Load labels.csv ===
df = pd.read_csv(LABEL_PATH)
class_names = [col for col in df.columns if col != 'filename']
print(f"🔤 Classes: {class_names}")

# === Build tf.data.Dataset ===
def load_image(filename, label):
    path = tf.strings.join([TRAIN_DIR, filename], separator=os.sep)
    img = tf.io.read_file(path)
    img = tf.image.decode_png(img, channels=3)
    img = tf.image.resize(img, IMAGE_SIZE)
    img = img / 255.0
    return img, label

filepaths = df['filename'].values
labels = df[class_names].values.astype('float32')
dataset = tf.data.Dataset.from_tensor_slices((filepaths, labels))
dataset = dataset.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
dataset = dataset.shuffle(1000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

# === Optional split for validation ===
total = len(filepaths)
val_size = int(0.2 * total)
# Recreate dataset so you can split before batching
full_dataset = tf.data.Dataset.from_tensor_slices((filepaths, labels))
full_dataset = full_dataset.shuffle(len(filepaths), seed=42)

val_data = full_dataset.take(val_size)
train_data = full_dataset.skip(val_size)

train_ds = train_data.map(load_image).batch(BATCH_SIZE).repeat().prefetch(tf.data.AUTOTUNE)
val_ds = val_data.map(load_image).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

steps_per_epoch = (len(filepaths) - val_size) // BATCH_SIZE

# === Build Model ===
model = models.Sequential([
    layers.Input(shape=(*IMAGE_SIZE, 3)),

    layers.Conv2D(32, 3, activation='relu', padding='same', kernel_regularizer=regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.MaxPooling2D(),

    layers.Conv2D(64, 3, activation='relu', padding='same', kernel_regularizer=regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.MaxPooling2D(),

    layers.Conv2D(128, 3, activation='relu', padding='same', kernel_regularizer=regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.MaxPooling2D(),

    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(len(class_names), activation='sigmoid')  # Multi-label!
])

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=[tf.keras.metrics.AUC(name='auc', multi_label=True)]
)

model.summary()

# === Callbacks ===
os.makedirs('./models', exist_ok=True)
model_path = f'./models/{slug}_multilabel.keras'
callbacks = [
    EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
    ModelCheckpoint(filepath=model_path, monitor='val_loss', save_best_only=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
]

# === Train ===
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks,
    steps_per_epoch=steps_per_epoch  # Required with .repeat()
)


# === Plot ===
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.legend()
plt.title("Loss")
plt.show()

# === Evaluate ===
print("\n🔍 Final evaluation on validation set:")
val_preds, val_true = [], []
for x, y in val_ds:
    val_true.append(y.numpy())
    val_preds.append(model.predict(x, verbose=0))
val_preds = np.vstack(val_preds)
val_true = np.vstack(val_true)

macro_auc = roc_auc_score(val_true, val_preds, average='macro')
print(f"Macro ROC AUC: {macro_auc:.4f}")

pred_labels = (val_preds > 0.5).astype(int)
print("\nClassification report:")
print(classification_report(val_true, pred_labels, target_names=class_names))

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_dir = os.path.join('./models/results', f'{slug}_{timestamp}')
os.makedirs(results_dir, exist_ok=True)
mcm = multilabel_confusion_matrix(val_true, pred_labels)
# === Plot and save confusion matrices per class
for idx, cm in enumerate(mcm):
    plt.figure()
    sns.heatmap(cm, annot=True, fmt="d", cmap="Purples", xticklabels=['No', 'Yes'], yticklabels=['No', 'Yes'])
    plt.title(f"Confusion Matrix: {class_names[idx]}")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, f'confusion_{class_names[idx]}.png'))
    plt.close()

# === Plot ROC curves for each class
plt.figure(figsize=(10, 7))
for i, name in enumerate(class_names):
    fpr, tpr, _ = roc_curve(val_true[:, i], val_preds[:, i])
    roc_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f"{name} (AUC={roc_auc:.2f})")
plt.plot([0, 1], [0, 1], 'k--', label="Chance")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curves (Validation Set)")
plt.legend(loc="lower right")
plt.tight_layout()
plt.savefig(os.path.join(results_dir, "roc_curves.png"))
plt.close()

print("📊 Plots saved (confusion matrices + ROC curves).")
report = classification_report(val_true, pred_labels, target_names=class_names, output_dict=True)
with open(os.path.join(results_dir, 'classification_report.json'), 'w') as f:
    json.dump(report, f, indent=2)

# Save predictions and ground truth for later analysis
np.save(os.path.join(results_dir, 'pred_probs.npy'), val_preds)
np.save(os.path.join(results_dir, 'true_labels.npy'), val_true)