<p align="center">
  <h1 align="center">🌲 Chorus Avery</h1>
  <p align="center">
    <strong>Wildlife Audio Classification Platform</strong><br>
    Identifying frogs, canids, and hidden voices in Minnesota's wetlands using machine learning.
  </p>
  <p align="center">
    <a href="#species">Species Catalog</a> •
    <a href="#pipeline">ML Pipeline</a> •
    <a href="#api">API</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="docs/ARCHITECTURE.md">Architecture</a>
  </p>
</p>

---

## What is Chorus Avery?

**Chorus Avery** is an end-to-end machine learning platform for classifying wildlife sounds — particularly amphibians and mammals that traditional birdsong apps (like Merlin) overlook.

Named after the [Carlos Avery Wildlife Management Area](https://www.dnr.state.mn.us/wmas/carlos_avery/index.html) in Minnesota, the project processes long-form nature recordings into species identifications using a pipeline of custom-trained Keras CNN classifiers.

**Think Merlin, but for frogs.**

### Key Capabilities

- **Automated recording ingestion** — split hours-long recordings into analyzable chunks
- **BirdNET integration** — leverage pretrained bird detection as a first pass
- **Custom species classifiers** — binary CNN models trained on Mel spectrograms for species BirdNET can't handle
- **Environmental sound filtering** — separate biological sounds from road noise, human activity, and weather
- **CLI labeling tool** — manual annotation workflow with audio playback, spectrogram visualization, and clip editing
- **Grad-CAM interpretability** — see what the model is "hearing" in each spectrogram

---

<a id="species"></a>
## Species Catalog

### Animal Species

| Category | Species | Model Status |
|----------|---------|--------------|
| 🐸 Amphibians | American Toad (*Anaxyrus americanus*) | v5 — production |
| 🐸 Amphibians | Western Chorus Frog (*Pseudacris triseriata*) | v2 — production |
| 🐸 Amphibians | Eastern Grey Tree Frog (*Hyla versicolor*) | v5 — production |
| 🐸 Amphibians | Spring Peeper (*Pseudacris crucifer*) | v2 — production |
| 🐺 Mammals | Coyote (*Canis latrans*) | v1 — experimental |
| 🐺 Mammals | Grey Wolf (*Canis lupus*) | v1 — experimental |
| 🐿️ Mammals | Eastern Chipmunk (*Tamias striatus*) | v1 — experimental |
| 🐿️ Mammals | Red Squirrel (*Tamiasciurus hudsonicus*) | v1 — experimental |

### Environmental Sound Classifiers

| Classifier | Purpose |
|------------|---------|
| Bio/Mechanical Differentiation | Separate biological from human-made sounds |
| Road Noise | Filter vehicle/traffic noise |
| Human/Mechanical | Detect human activity near recording sites |
| Natural Non-Biological | Classify rain, wind, water sounds |

---

<a id="pipeline"></a>
## ML Pipeline

```
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Record    │────▶│   Chunk     │────▶│   Detect    │────▶│   Extract   │
  │  (field)    │     │  (5-min)    │     │  (BirdNET)  │     │  (clips)    │
  └─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                     │
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────▼───────┐
  │   Deploy    │◀────│   Train     │◀────│   Build     │◀────│   Label     │
  │  (API)      │     │  (Keras)    │     │  (dataset)  │     │  (CLI)      │
  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Record** — Long-form `.wav` recordings from field recorders at Carlos Avery WMA
2. **Chunk** — Split into 5-minute segments, resample to 16kHz mono
3. **Detect** — Run BirdNET Analyzer (≥0.6 confidence threshold)
4. **Extract** — Dynamic dBFS-based silence detection → non-silent clips
5. **Label** — CLI tool with playback, spectrogram view, species search
6. **Build** — Generate 224×224 Mel spectrograms with augmentation (noise overlay, volume polarization)
7. **Train** — Keras CNN with EarlyStopping, ReduceLR, ModelCheckpoint
8. **Deploy** — FastAPI service on AWS (in progress)

### Spectrogram Configuration

All classifiers use consistent Mel spectrogram parameters:
- **128 Mel bands** at **16 kHz** sample rate
- **8 kHz max frequency** — captures the full range of frog/mammal vocalizations
- **224 × 224 px** output — compatible with transfer learning architectures

---

<a id="api"></a>
## API (In Development)

REST API for species identification from audio recordings.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + loaded model count |
| `/species` | GET | List all supported species with metadata |
| `/identify` | POST | Upload audio → ranked species predictions |

**Tech stack:** FastAPI + TensorFlow Serving + Streamlit frontend

See [Architecture Docs](docs/ARCHITECTURE.md) for deployment details.

---

<a id="quick-start"></a>
## Quick Start

### Prerequisites
- Python 3.10+
- FFmpeg (for audio processing)

### Setup

```bash
# Clone the repository
git clone https://github.com/bbureau12/chorusAvery.git
cd chorusAvery

# Create virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\Activate.ps1    # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Step 1: Chunk long recordings into 5-min segments
python scripts/step_1_chunk_generator.py

# Step 2: Extract non-silent clips
python scripts/step_2_clip_parserv2.py

# Step 3: Run BirdNET detection
python scripts/run_birdnet.py

# Step 4: Label clips manually
python scripts/sound_labeler.py

# Step 5: Build training dataset
python scripts/training/dataset_builder.py

# Step 6: Train a classifier
python scripts/training/train_test_eval_latest.py
```

---

## Project Structure

```
chorusAvery/
├── scripts/                    # ML pipeline scripts
│   ├── step_1_chunk_generator.py    # Audio chunking (5-min segments)
│   ├── step_2_clip_parserv2.py      # Clip extraction (silence detection)
│   ├── run_birdnet.py               # BirdNET analysis
│   ├── sound_labeler.py             # CLI labeling tool
│   ├── training/                    # Dataset building & model training
│   │   ├── dataset_builder.py
│   │   ├── train_test_eval_latest.py
│   │   ├── collection/             # Training data collection
│   │   └── eval/                   # Model evaluation & Grad-CAM
│   ├── validation/                  # Model validation
│   ├── augmentation/                # Data augmentation
│   └── hugging_face/               # AST transformer experiments
├── utils/                      # Shared utility modules
│   ├── generate_spectogram.py       # Mel spectrogram generation (core)
│   ├── db.py                        # SQLite connection
│   ├── grad_cam.py                  # Grad-CAM visualization
│   └── ...
├── api/                        # FastAPI service (planned)
├── frontend/                   # Streamlit app (planned)
├── docs/                       # Architecture & planning docs
│   ├── ARCHITECTURE.md
│   ├── REORGANIZATION_PLAN.md
│   └── DEPENDENCY_MAP.md
├── models/                     # Trained .keras weights (.gitignored)
├── recordings/                 # Audio data (.gitignored)
└── db/                         # SQLite database (.gitignored)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **ML Framework** | TensorFlow / Keras |
| **Audio Processing** | librosa, pydub, scipy |
| **Bird Detection** | BirdNET Analyzer |
| **Visualization** | matplotlib, seaborn, Grad-CAM |
| **Database** | SQLite |
| **API** | FastAPI (planned) |
| **Frontend** | Streamlit (planned) |
| **Deployment** | AWS ECS + S3 + CloudFront (planned) |

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) — System design, data flow, AWS deployment plan
- [Reorganization Plan](docs/REORGANIZATION_PLAN.md) — Phased roadmap for productionization
- [Dependency Map](docs/DEPENDENCY_MAP.md) — Import graph for safe refactoring

---

## About

Built by **Beau Bureau** as a machine learning portfolio project, blending passion for wildlife conservation with practical ML engineering. The project started as a way to identify frog species in long-form nature recordings from the Carlos Avery WMA — calls that automated tools like Merlin consistently miss.

**Chorus Avery** is both a scientific tool and a meditation — a way of honoring the living world one chirp at a time.

---

## License

MIT License. All recordings and data belong to their original recordists unless otherwise stated.