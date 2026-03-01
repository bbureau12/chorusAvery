# Repository Map

Purpose: quick navigation aid for where code and data live.

## Top-level folders

- `scripts/`: Operational scripts by pipeline domain
- `utils/`: Shared utility modules
- `docs/`: Architecture and process documentation
- `recordings/`: Raw, chunked, and clipped audio
- `models/`: Trained model files
- `db/`: SQLite databases
- `dataset/`, `dsp_dataset/`, `training/`: dataset and training artifacts
- `outputs/`, `results/`: generated outputs and analysis results

## scripts/ breakdown

- `scripts/import/`: source file ingestion helpers
- `scripts/augmentation/`: augmentation workflows
- `scripts/training/`: dataset building, training, and evaluation
- `scripts/validation/`: validation workflows
- `scripts/review/`: manual review tools
- `scripts/sound_isolation/`: filtering/clustering/fingerprint experiments
- `scripts/readings/`: environmental/temperature imports
- `scripts/file_maintenance/`: file reconciliation and integrity tasks
- `scripts/analysis/`: analytics and reporting scripts
- `scripts/one-off/`: one-time maintenance scripts

## Key entry scripts

- Ingestion: `scripts/import/import_new_soundfile.py`
- Chunking: `scripts/step_1_chunk_generator.py`
- Clip extraction: `scripts/step_2_clip_parserv2.py`
- BirdNET pass: `scripts/run_birdnet.py`
- Labeling: `scripts/sound_labeler.py`
- Dataset build: `scripts/training/dataset_builder.py`
- Training: `scripts/training/train_test_eval_latest.py`
- Validation: `scripts/validation/validate_self.py`

## Utility modules often reused

- `utils/generate_spectogram.py`
- `utils/augmentation_helpers.py`
- `utils/db.py`
- `utils/grad_cam.py`
- `utils/load_model.py`

## Notes for organization work

- Consolidate script naming conventions (`snake_case`, consistent verbs).
- Move one-off scripts behind clear archival markers.
- Gradually package common pipeline code into importable modules.
- Keep docs synchronized with script additions/removals.

## Related Docs

- [docs/PIPELINE.md](PIPELINE.md)
- [docs/RUNBOOK.md](RUNBOOK.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
