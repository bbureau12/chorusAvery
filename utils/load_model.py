import os
import json


def list_models(models_dir="./models"):
    models = sorted([
        f for f in os.listdir(models_dir)
        if f.endswith(".keras") and not f.startswith(".")
    ])
    for idx, name in enumerate(models, 1):
        print(f"{idx}. {name}")
    return models

def choose_model(models):
    choice = int(input("Select model by number: ")) - 1
    return models[choice]

def extract_species_id(model_path: str):
    import os, json

    # 3. Construct the expected path to the summary file
    results_folder = extract_results_folder(model_path)
    summary_path = os.path.join(results_folder, "results_summary.json")

    # 4. Load the summary and extract the non-zero class
    with open(summary_path) as f:
        summary = json.load(f)

    for class_id_str in summary["class_names"]:
        class_id = int(class_id_str)
        if class_id != 0:
            return class_id

    raise ValueError("No non-zero class found in summary.")

def extract_results_folder(model_path: str):
    import os, json

    # 1. Extract the model filename (no directory)
    model_name = os.path.basename(model_path)

    # 2. Remove .keras and _best if present
    if model_name.endswith(".keras"):
        model_name = model_name[:-6]
    if model_name.endswith("_best"):
        model_name = model_name[:-5]

    # 3. Construct the expected path to the summary file
    results_folder = os.path.join("./models/results", model_name)
    return results_folder