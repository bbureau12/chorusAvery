# import os
# import shutil
# import sqlite3
# import random

# # ---------------------------------
# # CONFIGURATION
# # ---------------------------------

# DB_PATH = r"D:\Projects\ChorusAvery\chorusAvery\db\chorusAvery.db"   # <-- update this
# CLIPS_BASE_DIR = r"D:\Projects\ChorusAvery\chorusAvery\recordings\training_data"      # base directory for clip_path
# OUTPUT_DIR = "dsp_dataset"                     # dataset root folder

# MAX_PER_BUCKET = 600  # max files per (category, purity) bucket


# def ensure_dir(path: str):
#     if not os.path.exists(path):
#         os.makedirs(path)


# # ---------------------------------
# # CONNECT TO DB
# # ---------------------------------
# conn = sqlite3.connect(DB_PATH)
# cur = conn.cursor()

# query = """
# WITH clip_counts AS (
#     SELECT
#         ca.clip_id,
#         SUM(CASE WHEN ca.non_animal_sound_id IS NOT NULL THEN 1 ELSE 0 END) AS non_animal_count,
#         SUM(CASE WHEN ca.species_id IS NOT NULL THEN 1 ELSE 0 END) AS species_count
#     FROM ClipAnnotations ca
#     GROUP BY ca.clip_id
# )
# SELECT 
#     c.clip_path,
#     nas.name AS category,
#     CASE 
#         WHEN cc.species_count = 0 
#              AND cc.non_animal_count = 1 
#         THEN 1 
#         ELSE 0 
#     END AS is_pure_non_animal
# FROM ClipAnnotations ca
# JOIN Clips c ON ca.clip_id = c.id
# JOIN NonAnimalSounds nas ON ca.non_animal_sound_id = nas.id
# JOIN clip_counts cc ON cc.clip_id = ca.clip_id
# WHERE ca.non_animal_sound_id IS NOT NULL
#   AND nas.is_ambience = 3;
# """

# rows = cur.execute(query).fetchall()
# conn.close()

# print(f"Found {len(rows)} annotated non-animal clips (before filtering & capping).")


# # ---------------------------------
# # GROUP BY (category, purity)
# # ---------------------------------
# bucket_to_files: dict[tuple[str, str], list[str]] = {}

# for clip_path, category, is_pure in rows:
#     category_norm = category.lower().replace(" ", "_")
#     purity = "pure" if is_pure == 1 else "mixed"

#     abs_clip_path = os.path.join(CLIPS_BASE_DIR, clip_path)

#     if not os.path.isfile(abs_clip_path):
#         print(f"[WARNING] Missing file: {abs_clip_path}")
#         continue

#     key = (category_norm, purity)
#     bucket_to_files.setdefault(key, []).append(abs_clip_path)


# # ---------------------------------
# # CREATE OUTPUT DIRS AND COPY (CAPPED)
# # ---------------------------------
# ensure_dir(OUTPUT_DIR)

# for (category, purity), files in bucket_to_files.items():
#     random.shuffle(files)

#     if MAX_PER_BUCKET is not None and len(files) > MAX_PER_BUCKET:
#         files = files[:MAX_PER_BUCKET]

#     out_dir = os.path.join(OUTPUT_DIR, category, purity)
#     ensure_dir(out_dir)

#     print(f"\nBucket '{category}/{purity}': exporting {len(files)} files")

#     for src in files:
#         dst = os.path.join(out_dir, os.path.basename(src))
#         shutil.copy2(src, dst)

#     print(f"  Copied {len(files)} files to {out_dir}")

# print("\nDSP test dataset export complete!")


# import os
# import shutil
# import sqlite3
# import random

# DB_PATH = r"D:\Projects\ChorusAvery\chorusAvery\db\chorusAvery.db"   # <-- update this
# CLIPS_BASE_DIR = r"D:\Projects\ChorusAvery\chorusAvery\recordings\training_data"      # base directory for clip_path
# OUTPUT_DIR = "dsp_dataset"                     # dataset root folder

# MAX_PER_BUCKET = 200  # max files per (category, purity) bucket

# def ensure_dir(path: str):
#     if not os.path.exists(path):
#         os.makedirs(path)

# conn = sqlite3.connect(DB_PATH)
# cur = conn.cursor()

# query = """
# SELECT 
#     c.clip_path,
#     s.name AS category
# FROM ClipAnnotations ca
# JOIN Clips c   ON ca.clip_id = c.id
# JOIN Species s ON ca.species_id = s.id
# WHERE ca.species_id IS NOT NULL
#   AND ca.non_animal_sound_id IS NULL;
# """

# rows = cur.execute(query).fetchall()
# conn.close()

# print(f"Found {len(rows)} annotated pure-nature clips.")

# bucket_to_files: dict[str, list[str]] = {}

# for clip_path, category in rows:
#     category_norm = category.lower().replace(" ", "_")
#     abs_clip_path = os.path.join(CLIPS_BASE_DIR, clip_path)

#     if not os.path.isfile(abs_clip_path):
#         print(f"[WARNING] Missing file: {abs_clip_path}")
#         continue

#     bucket_to_files.setdefault(category_norm, []).append(abs_clip_path)

# ensure_dir(OUTPUT_DIR)

# for category, files in bucket_to_files.items():
#     random.shuffle(files)
#     if MAX_PER_BUCKET is not None and len(files) > MAX_PER_BUCKET:
#         files = files[:MAX_PER_BUCKET]

#     out_dir = os.path.join(OUTPUT_DIR, category)
#     ensure_dir(out_dir)

#     print(f"\nCategory '{category}': exporting {len(files)} files")

#     for src in files:
#         dst = os.path.join(out_dir, os.path.basename(src))
#         shutil.copy2(src, dst)

# print("\nNature dataset export complete!")
import os
import shutil
import sqlite3

# ---------------------------------
# CONFIGURATION
# ---------------------------------

DB_PATH = r"D:\Projects\ChorusAvery\chorusAvery\db\chorusAvery.db"
CLIPS_BASE_DIR = r"D:\Projects\ChorusAvery\chorusAvery\recordings\training_data"
OUTPUT_DIR = "dataset_cnn"   # root dataset folder

# Optional cap per class to avoid explosion; set to None for unlimited
MAX_PER_BUCKET = 1000  # e.g. 1000


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def safe_copy(relative_clip_path: str, dest_dir: str):
    """Join CLIPS_BASE_DIR + clip_path and copy if present."""
    abs_src = os.path.join(CLIPS_BASE_DIR, relative_clip_path)
    if not os.path.isfile(abs_src):
        print(f"[WARNING] Missing file: {abs_src}")
        return False

    ensure_dir(dest_dir)
    fname = os.path.basename(relative_clip_path)
    dst = os.path.join(dest_dir, fname)
    shutil.copy2(abs_src, dst)
    return True


# ---------------------------------
# CONNECT TO DB
# ---------------------------------

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---------------------------------
# 1) CLEAN SPECIES CLIPS  -> nature/<species_name>/
# ---------------------------------
print("Exporting CLEAN species clips into nature/...")

query_clean_species = """
WITH per_clip AS (
    SELECT
        c.id AS clip_id,
        c.clip_path,
        SUM(CASE WHEN ca.species_id IS NOT NULL THEN 1 ELSE 0 END) AS species_rows,
        COUNT(DISTINCT ca.species_id) AS distinct_species,
        SUM(CASE WHEN ca.non_animal_sound_id IS NOT NULL THEN 1 ELSE 0 END) AS non_animal_rows
    FROM ClipAnnotations ca
    JOIN Clips c ON c.id = ca.clip_id
    GROUP BY c.id, c.clip_path
),
clean_clips AS (
    SELECT clip_id, clip_path
    FROM per_clip
    WHERE species_rows > 0         -- has at least one species
      AND distinct_species = 1     -- only one unique species
      AND non_animal_rows = 0      -- no non-animal sounds
)
SELECT
    cc.clip_path,
    s.name AS species_name
FROM clean_clips cc
JOIN ClipAnnotations ca ON ca.clip_id = cc.clip_id
JOIN Species s ON s.id = ca.species_id
GROUP BY cc.clip_id, cc.clip_path, s.name;
"""

species_rows = cur.execute(query_clean_species).fetchall()
print(f"  Found {len(species_rows)} clean species clips.")

species_counts = {}

for clip_path, species_name in species_rows:
    bucket = ("nature", species_name)
    species_counts.setdefault(bucket, 0)

    if MAX_PER_BUCKET is not None and species_counts[bucket] >= MAX_PER_BUCKET:
        continue

    dest = os.path.join(OUTPUT_DIR, "nature", species_name)
    if safe_copy(clip_path, dest):
        species_counts[bucket] += 1

# ---------------------------------
# 2) NATURAL AMBIENCE (is_ambience = 4) -> nature/<name>/
# ---------------------------------
print("\nExporting natural ambience (is_ambience = 4) into nature/...")

query_nature_ambience = """
SELECT DISTINCT
    c.clip_path,
    n.name AS ambience_name
FROM ClipAnnotations ca
JOIN Clips c ON c.id = ca.clip_id
JOIN NonAnimalSounds n ON n.id = ca.non_animal_sound_id
WHERE n.is_ambience = 4
  AND ca.species_id IS NULL;   -- pure ambience only
"""

amb_rows = cur.execute(query_nature_ambience).fetchall()
print(f"  Found {len(amb_rows)} ambience clips.")

amb_counts = {}

for clip_path, ambience_name in amb_rows:
    bucket = ("nature", ambience_name)
    amb_counts.setdefault(bucket, 0)

    if MAX_PER_BUCKET is not None and amb_counts[bucket] >= MAX_PER_BUCKET:
        continue

    dest = os.path.join(OUTPUT_DIR, "nature", ambience_name)
    if safe_copy(clip_path, dest):
        amb_counts[bucket] += 1

# ---------------------------------
# 3) ANTHRO SOUNDS (is_ambience = 3) -> anthro/<name>/
# ---------------------------------
print("\nExporting anthropogenic sounds (is_ambience = 3) into anthro/...")

query_anthro = """
SELECT DISTINCT
    c.clip_path,
    n.name AS sound_name
FROM ClipAnnotations ca
JOIN Clips c ON c.id = ca.clip_id
JOIN NonAnimalSounds n ON n.id = ca.non_animal_sound_id
WHERE n.is_ambience = 3;
"""

anthro_rows = cur.execute(query_anthro).fetchall()
print(f"  Found {len(anthro_rows)} anthro clips.")

anthro_counts = {}

for clip_path, sound_name in anthro_rows:
    # normalize folder names a bit (optional)
    sound_folder = sound_name.lower().replace(" ", "_")
    bucket = ("anthro", sound_folder)
    anthro_counts.setdefault(bucket, 0)

    if MAX_PER_BUCKET is not None and anthro_counts[bucket] >= MAX_PER_BUCKET:
        continue

    dest = os.path.join(OUTPUT_DIR, "anthro", sound_folder)
    if safe_copy(clip_path, dest):
        anthro_counts[bucket] += 1

conn.close()

print("\n✔ Dataset export complete!")
print(f"Output root: {os.path.abspath(OUTPUT_DIR)}")
