# Data Contracts

This document captures the practical contracts between scripts, the SQLite database, and filesystem artifacts.

## Database locations

Observed in current scripts:
- `./db/chorusAvery.db` (most common)
- `./chorusAvery.db` (present in repo root and used by some paths)

Contract recommendation:
- Standardize on `./db/chorusAvery.db` for all scripts.

## DB migration note

As of February 27, 2026:
- Canonical live database is `./db/chorusAvery.db`.
- Legacy root DB was retired from repo root and moved to:
- `./db/_legacy/chorusAvery.root_legacy_2026-02-27.db`

Rationale:
- The root DB was a partial/legacy file with limited tables and no active pipeline state.
- The `db/` copy is the full operational database used by ingestion, labeling, training, and validation scripts.

## Core tables used by pipeline

### `SourceFiles`
Purpose:
- Canonical record for imported long-form source recordings.

Key columns:
- `id` (PK)
- `filename`
- `LocationID`
- `From_Date`, `To_Date`

Writers:
- `scripts/step_1_chunk_generator.py`

Readers:
- `scripts/import/import_new_soundfile.py`
- `scripts/sound_labeler.py` (source lookup)

### `Clips`
Purpose:
- Metadata for extracted clip files and timing/volume attributes.

Key columns:
- `id` (PK)
- `clip_path`
- `source_id`
- `start_date_source`, `end_date_source`
- `start_date_utc`, `end_time_utc`
- `max_dbfs`, `avg_dbfs`, `boost_db`

Writers:
- `scripts/sound_labeler.py`

Readers:
- Training/validation query scripts.

### `ClipAnnotations`
Purpose:
- Many-to-one annotation records for each clip.

Key columns:
- `clip_id`
- `species_id`
- `non_animal_sound_id`
- `verified`
- `relative_entity_volume`

Writers:
- `scripts/sound_labeler.py`
- `scripts/training/eval/evaluate_with_gradcam.py` (updates `relative_entity_volume`)

Readers:
- Dataset builders and validation scripts.

### `Species`
Purpose:
- Species catalog.

Key columns:
- `id`, `name`, `code`, `scentific_name`

Readers:
- Labeling and validation scripts.

### `NonAnimalSounds` and `SoundCategories`
Purpose:
- Non-animal taxonomy for filtering and dataset generation.

Readers/Writers:
- Used heavily in non-animal dataset pipelines.

### `Detections`
Purpose:
- BirdNET-derived detections tied to source files/species codes.

Writers:
- `scripts/run_birdnet.py` via loader utilities.

## File and folder contracts

### Source audio
- Input folder: `recordings/raw/`
- Expected formats: `.wav` and (in chunker) `.mp3`

### Chunks
- Output folder: `recordings/chunks/`
- Typical format: 16kHz mono WAV chunks
- Lifecycle: transient; often deleted after clip extraction

### Clips and sidecars
- Output folder: `recordings/clips/`
- Clip file: `.wav`
- Sidecar: `.json` with fields such as:
- `filename`
- `boost_applied_db`
- `start_time`
- `duration_ms`
- `max_dbfs`
- `avg_dbfs`

### Labeled training clips
- Folder: `recordings/training_data/<year>/`
- `Clips.clip_path` stores relative path under `recordings/training_data`

### Model datasets
- Folder: `recordings/model/<slug>/`
- Split folders: `train/`, `validation/`, `test/`
- Class subfolders under each split
- Artifacts:
- `class_names.json`
- `clip_counts.json`

### Trained models and results
- Models: `models/*.keras`
- Results: `models/results/<model_basename>/`
- Misclassified exports: `misclassified/`

## Naming and timestamp assumptions

- Many scripts infer timestamps from filenames using patterns like `yymmdd_*_HH_MM_SS`.
- Invalid/unexpected filenames can cause fallback prompts or skipped records.
- Labeling pipeline derives source mapping from clip filename prefix (first `YYMMDD_HHMM` segment pattern).

## Quality and integrity checks

Recommended routine checks:
- Every file in `recordings/training_data` has corresponding `Clips` row.
- Every labeled clip has at least one `ClipAnnotations` row.
- `Clips.source_id` references valid `SourceFiles.id`.
- DB path used by scripts points to the same physical DB file.

## Known contract drift

- Dual DB files in repo root and `db/` can split state.
- `import_new_soundfile.py` currently does not insert into `SourceFiles` despite naming.
- Some scripts expect `models/complete/` while others write to `models/`.

## Related docs

- [docs/SCRIPT_REFERENCE.md](SCRIPT_REFERENCE.md)
- [docs/PIPELINE.md](PIPELINE.md)
- [docs/DEPENDENCY_MAP.md](DEPENDENCY_MAP.md)
