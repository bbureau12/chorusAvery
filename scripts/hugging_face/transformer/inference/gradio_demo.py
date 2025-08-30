import json, torch
import gradio as gr
import torchaudio
from transformers import AutoProcessor, AutoModelForAudioClassification

MODEL_DIR = "out/ast/best"

processor = AutoProcessor.from_pretrained(MODEL_DIR)
model = AutoModelForAudioClassification.from_pretrained(MODEL_DIR).eval()
with open(f"{MODEL_DIR}/labels.json") as f:
    meta = json.load(f)
id2label = {int(k): v for k, v in meta["id2label"].items()}

def predict(audio):
    wav_path = audio
    wav, sr = torchaudio.load(wav_path)
    wav = wav.mean(dim=0)  # mono
    inputs = processor(wav.numpy(), sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1).squeeze().tolist()
    labeled = {id2label[i]: float(p) for i, p in enumerate(probs)}
    # Sort & return
    return dict(sorted(labeled.items(), key=lambda kv: kv[1], reverse=True))

demo = gr.Interface(
    fn=predict,
    inputs=gr.Audio(type="filepath", label="Upload or record 2.5s clip"),
    outputs=gr.Label(num_top_classes=5),
    title="Chorus Avery — Frog Classifier (MVP)"
)

if __name__ == "__main__":
    demo.launch()
