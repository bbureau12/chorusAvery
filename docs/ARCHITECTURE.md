# Chorus Avery — Architecture

> Wildlife audio classification platform for identifying species calls in Minnesota.  
> Think Merlin, but for frogs, canids, and everything the automated tools miss.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CHORUS AVERY                               │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  Recording   │  ML Pipeline │  Inference   │   Presentation     │
│  Ingestion   │  & Training  │  API         │   Layer            │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ chunk_gen    │ dataset_     │ FastAPI      │ Streamlit UI       │
│ clip_parser  │   builder    │ /identify    │ Upload & Results   │
│ birdnet_run  │ train_eval   │ /species     │ Spectrogram View   │
│ sound_label  │ grad_cam     │ /health      │ Species Gallery    │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
   ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
   │ SQLite │   │  .keras  │   │   S3     │   │ CloudFront   │
   │   DB   │   │  Models  │   │ (models) │   │ (static)     │
   └────────┘   └──────────┘   └──────────┘   └──────────────┘
```

---

## ML Pipeline

The pipeline flows through four major stages:

### 1. Data Ingestion

| Step | Script | Description |
|------|--------|-------------|
| **Chunk** | `scripts/step_1_chunk_generator.py` | Splits long-form `.wav`/`.mp3` into 5-min chunks (16kHz mono), logs to `SourceFiles` table |
| **Detect** | `scripts/run_birdnet.py` | Runs BirdNET Analyzer on chunks (≥0.6 confidence), writes to `Detections` table |
| **Extract** | `scripts/step_2_clip_parserv2.py` | Dynamic dBFS-based silence detection → extract non-silent clips + JSON sidecars |

### 2. Labeling & Annotation

| Step | Script | Description |
|------|--------|-------------|
| **Label** | `scripts/sound_labeler.py` | CLI labeler with playback, spectrogram view, species search, clip splitting/trimming |
| **Review** | `scripts/filter_review_tool.py` | Secondary Y/N review tool for pre-filtered clips |

### 3. Training

| Step | Script | Description |
|------|--------|-------------|
| **Build Dataset** | `scripts/training/dataset_builder.py` | Mel spectrograms (224×224) + augmentation → train/val/test splits |
| **Augment** | `scripts/augmentation/*.py` | Noise overlay, volume polarization, negative sample generation |
| **Train** | `scripts/training/train_test_eval_latest.py` | Keras CNN with EarlyStopping, ReduceLR, ModelCheckpoint |
| **Evaluate** | `scripts/training/eval/*.py` | Confusion matrix, ROC, Grad-CAM visualization |

### 4. Validation

| Step | Script | Description |
|------|--------|-------------|
| **Self-validate** | `scripts/validation/validate_self.py` | Validate against labeled clips in DB |
| **Cohort-validate** | `scripts/validation/validate_cohorts.py` | Cross-cohort validation with spec writer |
| **File-validate** | `scripts/validation/validate_file.py` | Validate against specific audio files |

---

## Species & Sound Classification

### Animal Species (Custom Binary Classifiers)

| Category | Species | Model Versions |
|----------|---------|----------------|
| Amphibians | American Toad | v1–v5 |
| Amphibians | Chorus Frog | v1–v2 |
| Amphibians | Eastern Grey Tree Frog | v1–v5 |
| Amphibians | Spring Peeper | v1–v2 |
| Mammals | Coyote | v1 |
| Mammals | Eastern Chipmunk | v1 |
| Mammals | Grey Wolf | v1 |
| Mammals | Red Squirrel | v1 |

### Non-Animal Sound Classifiers

| Model | Purpose |
|-------|---------|
| `bio_mechanical_differentiation` | Bio vs. mechanical sound separation |
| `human_mechanical` | Human/mechanical activity detection |
| `road_noise_classifier` | Vehicle/road noise filtering |
| `noise_pollution` | General noise pollution classification |
| `natural_non_biological_multi_label` | Rain, wind, water, etc. |

### Experimental: Audio Spectrogram Transformer (AST)

Located in `scripts/hugging_face/transformer/` — a Hugging Face Transformers-based pipeline for multi-class audio classification using a pretrained AST model.

---

## Data Architecture

### SQLite Database (`chorusAvery.db`)

**Core tables:**

| Table | Purpose |
|-------|---------|
| `Species` | Species catalog (name, code, scientific name, animal type) |
| `NonAnimalSounds` | Non-animal sound categories with parent `SoundCategories` |
| `SourceFiles` | Recording metadata (filename, location, timestamps) |
| `Clips` | Extracted audio clips (path, UTC timestamps, dBFS stats) |
| `ClipAnnotations` | Labels linking clips → species/sounds (verified flag, AI certainty) |
| `Detections` | BirdNET detection results (species, confidence, timing) |
| `Locations` | Recording sites (lat/lon) |
| `Location_Temperature` | Weather data (temp, rain, wind, UV, solar radiation) |
| `MysterySegments` | Unidentified sounds for future review |
| `Plants`, `Fungus` | Natural history tracking |

### File Storage

| Directory | Content |
|-----------|---------|
| `recordings/raw/` | Original long-form recordings |
| `recordings/chunks/` | 5-minute chunks (transient) |
| `recordings/clips/` | Extracted audio clips + JSON metadata |
| `recordings/training_data/` | Labeled clips organized by year |
| `recordings/model/{slug}/` | Spectrogram datasets (train/val/test) |
| `models/` | Trained `.keras` model weights |
| `data/` | BirdNET result CSVs |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.x |
| ML Framework | TensorFlow / Keras (CNN classifiers) |
| Transformer ML | Hugging Face Transformers (AST) |
| Audio Processing | pydub, librosa, scipy, soundfile |
| Bird Detection | BirdNET Analyzer (TFLite) |
| Spectrogram | librosa (128 Mel bands, 224×224 PNG) |
| Image Processing | OpenCV, Pillow |
| Visualization | matplotlib, seaborn |
| ML Metrics | scikit-learn |
| Database | SQLite3 |
| Weather API | Ambient Weather API |
| Audio Playback | simpleaudio |
| API (planned) | FastAPI |
| Frontend (planned) | Streamlit |
| Deployment (planned) | AWS (S3, ECS/Lambda, CloudFront) |

---

## Spectrogram Configuration

All models use consistent Mel spectrogram parameters:

| Parameter | Value |
|-----------|-------|
| Sample Rate | 16,000 Hz |
| Mel Bands | 128 |
| Max Frequency | 8,000 Hz |
| Output Size | 224 × 224 px |
| Colormap | viridis |
| Format | PNG |

Defined centrally in `utils/generate_spectogram.py` (`generate_mel_spectrogram()` and `load_spectrogram()`).

---

## Key Utility Modules

| Module | Purpose | Consumers |
|--------|---------|-----------|
| `utils/generate_spectogram.py` | Mel spectrogram generation & loading | 13 scripts (most critical) |
| `utils/augmentation_helpers.py` | Audio augmentation (noise, volume, padding) | 6 training pipelines |
| `utils/db.py` | SQLite connection factory | Internal utils |
| `utils/grad_cam.py` | Grad-CAM visualization | Evaluation scripts |
| `utils/entityfinder.py` | Species/sound entity lookup from DB | Augmentation pipeline |
| `utils/insert_detections.py` | BirdNET detection DB insertion | Import pipeline |
| `utils/load_model.py` | Model listing, selection, version extraction | Evaluation scripts |
| `utils/split_wav.py` | WAV splitting with volume boost | BirdNET runner |

---

## AWS Deployment Plan

```
                    ┌──────────────┐
                    │  CloudFront  │
                    │  (CDN)       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │   S3 Bucket     │      │   API Gateway   │
     │ (Streamlit /    │      │   (HTTPS)       │
     │  static assets) │      └────────┬────────┘
     └─────────────────┘               │
                              ┌────────▼────────┐
                              │  ECS Fargate    │
                              │  (FastAPI +     │
                              │   TF models)    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  S3 Bucket      │
                              │ (model weights  │
                              │  + audio upload)│
                              └─────────────────┘
```

| Service | Purpose |
|---------|---------|
| **S3** | Model artifact storage + audio file uploads |
| **ECS Fargate** | Containerized FastAPI service with TensorFlow |
| **API Gateway** | Public HTTPS endpoint with rate limiting |
| **CloudFront** | CDN for Streamlit/static frontend |
| **ECR** | Docker image registry |
| **CloudWatch** | Logging & monitoring |
