import os
import random
import sys

# === Import project utilities
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from utils.entityfinder import EntityFinder  # assuming your EntityFinder is saved here
from augmentation_generator import AugmentedClipGenerator  # assuming your AugmentedClipGenerator is saved here

def main():
    db_path = "./db/chorusAvery.db"
    models_root = "./recordings/model"

    # 1️⃣ Instantiate EntityFinder & prompt for species selection
    finder = EntityFinder(db_path)
    selected = finder.prompt_search(mode="species")
    finder.close()
    if not selected:
        print("🚫 No species selected, exiting.")
        return

    species_id, species_name = selected[0]  # use the first selected species
    print(f"\n🎯 Selected species: {species_name} (ID {species_id})")

    # 2️⃣ Verify species ID directory exists in each train/test/val split
    for split in ["train", "test", "validation"]:
        split_dirs = []
        # walk model directory
        for root, dirs, files in os.walk(models_root):
            if os.path.basename(root) == split:
                split_dirs.append(root)
        
        if not split_dirs:
            print(f"⚠️ No '{split}' directories found under {models_root}, skipping split.")
            continue

        found = False
        for split_dir in split_dirs:
            species_dir = os.path.join(split_dir, str(species_id))
            if os.path.isdir(species_dir):
                print(f"✅ Found species ID folder in {split_dir}: {species_dir}")
                found = True
            else:
                print(f"🚫 Species ID {species_id} not found in {split_dir}")

        if not found:
            print(f"🚨 Could not verify species ID {species_id} for split '{split}', exiting.")
            return

    # 3️⃣ Create one AugmentedClipGenerator instance to fetch files
    gen = AugmentedClipGenerator(db_path, output_dir="./temp")  # output_dir here is a placeholder
    pairs = gen.fetch_files(target_species_id=species_id)

    # 4️⃣ Split pairs into train/test/val (80/10/10 example)
    random.shuffle(pairs)
    total = len(pairs)
    train_end = int(total * 0.8)
    test_end = train_end + int(total * 0.1)
    train_pairs = pairs[:train_end]
    test_pairs = pairs[train_end:test_end]
    val_pairs = pairs[test_end:]

    # 5️⃣ Process each split separately
    for split_name, split_pairs in [("train", train_pairs), ("test", test_pairs), ("validation", val_pairs)]:
        normalized_species_name = species_name.strip().lower().replace(' ', '_')
        out_dir = os.path.join(models_root, normalized_species_name, split_name, str(species_id))
        os.makedirs(out_dir, exist_ok=True)
        split_gen = AugmentedClipGenerator(db_path, output_dir=out_dir)
        for species_file, non_species_file in split_pairs:
            split_gen.overlay_clips(species_file, non_species_file)
        split_gen.close()
        print(f"🏁 Finished split: {split_name} → {len(split_pairs)} overlays written to {out_dir}")


    print("\n✅ All done!")

if __name__ == "__main__":
    main()