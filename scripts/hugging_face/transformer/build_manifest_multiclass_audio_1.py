# hugging_face/transformer/build_manifest_multiclass_audio.py
import os, csv, sqlite3, pathlib, random
from pydub import AudioSegment
from scripts.training.collection.collect_negative_clips import NegativeClipGenerator

DB_PATH = './db/chorusAvery.db'
RAW = './recordings/training_data'
CACHE_ROOT = './data/slices_hf'          # WAV slices for HF live here
SLICE_MS = 2500
TARGET_SPECIES = ["american_toad","spring_peeper","chorus_frog","green_frog","gray_treefrog","bullfrog"]
RNG = random.Random(1337)

def q(conn, sql, args=()):
    cur = conn.cursor(); cur.execute(sql, args); r = cur.fetchall(); cur.close(); return r

def species_name_to_id(conn, name):
    r = q(conn, "SELECT id FROM Species WHERE lower(name)=lower(?)", (name,))
    return r[0][0] if r else None

def clips_for_species(conn, sid):
    r = q(conn, """
        SELECT DISTINCT c.clip_path
        FROM Clips c JOIN ClipAnnotations ca ON ca.clip_id=c.id
        WHERE ca.species_id = ?
    """, (sid,))
    return [row[0] for row in r]

def slice_wav(src_wav, out_dir):
    try:
        audio = AudioSegment.from_file(src_wav)
    except Exception:
        return []
    if len(audio) < SLICE_MS: 
        return []
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_wav))[0]
    out = []
    for i in range(0, len(audio)-SLICE_MS+1, SLICE_MS):
        dst = os.path.join(out_dir, f"{base}_s{i}.wav")
        audio[i:i+SLICE_MS].export(dst, format="wav")
        out.append(dst)
    return out

def main():
    pathlib.Path(CACHE_ROOT).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # 1) Positives → slice WAVs
    label_to_slices = {}
    species_ids = {}
    for name in TARGET_SPECIES:
        sid = species_name_to_id(conn, name)
        if sid is None: 
            print(f"⚠️ missing species: {name}"); 
            continue
        species_ids[name] = sid

        out_all = os.path.join(CACHE_ROOT, name, "all")
        label_to_slices[name] = []
        for rel in clips_for_species(conn, sid):
            src = os.path.join(RAW, rel)
            label_to_slices[name] += slice_wav(src, out_all)

    # 2) Negatives via your generator → WAVs to data/slices_hf/other/<split>
    #    We want roughly as many negative *slices* as positives.
    pos_slice_total = sum(len(v) for v in label_to_slices.values())
    # Convert to "clip budget" by assuming ~1 slice per clip (close enough for MVP).
    neg_gen = NegativeClipGenerator(
        model_name="hf_mvp",
        db_path=DB_PATH,
        recordings_root=RAW,
        export_mode="wavs",
        export_root=os.path.join(CACHE_ROOT, "other"),
        return_manifest=True,
        target_multiplier=1,         # start balanced; adjust later
        negative_length_ms=SLICE_MS
    )
    neg_manifest = neg_gen.run()     # {"train":[...wav], "val":[...], "test":[...]}

    # 3) Split positives (simple random split at slice level)
    rows = []
    def emit_random_split(label, paths):
        paths = list(paths); RNG.shuffle(paths)
        n = len(paths); n_tr = int(0.8*n); n_va = int(0.1*n)
        for p in paths[:n_tr]: rows.append({"filepath":p,"label":label,"subset":"train","is_mixed":"false"})
        for p in paths[n_tr:n_tr+n_va]: rows.append({"filepath":p,"label":label,"subset":"val","is_mixed":"false"})
        for p in paths[n_tr+n_va:]: rows.append({"filepath":p,"label":label,"subset":"test","is_mixed":"false"})

    for label, paths in label_to_slices.items():
        emit_random_split(label, paths)

    # 4) Add negatives (already split by generator)
    for subset in ["train","val","test"]:
        for p in neg_manifest.get(subset, []):
            rows.append({"filepath": p, "label": "other", "subset": subset, "is_mixed":"true"})

    # 5) Write HF manifest
    out_csv = os.path.join(CACHE_ROOT, "metadata_audio_multiclass.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filepath","label","subset","is_mixed"])
        w.writeheader(); w.writerows(rows)
    print(f"✅ HF manifest: {len(rows)} rows → {out_csv}")

if __name__ == "__main__":
    main()
