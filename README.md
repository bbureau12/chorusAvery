# Chorus Avery

Chorus Avery is an audio ML project for logging and classifying wildlife sounds, with a strong focus on Minnesota frog species.

This repository contains the full working pipeline: recording ingestion, clip extraction, labeling, dataset creation, model training, and evaluation.

## Start Here

1. Read [SETUP.md](SETUP.md) for environment setup.
2. Read [docs/PIPELINE.md](docs/PIPELINE.md) for the end-to-end flow.
3. Use [docs/RUNBOOK.md](docs/RUNBOOK.md) for common day-to-day commands.
4. Use [docs/REPO_MAP.md](docs/REPO_MAP.md) to navigate scripts and folders.
5. Use [docs/SCRIPT_REFERENCE.md](docs/SCRIPT_REFERENCE.md) for script interfaces and usage notes.
6. Use [docs/DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) for database/filesystem contracts.
7. Use [docs/ORGANIZATION_PROPOSAL.md](docs/ORGANIZATION_PROPOSAL.md) for phased cleanup work.

## Current Goals

- Keep ingestion and labeling repeatable.
- Improve model quality for frog species detection.
- Reduce ambiguity between similar calls.
- Continue organizing the project into a cleaner, easier-to-maintain structure.

## Project Snapshot

- Language: Python
- ML framework: TensorFlow/Keras
- Audio stack: pydub, librosa, scipy
- Primary storage: SQLite (`chorusAvery.db`)
- External detector: BirdNET Analyzer

## Repository Layout (high-level)

- `scripts/` pipeline, training, validation, and utilities
- `utils/` shared helper modules
- `recordings/` raw/chunked/clip audio data
- `models/` trained model artifacts
- `db/` sqlite database files
- `docs/` project documentation

For detailed architecture and planning docs, see:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md)
- [docs/REORGANIZATION_PLAN.md](docs/REORGANIZATION_PLAN.md)

## Important Notes

- Many scripts are operational and script-first (not yet fully packaged).
- Some imports currently rely on `sys.path` adjustments.
- Large data/model folders should remain out of git where possible.

## Suggested Next Documentation Steps

- Add per-script argument reference for high-use scripts.
- Add model registry doc (naming/versioning/metrics).
- Add data policy doc for recordings, labels, and derived artifacts.
