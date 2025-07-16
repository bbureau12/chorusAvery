import os
import random
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from utils.entityfinder import EntityFinder
from scripts.augmentation.augmentation_generator import AugmentedClipGenerator

class SpeciesAugmentor:
    def __init__(self, db_path="./db/chorusAvery.db", models_root="./recordings/model"):
        self.db_path = db_path
        self.models_root = models_root

    def select_species(self, species_name=None, species_id=None):
        """
        Resolves species by CLI args or interactive prompt.
        """
        if species_name and species_id:
            print(f"✅ Using species from args: {species_name} (ID {species_id})")
            return species_id, species_name
        
        finder = EntityFinder(self.db_path)
        selected = finder.prompt_search(mode="species")
        finder.close()
        if not selected:
            print("🚫 No species selected, exiting.")
            return None, None
        return selected[0]  # returns (species_id, species_name)

    def verify_species_dirs(self, species_id):
        """
        Verifies the existence of species directories in train/val/test splits.
        """
        for split in ["train", "test", "validation"]:
            split_dirs = []
            for root, dirs, files in os.walk(self.models_root):
                if os.path.basename(root) == split:
                    split_dirs.append(root)

            if not split_dirs:
                print(f"⚠️ No '{split}' directories found under {self.models_root}, skipping split.")
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
                return False
        return True

    def augment_species(self, species_id, species_name):
        """
        Runs augmentation on the given species.
        """
        print(f"\n🎯 Starting augmentation for species: {species_name} (ID {species_id})")
        gen = AugmentedClipGenerator(self.db_path, output_dir="./temp")
        pairs = gen.fetch_files(target_species_id=species_id)
        gen.close()

        random.shuffle(pairs)
        total = len(pairs)
        train_end = int(total * 0.8)
        test_end = train_end + int(total * 0.1)
        train_pairs = pairs[:train_end]
        test_pairs = pairs[train_end:test_end]
        val_pairs = pairs[test_end:]

        for split_name, split_pairs in [("train", train_pairs), ("test", test_pairs), ("validation", val_pairs)]:
            normalized_species_name = species_name.strip().lower().replace(' ', '_')
            out_dir = os.path.join(self.models_root, normalized_species_name, split_name, str(species_id))
            os.makedirs(out_dir, exist_ok=True)
            split_gen = AugmentedClipGenerator(self.db_path, output_dir=out_dir)
            for species_file, non_species_file in split_pairs:
                split_gen.overlay_clips(species_file, non_species_file)
            split_gen.close()
            print(f"🏁 Finished split: {split_name} → {len(split_pairs)} overlays written to {out_dir}")

        print("\n✅ Augmentation complete!")

    def run(self, species_name=None, species_id=None):
        """
        High-level runner: selects species, verifies dirs, runs augmentation.
        """
        sid, sname = self.select_species(species_name, species_id)
        if not sid or not sname:
            return
        if not self.verify_species_dirs(sid):
            return
        self.augment_species(sid, sname)