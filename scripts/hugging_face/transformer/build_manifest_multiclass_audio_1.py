import os, csv, sqlite3, random, pathlib
from pydub import AudioSegment

# === CONFIG ===
DB_PATH = './db/chorusAvery.db'
RAW_AUDIO_FOLDER = './recordings/training_data'
SLICE_MS = 2500
SPLIT = (0.8, 0.1, 0.1)
CACHE_ROOT = "./data/slices_hf"   # WAV slices go here

# Replace with your canonical species names exactly as in Species.name
TARGET_SPECIES = [
    "american_toad","spring_peeper","chorus_frog",
    "green_frog","gray_treefrog","bullfrog"
]

RNG = random.Random(1337)

def q(conn, sql, args=()):
    cur = conn.cursor(); cur.execute(sql, args); rows = cur.fetchall(); cur.close(); return rows

def species_name_to_id(conn, name):
    r = q(conn, "SELECT id FROM Species WHERE lower(name)=lower(?)", (name,))
    return r[0][0] if r else None

def clips_for_species(conn, sid):
    r = q(conn, """
        SELECT DISTINCT c.clip_path
        FROM Clips c JOIN ClipAnnotations a ON a.clip_id=c.id
        WHERE a.species_id = ?
    """, (sid,))
    return [row[0] for row in r]

def clips_without_any_targets(conn, target_ids):
    # Clips NOT annotated with any of the target species
    placeholders = ",".join(["?"]*len(target_ids))
    r = q(conn, f"""
        SELECT DISTINCT c.clip_path
        FROM Clips c
        WHERE c.id NOT IN (
          SELECT clip_id FROM ClipAnnotations WHERE species_id IN ({placeholders})
        )
    """, tuple(target_ids))
    paths = [row[0] for row in r]
    RNG.shuffle(paths)
    return paths

def slice_wav(src_wav, out_dir, slice_ms=SLICE_MS):
    try:
        audio = AudioSegment.from_file(src_wav)
    except Exception:
        return []
    if len(audio) < slice_ms: 
        return []
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_wav))[0]
    out = []
    for i in range(0, len(audio)-slice_ms+1, slice_ms):
        chunk = audio[i:i+slice_ms]
        dst = os.path.join(out_dir, f"{base}_s{i}.wav")
        chunk.export(dst, format="wav")
        out.append(dst)
    return out

def split(items, ratios=SPLIT):
    items = list(items); RNG.shuffle(items)
    n = len(items); n_tr = int(n*ratios[0]); n_va = int(n*ratios[1])
    return items[:n_tr], items[n_tr:n_tr+n_va], items[n_tr+n_va:]

def main():
    pathlib.Path(CACHE_ROOT).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Map species names → ids available in DB
    species_ids = {}
    for name in TARGET_SPECIES:
        sid = species_name_to_id(conn, name)
        if sid is None:
            print(f"⚠️ species not found in DB: {name}")
            continue
        species_ids[name] = sid

    # Slice positives for each species
    label_to_slices = {name: [] for name in species_ids.keys()}
    for name, sid in species_ids.items():
        clips = clips_for_species(conn, sid)
        for rel in clips:
            src = os.path.join(RAW_AUDIO_FOLDER, rel)
            out_dir = os.path.join(CACHE_ROOT, name, "all")
            label_to_slices[name].extend(slice_wav(src, out_dir))

    # Build 'other' from clips with no target species annotations
    other_slices = []
    neg_clips = clips_without_any_targets(conn, list(species_ids.values()))
    for rel in neg_clips:
        src = os.path.join(RAW_AUDIO_FOLDER, rel)
        out_dir = os.path.join(CACHE_ROOT, "other", "all")
        other_slices.extend(slice_wav(src, out_dir))

    # Split and write manifest
    rows = []
    def emit(label, paths):
        tr, va, te = split(paths)
        for p in tr: rows.append({"filepath": p, "label": label, "subset": "train", "is_mixed": "true" if label=="other" else "false"})
        for p in va: rows.append({"filepath": p, "label": label, "subset": "val",   "is_mixed": "true" if label=="other" else "false"})
        for p in te: rows.append({"filepath": p, "label": label, "subset": "test",  "is_mixed": "true" if label=="other" else "false"})

    for label, paths in label_to_slices.items():
        emit(label, paths)
    emit("other", other_slices)

    out_csv = os.path.join(CACHE_ROOT, "metadata_audio_multiclass.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filepath","label","subset","is_mixed"])
        w.writeheader(); w.writerows(rows)

    print(f"✅ Wrote {len(rows)} rows → {out_csv}")
    print(f"Labels: {sorted(list(species_ids.keys()) + ['other'])}")

if __name__ == "__main__":
    main()
