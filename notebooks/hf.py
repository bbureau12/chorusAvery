from datasets import load_dataset

minds = load_dataset("PolyAI/minds14", name="en-AU", split="train")
example = minds[0]
id2label = minds.features["intent_class"].int2str
print(id2label(example["intent_class"]))