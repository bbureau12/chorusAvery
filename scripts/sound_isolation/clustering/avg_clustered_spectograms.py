import os
import numpy as np
from PIL import Image
from collections import defaultdict

# === CONFIG ===
SPECTROGRAM_DIR = './training/species/1/final/train/solo'
CLUSTER_LABEL_FILE = 'cluster_labels.txt'
OUTPUT_DIR = './cluster_fingerprints'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Load cluster assignments
cluster_map = defaultdict(list)
with open(CLUSTER_LABEL_FILE, 'r') as f:
    for line in f:
        fname, cluster = line.strip().split(',')
        cluster_map[int(cluster)].append(fname)

# === Average spectrograms per cluster
for cluster_id, files in cluster_map.items():
    print(f"🧮 Averaging cluster {cluster_id} ({len(files)} images)")
    imgs = []

    for fname in files:
        path = os.path.join(SPECTROGRAM_DIR, fname)
        img = Image.open(path).convert('L').resize((465, 465))  # grayscale
        imgs.append(np.array(img, dtype=np.float32))

    avg_img = np.mean(imgs, axis=0)
    avg_img = np.clip(avg_img, 0, 255).astype(np.uint8)
    output_path = os.path.join(OUTPUT_DIR, f'cluster_{cluster_id}.png')
    Image.fromarray(avg_img).save(output_path)

print(f"\n✅ Cluster fingerprints saved to: {OUTPUT_DIR}")
