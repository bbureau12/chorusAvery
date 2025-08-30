from transformers import AutoConfig, AutoProcessor, AutoModelForAudioClassification, TrainingArguments, Trainer
import numpy as np
from sklearn.metrics import f1_score, classification_report
import os, json
from dataset_audio_2 import load_manifest

MODEL_ID = "MIT/ast-finetuned-audioset-10-10-0.4593"
MANIFEST = "data/slices_hf/metadata_audio_multiclass.csv"
OUT_DIR = "out/ast"

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"macro_f1": f1_score(labels, preds, average="macro")}

def collate_fn(processor):
    def _fn(batch):
        audio = [b["audio"] for b in batch]
        inputs = processor([a["array"] for a in audio],
                           sampling_rate=audio[0]["sampling_rate"],
                           return_tensors="pt", padding=True)
        inputs["labels"] = [b["label_id"] for b in batch]
        return inputs
    return _fn

def main():
    ds = load_manifest(MANIFEST)
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    config = AutoConfig.from_pretrained(
        MODEL_ID,
        num_labels=len(ds["labels"]),
        label2id=ds["label2id"],
        id2label=ds["id2label"]
    )
    model = AutoModelForAudioClassification.from_pretrained(MODEL_ID, config=config)

    args = TrainingArguments(
        output_dir=OUT_DIR,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=5e-5,
        num_train_epochs=8,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=50
    )

    trainer = Trainer(
        model=model,
        args=args,
        data_collator=collate_fn(processor),
        train_dataset=ds["train"],
        eval_dataset=ds["val"],
        compute_metrics=compute_metrics
    )
    trainer.train()

    # Save model + label maps
    best_dir = os.path.join(OUT_DIR, "best")
    trainer.save_model(best_dir)
    with open(os.path.join(best_dir, "labels.json"), "w") as f:
        json.dump({"labels": ds["labels"], "label2id": ds["label2id"], "id2label": ds["id2label"]}, f)

    # Quick final report on test
    outputs = trainer.predict(ds["test"])
    preds = outputs.predictions.argmax(axis=-1)
    print(classification_report(ds["test"]["label_id"], preds, target_names=ds["labels"]))

if __name__ == "__main__":
    main()
