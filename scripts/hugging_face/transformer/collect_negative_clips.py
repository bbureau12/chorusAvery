# scripts/hugging_face/transformer/collect_negative_clips.py
from training.collection.collect_negative_clips import NegativeClipGenerator
def sample_negatives_for_targets(
    conn,                      # sqlite3 connection
    target_species_ids,        # list[int]
    n_train, n_val, n_test,    # target *counts* of negative CLIPS (before slicing)
    clip_len_ms=2500,
    seed=1337,
    # optional knobs your module already supports:
    stratify_by=("recorder_id","date_bin"),  # or whatever you use
    pools=("non_animal","non_target_animals"),
    hard_negatives_for=None,   # dict{species_id: [confuser species ids]}
):
    """
    Return dict with lists of clip *relative paths*:
      {"train":[...], "val":[...], "test":[...]}
    Uses your existing logic to balance by pool, location/time, etc.
    """
    neg_gen = NegativeClipGenerator(model_name=slug)
    neg_gen.run()
    return {"train": train_paths, "val": val_paths, "test": test_paths}
