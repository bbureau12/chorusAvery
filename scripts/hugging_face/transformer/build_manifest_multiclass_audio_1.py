import os, csv, sqlite3, pathlib, random, argparse
from pydub import AudioSegment
from scripts.training.collection.collect_negative_clips import NegativeClipGenerator

DB_PATH_DEFAULT = './db/chorusAvery.db'
RAW_DEFAULT = './recordings/training_data'
CACHE_ROOT_DEFAULT = './data/slices_hf'
SLICE_MS_DEFAULT = 2500
RNG = random.Random(1337)

def q(cur, sql, args=()):
    cur.execute(sql, args)
    return cur.fetchall()

def choose_species(conn,
                   top_n=8,
                   min_clips=50,
                   animal_type_id=None,
                   name_like=None,
                   locations=None):
    """
    Return [(id, name, n_clips), ...] of target species.
    - top_n: max species to return ordered by clip count desc
    - min_clips: require at least this many DISTINCT clips
    - animal_type_id: restrict by Species.animal_type_id (e.g., frogs)
    - name_like: substring (case-insensitive) filter on Species.name
    - locations: iterable of SourceFiles.LocationID to include
    """
    cur = conn.cursor()
    filters = []
    args = []

    base = """
      SELECT s.id, s.name, COUNT(DISTINCT c.id) AS n
      FROM Species s
      JOIN ClipAnnotations ca ON ca.species_id = s.id
      JOIN Clips c ON c.id = ca.clip_id
    """

    if locations:
        placeholders = ",".join(["?"] * len(locations))
        base += f" JOIN SourceFiles sf ON c.source_id = sf.id AND sf.LocationID IN ({placeholders})"
        args.extend(locations)

    where = []
    if animal_type_id is not None:
        where.append("s.animal_type_id = ?")
        args.append(animal_type_id)
    if name_like:
        where.append("LOWER(s.name) LIKE ?")
        args.append(f"%{name_like.lower()}%")

    if where:
        base += " WHERE " + " AND ".join(where)

    base += " GROUP BY s.id HAVING COUNT(DISTINCT c.id) >= ? ORDER BY n DESC"
    args.append(min_clips)

    rows = q(cur, base, tuple(args))
    cur.close()
    return rows[:top_n]

def species_id_to_name(cur, sid):
    r = q(cur, "SELECT name FROM Species WHERE id = ?", (sid,))
    return r[0][0] if r else None

def clips_for_species(cur, sid):
    r = q(cur, """
        SELECT DISTINCT c.clip_path
        FROM Clips c JOIN ClipAnnotations ca ON ca.clip_id = c.id
        WHERE ca.species_id = ?
    """, (sid,))
    return [row[0] for row in r]

def slice_wav(src_wav, out_dir, slice_ms):
    try:
        audio = AudioSegment.from_file(src_wav)
    except Exception:
        return []
    if len(audio) < slice_ms:
        return []
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_wav))[0]
    out = []
    for i in range(0, len(audio) - slice_ms + 1, slice_ms):
        dst = os.path.join(out_dir, f"{base}_s{i}.wav")
        audio[i:i+slice_ms].export(dst, format="wav")
        out.append(dst)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH_DEFAULT)
    ap.add_argument("--raw", default=RAW_DEFAULT)
    ap.add_argument("--cache_root", default=CACHE_ROOT_DEFAULT)
    ap.add_argument("--slice_ms", type=int, default=SLICE_MS_DEFAULT)

    # Dynamic species selection
    ap.add_argument("--top_n", type=int, default=8)
    ap.add_argument("--min_clips", type=int, default=50)
    ap.add_argument("--animal_type_id", type=int, default=None,
                    help="e.g., the frog/reptile group id used in Species.animal_type_id")
    ap.add_argument("--name_like", type=str, default=None,
                    help="substring match on species name (optional)")
    ap.add_argument("--locations", type=str, default=None,
                    help="comma-separated LocationID filter (optional)")

    # Negatives
    ap.add_argument("--neg_multiplier", type=float, default=1.0,
                    help="negatives relative to positives (1.0 ≈ balanced)")
    args = ap.parse_args()

    locations = None
    if args.locations:
        locations = [int(x.strip()) for x in args.locations.split(",") if x.strip()]

    pathlib.Path(args.cache_root).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db); cur = conn.cursor()

    # 1) Pick species dynamically
    picked = choose_species(conn,
                            top_n=args.top_n,
                            min_clips=args.min_clips,
                            animal_type_id=args.animal_type_id,
                            name_like=args.name_like,
                            locations=locations)
    if not picked:
        print("❌ No species matched your selection criteria."); return

    species_ids = [sid for sid, _, _ in picked]
    species_names = {sid: name for sid, name, _ in picked}
    print("✅ Selected species:", [species_names[sid] for sid in species_ids])

    # 2) Slice positives
    label_to_slices = {species_names[sid]: [] for sid in species_ids}
    for sid in species_ids:
        out_all = os.path.join(args.cache_root, species_names[sid], "all")
        for rel in clips_for_species(cur, sid):
            src = os.path.join(args.raw, rel)
            label_to_slices[species_names[sid]] += slice_wav(src, out_all, args.slice_ms)

    # 3) Negatives via your generator (WAVs per split)
    # Use a fixed model_name stub; we are writing into export_root anyway
    pos_slice_total = sum(len(v) for v in label_to_slices.values())
    neg_gen = NegativeClipGenerator(
        model_name="hf_mvp",
        db_path=args.db,
        recordings_root=args.raw,
        export_mode="wavs",
        export_root=os.path.join(args.cache_root, "other"),
        return_manifest=True,
        target_multiplier=max(0.0, args.neg_multiplier),
        negative_length_ms=args.slice_ms
    )
    neg_manifest = neg_gen.run()  # {"train":[...], "val":[...], "test":[...]}

    # 4) Split positives (simple random split at slice level)
    rows = []
    def emit_random_split(label, paths):
        paths = list(paths); RNG.shuffle(paths)
        n = len(paths); n_tr = int(0.8 * n); n_va = int(0.1 * n)
        for p in paths[:n_tr]: rows.append({"filepath": p, "label": label, "subset": "train", "is_mixed": "false"})
        for p in paths[n_tr:n_tr+n_va]: rows.append({"filepath": p, "label": label, "subset": "val", "is_mixed": "false"})
        for p in paths[n_tr+n_va:]: rows.append({"filepath": p, "label": label, "subset": "test", "is_mixed": "false"})

    for label, paths in label_to_slices.items():
        emit_random_split(label, paths)

    # 5) Add negatives (already split by generator)
    for subset in ["train", "val", "test"]:
        for p in neg_manifest.get(subset, []):
            rows.append({"filepath": p, "label": "other", "subset": subset, "is_mixed": "true"})

    # 6) Write manifest
    out_csv = os.path.join(args.cache_root, "metadata_audio_multiclass.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filepath","label","subset","is_mixed"])
        w.writeheader(); w.writerows(rows)
    print(f"✅ HF manifest: {len(rows)} rows → {out_csv}")

    cur.close(); conn.close()

if __name__ == "__main__":
    main()
