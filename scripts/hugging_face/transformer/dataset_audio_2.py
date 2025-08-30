from datasets import Dataset, Audio
import pandas as pd

def load_manifest(path, sampling_rate=16000):
    df = pd.read_csv(path)
    labels = sorted(df["label"].unique())
    label2id = {l:i for i,l in enumerate(labels)}
    id2label = {i:l for l,i in label2id.items()}

    ds_all = Dataset.from_pandas(df.assign(audio=df["filepath"]))
    ds_all = ds_all.cast_column("audio", Audio(sampling_rate=sampling_rate))
    ds_all = ds_all.map(lambda ex: {"label_id": label2id[ex["label"]]})

    return {
        "labels": labels,
        "label2id": label2id,
        "id2label": id2label,
        "train": ds_all.filter(lambda ex: ex["subset"]=="train"),
        "val":   ds_all.filter(lambda ex: ex["subset"]=="val"),
        "test":  ds_all.filter(lambda ex: ex["subset"]=="test"),
    }
