import os

BASE_DIR = './training/species_classification'
SPLITS = ['train', 'val']

def count_images(split_path):
    counts = {}
    for class_name in os.listdir(split_path):
        class_dir = os.path.join(split_path, class_name)
        if os.path.isdir(class_dir):
            count = len([f for f in os.listdir(class_dir) if f.endswith('.png')])
            counts[class_name] = count
    return counts

print("📊 Dataset Image Counts:")
for split in SPLITS:
    split_path = os.path.join(BASE_DIR, split)
    counts = count_images(split_path)
    total = sum(counts.values())
    print(f"\n📁 {split.upper()} SET (Total: {total} images)")
    for label, count in counts.items():
        percent = (count / total) * 100 if total > 0 else 0
        print(f"  - {label}: {count} images ({percent:.2f}%)")

    # Optional: imbalance warning
    if len(counts) == 2:
        values = list(counts.values())
        ratio = max(values) / min(values) if min(values) > 0 else float('inf')
        if ratio > 1.5:
            print("⚠️  Warning: Class imbalance detected.")