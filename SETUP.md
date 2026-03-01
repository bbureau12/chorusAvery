# Setup Guide

This setup is for local development on Windows PowerShell, with notes for other platforms.

## Prerequisites

- Python 3.10+
- FFmpeg available on PATH
- Git

## 1. Clone and enter repository

```powershell
git clone https://github.com/bbureau12/chorusAvery.git
cd chorusAvery
```

## 2. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure BirdNET Analyzer

Repository includes `BirdNET-Analyzer/`.
Place required BirdNET model files in:

`BirdNET-Analyzer/BirdNET_GLOBAL_MODEL/`

Expected files:
- `model.tflite`
- `labels.txt`
- `metadata.json`

## 5. Verify key folders

Confirm these exist before running pipeline scripts:

- `recordings/raw/`
- `recordings/chunks/` (created by chunking workflow if missing)
- `recordings/clips/` (created by clip extraction workflow if missing)
- `models/`
- `db/`

## 6. Verify database path expectations

Most scripts expect one of the following DB locations:

- `./chorusAvery.db`
- `./db/chorusAvery.db`

If a script fails with missing DB, inspect that script's `DATABASE_PATH` constant and align it.

## 7. Smoke test commands

```powershell
python scripts\step_1_chunk_generator.py
python scripts\step_2_clip_parserv2.py
python scripts\run_birdnet.py
```

## Troubleshooting

- FFmpeg not found: install FFmpeg and restart shell.
- Module import errors from sibling folders: run from repo root.
- BirdNET model missing: verify files under `BirdNET-Analyzer/BirdNET_GLOBAL_MODEL/`.
- SQLite errors: confirm DB file path and table availability.

## Related Docs

- [README.md](README.md)
- [docs/PIPELINE.md](docs/PIPELINE.md)
- [docs/RUNBOOK.md](docs/RUNBOOK.md)
