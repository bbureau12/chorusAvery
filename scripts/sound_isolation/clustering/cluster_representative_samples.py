import os
import numpy as np
from PIL import Image
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import shutil

# === CONFIG ===
SPECTROGRAM_DIR = './training/species/1/final/train/solo'
LABELS_FILE = 'cluster_labels.txt'
REPRESENTATIVE_COUNT = 5
OUTPUT_FOLDER = './representatives'
RESIZE_SHAPE = (224, 224)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Load image vectors and filenames
print("📥 Loading spectrograms...")
X = []
filenames = []

for fname in os.listdir(SPECTROGRAM_DIR):
    if fname.endswith('.png'):
        path = os.path.join(SPECTROGRAM_DIR, fname)
        img = Image.open(path).convert('L').resize(RESIZE_SHAPE)
        X.append(np.array(img).flatten())
        filenames.append(fname)

X = np.array(X)

# === Normalize and reduce
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

pca = PCA(n_components=50)
X_pca = pca.fit_transform(X_scaled)

# === Load cluster labels
print("📋 Loading cluster labels...")
cluster_map = {}
with open(LABELS_FILE, 'r') as f:
    for line in f:
        name, cluster = line.strip().split(',')
        cluster_map[name] = int(cluster)

# === Group filenames by cluster
cluster_groups = {}
for i, fname in enumerate(filenames):
    cluster_id = cluster_map.get(fname)
    if cluster_id is not None:
        cluster_groups.setdefault(cluster_id, []).append((i, fname))

# === Pick closest samples to centroid
print("🏆 Selecting representatives...")
kmeans = KMeans(n_clusters=len(cluster_groups), random_state=42).fit(X_pca)
centroids = kmeans.cluster_centers_

for cluster_id, members in cluster_groups.items():
    indices = [i for i, _ in members]
    distances = [np.linalg.norm(X_pca[i] - centroids[cluster_id]) for i in indices]
    sorted_indices = np.argsort(distances)[:REPRESENTATIVE_COUNT]

    output_dir = os.path.join(OUTPUT_FOLDER, f'cluster_{cluster_id}')
    os.makedirs(output_dir, exist_ok=True)

    for rank, idx in enumerate(sorted_indices):
        _, fname = members[idx]
        src_path = os.path.join(SPECTROGRAM_DIR, fname)
        dst_path = os.path.join(output_dir, f'rep_{rank+1}_{fname}')
        shutil.copy(src_path, dst_path)
        print(f"✅ Copied: {fname} → {dst_path}")

print("\n✅ All representative spectrograms saved.")
