
import os
import json
import sqlite3
import random
import sys
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import tensorflow as tf
from pydub import AudioSegment
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from utils.generate_spectogram import generate_mel_spectrogram

class MixedSpeciesEvaluator:
    def __init__(self, db_path, results_root, model_slug, species_name):
        self.db_path = db_path
        self.results_root = results_root
        self.model_slug = model_slug
        self.species_name = species_name
        self.model_dir = os.path.join(results_root, model_slug)
        self.species_id = self._load_species_id()
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.model = None

    def _load_species_id(self):
        summary_path = os.path.join(self.model_dir, 'results_summary.json')
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        ids = [int(k) for k in summary.get('class_names', []) if int(k) != 0]
        if not ids:
            raise ValueError("No non-zero species ID found in results_summary.json")
        return ids[0]

    def get_clip_paths(self):
        self.cursor.execute("""
        SELECT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca1 ON Clips.id = ca1.clip_id
        WHERE ca1.species_id = ?
          AND EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              WHERE ca2.clip_id = ca1.clip_id
                AND ca2.species_id != ?
          )
        """, (self.species_id, self.species_id))
        mixed_clips = [row[0] for row in self.cursor.fetchall()]
        if len(mixed_clips) < 10:
            raise ValueError("Not enough mixed-species clips (need at least 10)")

        self.cursor.execute("""
        SELECT Clips.clip_path FROM Clips
        JOIN ClipAnnotations ca1 ON Clips.id = ca1.clip_id
        WHERE ca1.species_id = ?
          AND NOT EXISTS (
              SELECT 1 FROM ClipAnnotations ca2
              WHERE ca2.clip_id = ca1.clip_id
                AND ca2.species_id != ?
          )
        """, (self.species_id, self.species_id))
        solo_clips = [row[0] for row in self.cursor.fetchall()]
        solo_sample = random.sample(solo_clips, len(mixed_clips) // 2)
        return mixed_clips, solo_sample

    def create_spectrograms(self, clip_paths, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for clip_file in clip_paths:
            full_path = os.path.join("./recordings/training_data", clip_file)
            output_path = os.path.join(output_dir, os.path.basename(clip_file).replace('.wav', '.png'))
            audio = AudioSegment.from_file(full_path).set_channels(1).set_frame_rate(16000)
            generate_mel_spectrogram(audio, output_path)
            paths.append(output_path)
        return paths

    def load_model(self):
        model_path = os.path.join('./models', f"{self.model_slug}.keras")
        self.model = load_model(model_path)
        print(f"✅ Loaded model: {model_path}")

    def infer_clipset(self, image_paths, label_index):
        y_true, y_pred, confidences = [], [], []
        for path in image_paths:
            try:
                img = load_img(path, target_size=(224, 224), color_mode='rgb')
                img_array = img_to_array(img)
                img_array = np.expand_dims(img_array, axis=0)
                preds = self.model.predict(img_array, verbose=0)
                pred_class = np.argmax(preds[0])
                confidence = float(np.max(preds[0]))
                y_true.append(label_index)
                y_pred.append(pred_class)
                confidences.append((path, pred_class, confidence))
            except Exception as e:
                print(f"⚠️ Error processing {path}: {e}")
        return y_true, y_pred, confidences

    def plot_confusion(self, true_labels, pred_labels, label_names, title, out_path):
        cm = confusion_matrix(true_labels, pred_labels)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_names)
        disp.plot(cmap='Purples', xticks_rotation=45)
        plt.title(title)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path)
        plt.close()

    def log_outliers(self, confidences, label_index, class_names, out_path):
        outliers = [
            (path, class_names[pred], conf)
            for path, pred, conf in confidences
            if pred != label_index
        ]
        with open(out_path, 'w') as f:
            for path, pred_class, conf in outliers:
                f.write(f"{path}, Predicted: {pred_class}, Confidence: {conf:.2%}\n")
        print(f"📄 Logged {len(outliers)} outliers to {out_path}")

    @staticmethod
    def select_model_slug_from_results(results_dir="./models/results"):
        candidates = []
        for folder in sorted(os.listdir(results_dir)):
            json_path = os.path.join(results_dir, folder, "results_summary.json")
            if os.path.isfile(json_path):
                try:
                    with open(json_path, "r") as f:
                        meta = json.load(f)
                    species = meta.get("species", "Unknown")
                    class_ids = meta.get("class_names", [])
                    species_id = next((int(cid) for cid in class_ids if cid != "0"), None)
                    candidates.append((folder, species, species_id))
                except Exception as e:
                    print(f"⚠️ Failed to parse {json_path}: {e}")

        if not candidates:
            raise RuntimeError("No valid model summaries found in results folder.")

        print("\n📦 Available models:")
        for idx, (slug, species, sid) in enumerate(candidates):
            print(f" {idx+1}. {slug} → {species} (ID: {sid})")

        sel = int(input("🔢 Select a model number: ")) - 1
        selected_slug, species_name, species_id = candidates[sel]
        return selected_slug, species_name, species_id
