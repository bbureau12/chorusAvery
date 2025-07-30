# import os
# import numpy as np
# import tensorflow as tf
# import matplotlib.pyplot as plt
# from tensorflow.keras import layers, models
# from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
# from sklearn.metrics import confusion_matrix, classification_report
# import itertools
# import shutil
# from datetime import datetime

# # === SETTINGS ===
# IMAGE_SIZE = (224, 224)
# BATCH_SIZE = 32
# EPOCHS = 10
# DATA_DIR = './training/species_classification'
# MODEL_SAVE_PATH = './models/species_1_classifier_v2.keras'
# BEST_MODEL_PATH = './models/best_species_1_model_v2.keras'

# # === Ensure model directory exists
# os.makedirs('./models', exist_ok=True)

# # === Load datasets
# train_ds = tf.keras.preprocessing.image_dataset_from_directory(
#     os.path.join(DATA_DIR, 'train'),
#     label_mode='categorical',
#     image_size=IMAGE_SIZE,
#     batch_size=BATCH_SIZE
# )

# val_ds = tf.keras.preprocessing.image_dataset_from_directory(
#     os.path.join(DATA_DIR, 'val'),
#     label_mode='categorical',
#     image_size=IMAGE_SIZE,
#     batch_size=BATCH_SIZE,
#     shuffle=False
# )

# class_names = train_ds.class_names
# print("Class names:", class_names)

# AUTOTUNE = tf.data.AUTOTUNE
# train_ds = train_ds.prefetch(buffer_size=AUTOTUNE)
# val_ds = val_ds.prefetch(buffer_size=AUTOTUNE)

# # === Build model
# model = models.Sequential([
#     layers.Rescaling(1./255, input_shape=(224, 224, 3)),
#     layers.Conv2D(32, 3, activation='relu'),
#     layers.MaxPooling2D(),
#     layers.Conv2D(64, 3, activation='relu'),
#     layers.MaxPooling2D(),
#     layers.Conv2D(128, 3, activation='relu'),
#     layers.MaxPooling2D(),
#     layers.GlobalAveragePooling2D(),
#     layers.Dropout(0.3),
#     layers.Dense(64, activation='relu'),
#     layers.Dense(2, activation='softmax')
# ])

# model.compile(
#     optimizer='adam',
#     loss='categorical_crossentropy',
#     metrics=['accuracy']
# )

# model.summary()

# # === Callbacks
# callbacks = [
#     EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True),
#     ModelCheckpoint(filepath=BEST_MODEL_PATH, monitor='val_loss', save_best_only=True)
# ]

# # === Train model
# history = model.fit(
#     train_ds,
#     validation_data=val_ds,
#     epochs=EPOCHS,
#     callbacks=callbacks
# )

# # === Save final model
# model.save(MODEL_SAVE_PATH)

# # === Best epoch info
# best_epoch = np.argmin(history.history['val_loss'])
# best_val = np.min(history.history['val_loss'])
# print(f"Best epoch: {best_epoch+1} with val_loss: {best_val:.4f}")

# # === Plot accuracy
# plt.plot(history.history['accuracy'], label='Train Acc')
# plt.plot(history.history['val_accuracy'], label='Val Acc')
# plt.legend()
# plt.title("Model Accuracy")
# plt.show()

# # === Evaluation
# y_true = []
# y_pred = []

# for images, labels in val_ds:
#     preds = model.predict(images)
#     y_true.extend(np.argmax(labels.numpy(), axis=1))
#     y_pred.extend(np.argmax(preds, axis=1))

# y_true = np.array(y_true)
# y_pred = np.array(y_pred)

# # === Classification Report
# print("Classification Report:")
# print(classification_report(y_true, y_pred, target_names=class_names))

# # === Confusion Matrix

# def plot_confusion_matrix(cm, classes, title='Confusion Matrix'):
#     plt.figure(figsize=(6, 5))
#     plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Purples)
#     plt.title(title)
#     plt.colorbar()
#     tick_marks = np.arange(len(classes))
#     plt.xticks(tick_marks, classes, rotation=30)
#     plt.yticks(tick_marks, classes)

#     thresh = cm.max() / 2.0
#     for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
#         plt.text(j, i, format(cm[i, j], 'd'),
#                  horizontalalignment="center",
#                  color="white" if cm[i, j] > thresh else "black")

#     plt.ylabel('Actual')
#     plt.xlabel('Predicted')
#     plt.tight_layout()
#     plt.grid(False)
#     plt.show()

# cm = confusion_matrix(y_true, y_pred)
# plot_confusion_matrix(cm, class_names)

# print("\n\u2705 Training and evaluation complete.")

# # === Misclassification Tracker ===
# val_root = os.path.join(DATA_DIR, 'val')
# image_paths = []

# for class_name in class_names:
#     class_dir = os.path.join(val_root, class_name)
#     for fname in sorted(os.listdir(class_dir)):
#         if fname.endswith('.png'):
#             image_paths.append((os.path.join(class_dir, fname), class_name))

# # Recreate loader with batch_size=1
# val_loader = tf.keras.preprocessing.image_dataset_from_directory(
#     val_root,
#     label_mode='categorical',
#     image_size=IMAGE_SIZE,
#     batch_size=1,
#     shuffle=False
# )

# misclassified = []
# y_index = 0
# for batch, labels in val_loader:
#     preds = model.predict(batch)
#     pred_index = int(np.argmax(preds[0]))
#     true_index = int(np.argmax(labels.numpy()[0]))
#     confidence = float(np.max(preds[0]))

#     if pred_index != true_index:
#         filepath, actual_class = image_paths[y_index]
#         predicted_class = class_names[pred_index]

#         misclassified.append({
#             'filename': filepath,
#             'actual': actual_class,
#             'predicted': predicted_class,
#             'confidence': confidence
#         })

#     y_index += 1

# # === Output misclassified files
# print(f"Total misclassified: {len(misclassified)}\n")
# for entry in misclassified:
#     print(f"[{entry['confidence']:.2%}] {entry['filename']} → Predicted: {entry['predicted']}, Actual: {entry['actual']}")

# # === Copy to export folder with timestamp
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# EXPORT_DIR = f'./misclassified/miss_{timestamp}'
# os.makedirs(EXPORT_DIR, exist_ok=True)

# for entry in misclassified:
#     basename = os.path.basename(entry['filename'])
#     dst_name = f"{entry['actual']}_as_{entry['predicted']}_{int(entry['confidence'] * 100)}pct_{basename}"
#     shutil.copy(entry['filename'], os.path.join(EXPORT_DIR, dst_name))

# print(f"Copied misclassified images to: {EXPORT_DIR}")
