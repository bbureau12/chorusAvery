import os
import random

NEGATIVE_VAL_DIR = './training/species_classification/val/negative'
TARGET_COUNT = 648

# Get all .png files
all_pngs = [f for f in os.listdir(NEGATIVE_VAL_DIR) if f.endswith('.png')]
current_count = len(all_pngs)

print(f"🧾 Found {current_count} negative validation images.")

if current_count <= TARGET_COUNT:
    print("✅ No trimming needed.")
else:
    # Randomly choose which ones to KEEP
    keep = set(random.sample(all_pngs, TARGET_COUNT))

    # Delete the rest
    for f in all_pngs:
        if f not in keep:
            os.remove(os.path.join(NEGATIVE_VAL_DIR, f))

    print(f"🗑️ Removed {current_count - TARGET_COUNT} images.")
    print(f"✅ Trimmed to {TARGET_COUNT} negative validation images.")