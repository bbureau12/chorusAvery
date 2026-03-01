# Script Reference

This is the operational reference for high-use scripts.

Conventions:
- Run from repo root.
- Most scripts are interactive (prompts), not fully argument-driven.
- Paths are generally relative to repo root.

## Preflight

### `scripts/doctor.py`
Command:
```powershell
python scripts\doctor.py --skip-birdnet
python scripts\doctor.py --strict
```
Purpose:
- Validate local environment and repository prerequisites before pipeline runs.

Checks:
- Python version
- ffmpeg availability
- Required directories
- Canonical DB presence and core table availability
- BirdNET model assets (unless `--skip-birdnet`)

## Core pipeline

### `scripts/import/import_new_soundfile.py`
Purpose:
- Scan a target directory for new `.wav` files not yet in `SourceFiles`.
- Copy selected file to `./recordings/raw`.

Inputs:
- Prompt: source folder path.
- DB: `./db/chorusAvery.db` table `SourceFiles`.

Outputs:
- File copy into `recordings/raw`.

Notes:
- Current version logs copy/import messages but does not currently insert a DB row in `copy_and_import_file`.

### `scripts/step_1_chunk_generator.py`
Purpose:
- Split raw `.mp3/.wav` files into 5-minute 16kHz mono WAV chunks.
- Insert source metadata into `SourceFiles`.

Inputs:
- `./recordings/raw`
- Prompts for `LocationID` and optional datetime fallback.

Outputs:
- `./recordings/chunks/*.wav`
- Source rows in `SourceFiles`
- Deletes original file from `recordings/raw` after chunking.

### `scripts/step_2_clip_parserv2.py`
Purpose:
- Slice chunk WAVs into candidate clips using dynamic dBFS threshold.
- Emit WAV clips with JSON sidecars.

Inputs:
- `./recordings/chunks/*.wav`

Outputs:
- `./recordings/clips/*.wav`
- `./recordings/clips/*.json`
- Deletes processed chunk files.

### `scripts/run_birdnet.py`
Purpose:
- Run BirdNET over WAV files and import filtered detections.

Inputs:
- `./recordings/raw/*.wav`
- Prompts for location via `utils.location_selector.choose_location()`
- BirdNET runtime (`python -m birdnet_analyzer.analyze`)

Outputs:
- Detection CSVs under `./data/`
- DB inserts through `utils.load_detections_from_csv.load_detections_from_csv`

## Labeling and review

### `scripts/sound_labeler.py`
Purpose:
- Interactive clip labeling tool with playback/edit/split/delete controls.

Inputs:
- DB: `./db/chorusAvery.db`
- Clips: `./recordings/clips`

Outputs:
- Moves labeled clips into `./recordings/training_data/<year>/`
- Inserts rows into `Clips` and `ClipAnnotations`
- Handles UTC conversion using `Locations` coordinates.

### `scripts/filter_review_tool.py`
Purpose:
- Secondary review pass for filtered clips.

Inputs/Outputs:
- Reads and updates clip review state through DB and clip folders.

### `scripts/review/species_review.py`
Purpose:
- Additional review workflow around species-labeled clips.

## Dataset building and training

### `scripts/training/dataset_builder.py`
Purpose:
- Build spectrogram dataset tree with augmentation for selected classes.

Inputs:
- Prompts:
- Dataset type (`binary` or `multilabel`)
- Label source (`species` or `non-species`)
- Include clean class 0
- Min and max clips
- Output slug
- DB: `./db/chorusAvery.db`
- Audio root: `./recordings/training_data`

Outputs:
- Dataset under `./recordings/model/<slug>/`
- `class_names.json`
- `clip_counts.json`

### `scripts/training/train_test_eval_latest.py`
Purpose:
- Interactive model training/evaluation for dataset under `recordings/model`.

Inputs:
- Prompt: dataset selection
- Reads train/validation/test PNG directories

Outputs:
- Model `.keras` files in `./models/`
- Plots and reports in `./models/results/<model_basename>/`
- Misclassified exports under `./misclassified/`

## Validation and model checks

### `scripts/validation/validate_self.py`
Purpose:
- Run model inference against species-cohort clips queried from DB.

Inputs:
- Prompt: model selection, species name, sample count

Outputs:
- Console predictions/probabilities over selected cohort clips.

### `scripts/validation/validate_file.py`
Purpose:
- Run model inference against folder-based PNG test files.

Inputs:
- Prompt: model selection, species slug, sample count
- Expects folder pattern `./recordings/model/<slug>/test/13`

Outputs:
- Console predictions/probabilities.

### `scripts/validation/validate_cohorts.py`
Purpose:
- Evaluate model against mixed-species cohorts.

Inputs:
- Prompt: model selection, species name, sample count

Outputs:
- Console predictions/probabilities.

## Argument-driven scripts

### `scripts/training/eval/evaluate_with_gradcam.py`
Command:
```powershell
python scripts\training\eval\evaluate_with_gradcam.py [--auto]
```
Purpose:
- Compute Grad-CAM-based relative entity volume score and write to DB.

Notes:
- Script defines `--auto` but currently calls `main(False)` unconditionally; the flag is not wired through.

### `scripts/analysis/date_bias_analysis.py`
Command:
```powershell
python scripts\analysis\date_bias_analysis.py --help
```
Purpose:
- Analyze interval coverage by month, day-of-week, and hour from DB and/or WAV files.

Key args:
- `--sqlite` default `./db/chorusAvery.db`
- `--table` default `SourceFiles`
- `--from-col` default `From_Date`
- `--to-col` default `To_Date`
- `--root` default `E:\`
- `--tz` default `America/Chicago`
- `--since` default `2024-01-01`
- `--until` default `2025-12-31`
- `--export-prefix` default `chorus_avery_interval_coverage`

Outputs:
- CSV exports for month/day/hour coverage.

## Known script-level hazards

- Mixed DB path assumptions (`./chorusAvery.db` vs `./db/chorusAvery.db`).
- Some scripts rely on `sys.path` insertion instead of package imports.
- `utils/split_wav.py` currently uses a bare import.
- Several scripts are interactive only, which limits automation.

## Related docs

- [docs/PIPELINE.md](PIPELINE.md)
- [docs/RUNBOOK.md](RUNBOOK.md)
- [docs/DATA_CONTRACTS.md](DATA_CONTRACTS.md)
