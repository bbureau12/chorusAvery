# Reorganization Plan — Chorus Avery

> This document outlines the phased approach to restructuring the project from a collection of 
> ML scripts into a portfolio-ready, deployable application with an API and UI layer.
>
> **Guiding principle: nothing breaks.** Each phase is independently testable.

---

## Current State

The project is a working ML pipeline with:
- ~60 Python scripts across `scripts/` and `utils/`
- ~40 trained `.keras` models
- SQLite database with 30 tables
- No API, no web frontend, no deployment infrastructure
- No `__init__.py` files — all cross-module imports use `sys.path` hacks
- `utils/datetime.py` shadows the stdlib `datetime` module

## Target State

```
chorusAvery/
├── README.md                   # Portfolio-grade overview
├── pyproject.toml              # Single dependency file (replaces requirements.txt)
├── docker-compose.yml          # Local dev environment
├── .gitignore                  # Cleaned up
│
├── ml/                         # All ML code (reorganized from scripts/ + utils/)
│   ├── __init__.py
│   ├── pipeline/               # Data ingestion & processing
│   │   ├── __init__.py
│   │   ├── chunk_generator.py      ← scripts/step_1_chunk_generator.py
│   │   ├── clip_parser.py          ← scripts/step_2_clip_parserv2.py
│   │   ├── birdnet_runner.py       ← scripts/run_birdnet.py
│   │   └── sound_labeler.py        ← scripts/sound_labeler.py
│   ├── training/               # Model training
│   │   ├── __init__.py
│   │   ├── dataset_builder.py      ← scripts/training/dataset_builder.py
│   │   ├── trainer.py              ← scripts/training/train_test_eval_latest.py
│   │   ├── evaluator.py            ← scripts/training/eval/
│   │   └── augmentation.py         ← scripts/augmentation/
│   ├── inference/              # Model loading & prediction (NEW)
│   │   ├── __init__.py
│   │   ├── classifier.py           # Load models, run inference, ensemble
│   │   ├── audio_processor.py      # Audio preprocessing for inference
│   │   └── spectrogram.py          ← utils/generate_spectogram.py
│   ├── validation/
│   │   ├── __init__.py
│   │   └── validators.py           ← scripts/validation/
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── db.py                   ← utils/db.py
│       ├── audio.py                ← utils/split_wav.py, utils/boost_if_needed.py
│       ├── spectrogram.py          ← utils/generate_spectogram.py
│       └── gradcam.py              ← utils/grad_cam.py
│
├── api/                        # FastAPI service
│   ├── __init__.py
│   ├── main.py                 # App entrypoint
│   ├── routers/
│   │   ├── identify.py         # POST /identify
│   │   ├── species.py          # GET /species
│   │   └── health.py           # GET /health
│   ├── services/
│   │   ├── classifier.py       # Wraps ml/inference/
│   │   └── audio.py            # Audio handling
│   ├── schemas/
│   │   ├── prediction.py       # Response models
│   │   └── species.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Streamlit app
│   ├── app.py                  # Main Streamlit entry
│   ├── pages/
│   │   ├── identify.py         # Upload & identify page
│   │   ├── species.py          # Species catalog
│   │   └── about.py            # Project info
│   └── requirements.txt
│
├── infra/                      # AWS deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── deploy.sh
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── REORGANIZATION_PLAN.md
│   └── DEPENDENCY_MAP.md
│
├── data/                       # .gitignored
├── models/                     # .gitignored
├── recordings/                 # .gitignored
└── db/                         # .gitignored
```

---

## Phases

### Phase 0: Documentation & Hygiene (THIS PHASE) ✅

**Goal:** Document everything, fix hazards, clean the repo — **zero code changes** to existing scripts.

| Task | Status | Notes |
|------|--------|-------|
| Create `docs/ARCHITECTURE.md` | ✅ | Full system architecture |
| Create `docs/DEPENDENCY_MAP.md` | ✅ | Import graph for safe refactoring |
| Create `docs/REORGANIZATION_PLAN.md` | ✅ | This document |
| Fix `.gitignore` gaps | 🔲 | Add missing exclusions |
| Fix `.gitignore` typo | 🔲 | `*.pngchorus_frog_classifier.h5` → two lines |
| Remove API keys from `settings.json` tracking | ✅ | Already in `.gitignore` |
| Write portfolio README | 🔲 | Replace current README |
| Remove dead code files | 🔲 | 3 files identified |

---

### Phase 1: Proper Python Packaging (safe, no moves)

**Goal:** Make the project importable without `sys.path` hacks.

| Task | Notes |
|------|-------|
| Add `__init__.py` to `utils/`, `scripts/`, and all subdirectories | Enables proper `from utils.X import Y` |
| Rename `utils/datetime.py` → `utils/time_helpers.py` | Eliminates stdlib shadow |
| Fix `utils/split_wav.py` bare import | `from boost_if_needed` → `from utils.boost_if_needed` |
| Fix HF transformer bare imports | Standardize to project-root-relative |
| Create `pyproject.toml` with `[project.scripts]` entry points | Replace individual `sys.path` hacks |
| Test: all existing scripts still run | **Gate — do not proceed until verified** |

---

### Phase 2: Create Inference Layer

**Goal:** Extract the minimum code needed to **load a model and classify an audio clip**.

This is the bridge between the ML pipeline and the API — no training code, no labeling, just:
1. Accept audio bytes/file
2. Resample to 16kHz mono
3. Generate Mel spectrogram (224×224)
4. Run through ensemble of species classifiers
5. Return ranked predictions with confidence scores

| Task | Notes |
|------|-------|
| Create `ml/inference/__init__.py` | Package init |
| Create `ml/inference/audio_processor.py` | Extract from `step_2_clip_parserv2.py` |
| Create `ml/inference/spectrogram.py` | Thin wrapper around `utils/generate_spectogram.py` |
| Create `ml/inference/classifier.py` | Model loading + batch inference |
| Write unit tests | Test with a sample `.wav` file |
| Test: inference works standalone | **Gate** |

---

### Phase 3: FastAPI Service

**Goal:** Expose inference as a REST API.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + model count |
| `/species` | GET | List supported species with metadata |
| `/identify` | POST | Upload audio file → species predictions |
| `/identify/{id}/spectrogram` | GET | Retrieve spectrogram for a prediction |

| Task | Notes |
|------|-------|
| Create `api/main.py` | FastAPI app with CORS |
| Create `api/routers/` | Route handlers |
| Create `api/services/` | Business logic wrapping `ml/inference/` |
| Create `api/schemas/` | Pydantic request/response models |
| Add OpenAPI docs | Auto-generated by FastAPI |
| Write integration tests | Upload audio → check predictions |
| Create `Dockerfile` | `python:3.10-slim` + TensorFlow |
| Test: `docker build && docker run` | **Gate** |

---

### Phase 4: Streamlit Frontend

**Goal:** Build a user-friendly web interface.

| Page | Description |
|------|-------------|
| **Identify** | Drag-and-drop audio upload → real-time spectrogram + predictions |
| **Species Catalog** | Browse supported species with example spectrograms |
| **About** | Project story, architecture diagram, links |

| Task | Notes |
|------|-------|
| Create `frontend/app.py` | Multi-page Streamlit app |
| Implement audio upload with preview | Use `st.audio()` |
| Call API `/identify` endpoint | Display results as cards |
| Show spectrogram visualization | Inline matplotlib/plotly |
| Species catalog page | Pull from `/species` endpoint |
| Test: local end-to-end | Upload → API → results displayed |

---

### Phase 5: AWS Deployment

**Goal:** Deploy to AWS for public access.

| Task | Notes |
|------|-------|
| Push Docker image to ECR | API container |
| Deploy API on ECS Fargate | Or Lambda if cold start is acceptable |
| Upload models to S3 | With versioning |
| Set up API Gateway | HTTPS + rate limiting |
| Deploy Streamlit on EC2 or ECS | Or use Streamlit Cloud |
| Configure CloudFront | CDN for frontend |
| Set up domain + SSL | Optional: custom domain |

---

### Phase 6: ML Code Reorganization (optional, deferred)

**Goal:** Move existing scripts into the `ml/` package structure.

This is intentionally last because:
- The existing scripts **work** and don't need to move for the API/frontend to function
- Moving files requires updating all `sys.path` hacks and imports
- The inference layer (Phase 2) is a **clean extraction**, not a refactor

If/when you do this:
1. Move files one directory at a time
2. Update imports in that directory
3. Run all affected scripts to verify
4. Commit after each directory

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing scripts | Phase 1 gate: test all scripts before proceeding |
| Model files too large for deployment | S3 model hosting with lazy loading |
| TensorFlow container too large | Use `tensorflow-cpu` slim image (~500MB vs ~2GB) |
| Cold start latency | Pre-warm models on container startup |
| SQLite not suitable for production | Phase 5 can optionally migrate to RDS PostgreSQL |

---

## What NOT to Move (stays `.gitignored`)

| Item | Reason |
|------|--------|
| `recordings/` | Audio data (potentially GB) |
| `models/*.keras` | Trained weights (use S3 + model registry) |
| `db/chorusAvery.db` | Local SQLite database |
| `training/` | Training spectrogram datasets |
| `dataset/`, `dsp_dataset/` | Raw/processed datasets |
| `misclassified/` | Debugging artifacts |
| `env/`, `.venv/` | Python environments |
| `settings.json` | API keys |
| `BirdNET-Analyzer/` | Git submodule / external dependency |
