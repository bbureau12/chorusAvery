# import os
# import shutil
# import random

# # === CONFIG ===
# base_dir = r"D:\Projects\ChorusAvery\chorusAvery\recordings\model\human_mechanical\0"
# full_dir = os.path.join(base_dir, "full")
# train_dir = os.path.join(base_dir, "train")
# val_dir = os.path.join(base_dir, "validation")
# test_dir = os.path.join(base_dir, "test")

# # Create dirs if they don’t exist
# for d in [train_dir, val_dir, test_dir]:
#     os.makedirs(d, exist_ok=True)

# # === GET FILES ===
# all_pngs = [f for f in os.listdir(full_dir) if f.endswith(".png")]
# random.shuffle(all_pngs)

# # === SPLIT ===
# total = len(all_pngs)
# train_split = int(total * 0.8)
# val_split = int(total * 0.1)

# train_files = all_pngs[:train_split]
# val_files = all_pngs[train_split:train_split + val_split]
# test_files = all_pngs[train_split + val_split:]

# # === MOVE FILES ===
# def move_files(files, target_dir):
#     for f in files:
#         src = os.path.join(full_dir, f)
#         dst = os.path.join(target_dir, f)
#         shutil.move(src, dst)

# move_files(train_files, train_dir)
# move_files(val_files, val_dir)
# move_files(test_files, test_dir)

# print(f"✅ Done. Moved {len(train_files)} train, {len(val_files)} val, {len(test_files)} test.")

import os
import shutil

# === CONFIG ===
base_dir = r"D:\Projects\ChorusAvery\chorusAvery\recordings\model\noise_pollution"
old_root = os.path.join(base_dir, "1")
target_dirs = ["train", "test", "validation"]

for split in target_dirs:
    old_path = os.path.join(old_root, split)
    new_path = os.path.join(base_dir, split, "1")
    if not os.path.exists(old_path):
        print(f"⚠️ Skipping missing: {old_path}")
        continue
    os.makedirs(new_path, exist_ok=True)

    for f in os.listdir(old_path):
        src = os.path.join(old_path, f)
        dst = os.path.join(new_path, f)
        shutil.move(src, dst)
        print(f"✅ Moved: {src} -> {dst}")

# Optionally remove the now-empty "0" folder
try:
    os.rmdir(old_root)
    print(f"🗑️ Removed old folder: {old_root}")
except OSError:
    print(f"⚠️ Could not remove {old_root} (may not be empty)")

print("🎉 Structure fixed.")
