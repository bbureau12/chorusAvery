# Pipeline Guide

This document describes the practical end-to-end pipeline currently implemented in this repository.

## Overview

1. Import or collect raw source files.
2. Split long recordings into chunks.
3. Extract non-silent candidate clips.
4. Run BirdNET detections.
5. Label clips for species/non-species classes.
6. Build spectrogram datasets.
7. Train and evaluate models.
8. Validate models against cohorts/files/self-labeled sets.

## Stage 1: Import and ingestion

Representative script:
- `scripts/import/import_new_soundfile.py`

Purpose:
- Detect new source audio files and copy/import them into project raw storage.

## Stage 2: Chunk long recordings

Primary script:
- `scripts/step_1_chunk_generator.py`

Purpose:
- Convert long recordings into manageable fixed-duration segments.

## Stage 3: Extract clips

Primary script:
- `scripts/step_2_clip_parserv2.py`

Purpose:
- Detect non-silent regions and export clips for review/modeling.

## Stage 4: Run BirdNET

Primary script:
- `scripts/run_birdnet.py`

Purpose:
- Run BirdNET over chunks and capture detections for downstream use.

## Stage 5: Label and review

Primary scripts:
- `scripts/sound_labeler.py`
- `scripts/filter_review_tool.py`
- `scripts/review/species_review.py`

Purpose:
- Human-in-the-loop labeling, triage, and quality control.

## Stage 6: Build datasets

Primary scripts:
- `scripts/training/dataset_builder.py`
- `scripts/training/collection/collect_negative_clips.py`
- `scripts/augmentation/species_nonspecies_augmentor.py`

Purpose:
- Prepare training splits and spectrograms, including augmentation and negatives.

## Stage 7: Train and evaluate

Primary scripts:
- `scripts/training/train_test_eval_latest.py`
- `scripts/training/eval/evaluate_with_gradcam.py`
- `scripts/training/eval/mixed_species_evaluator.py`

Purpose:
- Train model versions, compute metrics, and inspect model behavior.

## Stage 8: Validate

Primary scripts:
- `scripts/validation/validate_self.py`
- `scripts/validation/validate_file.py`
- `scripts/validation/validate_cohorts.py`

Purpose:
- Assess quality against different validation sets and contexts.

## Outputs and artifacts

- Audio artifacts: `recordings/`, `outputs/`, `results/`
- Model artifacts: `models/`
- Intermediate datasets: `dataset/`, `dsp_dataset/`, `training/`
- Metadata and labels: SQLite DB files and CSV outputs

## Known operational constraints

- Not yet a fully packaged Python module.
- Some scripts rely on local path assumptions and `sys.path` manipulation.
- Several scripts are experimental or one-off; rely on runbook shortcuts for routine work.

## Related Docs

- [docs/RUNBOOK.md](RUNBOOK.md)
- [docs/REPO_MAP.md](REPO_MAP.md)
- [docs/DEPENDENCY_MAP.md](DEPENDENCY_MAP.md)
