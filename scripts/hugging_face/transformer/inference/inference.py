import json, sys
from transformers import AutoProcessor, AutoModelForAudioClassification
import torchaudio

MODEL_DIR = "out/ast/best"   # folder saved by training
TOPK = 5

def main(wav_path):
    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    model = AutoModelForAudioClassification.from_pretrained(MODEL_DIR)
    with open(f"{MODEL_DIR}/labels.json") as f:
        meta = json.load(f)
    id2label = {int(k): v for k, v in meta["id2label"].items()}

    wav, sr = torchaudio.load(wav_path)
    wav = wav.mean(dim=0).unsqueeze(0)  # mono
    inputs = processor(wav.squeeze().numpy(), sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = logits.softmax(dim=-1).squeeze().tolist()

    topk = sorted(list(enumerate(probs)), key=lambda x: x[1], reverse=True)[:TOPK]
    result = [{"label": id2label[i], "score": float(s)} for i, s in topk]
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    import torch
    if len(sys.argv) != 2:
        print("Usage: python inference/predict.py <path/to/clip.wav>")
        sys.exit(1)
    main(sys.argv[1])
