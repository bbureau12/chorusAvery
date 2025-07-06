import json
import os

class SpecWriter:
    def __init__(self, clip_length_ms, spectrogram_settings, audio_settings, augmentations=None):
        self.specs = {
            "clip_length_ms": clip_length_ms,
            "spectrogram": spectrogram_settings,
            "audio": audio_settings,
        }
        if augmentations:
            self.specs["augmentations"] = augmentations

    def save(self, base_dir, filename="model_specs.json"):
        spec_path = os.path.join(base_dir, filename)
        with open(spec_path, 'w') as f:
            json.dump(self.specs, f, indent=4)
        print(f"📄 Saved model specs to: {spec_path}")

    @staticmethod
    def default_spectrogram_settings():
        return {
            "type": "mel",
            "lib": "librosa",
            "n_mels": 128,
            "fmax": 8000,
            "figure_size": [4, 4],
            "dpi": 150,
            "target_sample_rate": 16000
        }

    @staticmethod
    def default_audio_settings():
        return {
            "frame_rate": 16000,
            "channels": 1
        }