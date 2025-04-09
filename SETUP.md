# 🐦 Chorus Avery - Setup Instructions

Welcome to **Chorus Avery**, a project dedicated to listening to and identifying birdsong using BirdNET Analyzer and AI tools.

---

## 📦 Setup Instructions

### 1. Clone This Repository
```bash
git clone https://github.com/your-username/chorus-avery.git
cd chorus-avery
```

### 2. Set Up a Python Virtual Environment
```bash
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

### 3. Install FFmpeg (Required for Audio Processing)
- Download from: https://www.gyan.dev/ffmpeg/builds/
- Extract and add the `bin/` folder to your system PATH.

### 4. Set Up BirdNET Analyzer
Inside this project, you’ll find a folder named `BirdNET-Analyzer/`. To activate BirdNET:

- Download the latest model files from [BirdNET Cornell](https://birdnet.cornell.edu/)
- Place them in:
  ```
  BirdNET-Analyzer/BirdNET_GLOBAL_MODEL/
  ```
  Required files:
  - `model.tflite`
  - `labels.txt`
  - `metadata.json`

---

## ✅ You’re Ready!
Drop `.wav` files into `recordings/raw/`, and run `scripts/run_birdnet.py` to analyze them.

Happy listening! 🌲🐦
