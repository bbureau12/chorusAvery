import os
import numpy as np
from PIL import Image
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# === CONFIG ===
SPECTROGRAM_DIR = './training/species/1/final/train/solo'
RESIZE_SHAPE = (224, 224)
OUTPUT_LABELS_FILE = 'cluster_labels.txt'
CLUSTER_RANGE = range(2, 10)

# === Load Spectrogram Images
def load_spectrograms(folder):
    specs, filenames = [], []
    for fname in os.listdir(folder):
        if fname.endswith('.png'):
            path = os.path.join(folder, fname)
            img = Image.open(path).convert('L').resize(RESIZE_SHAPE)
            specs.append(np.array(img).flatten())
            filenames.append(fname)
    return np.array(specs), filenames

print("📥 Loading spectrograms...")
X_raw, filenames = load_spectrograms(SPECTROGRAM_DIR)

# === Normalize + Reduce
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)

pca = PCA(n_components=50)
X_pca = pca.fit_transform(X_scaled)

# === Find Best k using Silhouette Score
print("🔍 Evaluating optimal cluster count...")
best_k, best_score = 0, -1
scores = []

for k in CLUSTER_RANGE:
    kmeans = KMeans(n_clusters=k, random_state=42).fit(X_pca)
    score = silhouette_score(X_pca, kmeans.labels_)
    scores.append(score)
    print(f"K={k} → Silhouette Score: {score:.4f}")
    if score > best_score:
        best_k, best_score = k, score

print(f"\n✅ Optimal k: {best_k} (Silhouette Score: {best_score:.4f})")

# === Final Clustering
kmeans = KMeans(n_clusters=best_k, random_state=42).fit(X_pca)
labels = kmeans.labels_

# === Save Labels
with open(OUTPUT_LABELS_FILE, 'w') as f:
    for fname, label in zip(filenames, labels):
        f.write(f"{fname},{label}\n")

print(f"\n📝 Cluster labels written to: {OUTPUT_LABELS_FILE}")

# === Optional: Plot Cluster Sample Counts
counts = np.bincount(labels)
for i, count in enumerate(counts):
    print(f"📂 Cluster {i}: {count} spectrograms")

plt.figure()
plt.plot(CLUSTER_RANGE, scores, marker='o')
plt.title("Silhouette Scores by Cluster Count")
plt.xlabel("Number of Clusters (k)")
plt.ylabel("Silhouette Score")
plt.grid(True)
plt.tight_layout()
plt.show()
