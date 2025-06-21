# lora_manager.py

import os
import json
import shutil

CONFIG_PATH = "astraea_models/config.json"
LAYERS_DIR = "astraea_models/lora_layers"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def list_layers():
    config = load_config()
    print("Available LoRA layers:")
    for layer in config["layers"]:
        prefix = "✅ ACTIVE:" if layer == config["active_layer"] else "   "
        print(f"{prefix} {layer}")

def branch_layer(new_layer_name):
    config = load_config()
    if new_layer_name in config["layers"]:
        print(f"❌ Layer '{new_layer_name}' already exists.")
        return
    os.makedirs(os.path.join(LAYERS_DIR, new_layer_name), exist_ok=True)
    config["layers"].append(new_layer_name)
    config["active_layer"] = new_layer_name
    save_config(config)
    print(f"🌱 Branched new layer: {new_layer_name} and set as active.")

def activate_layer(layer_name):
    config = load_config()
    if layer_name not in config["layers"]:
        print(f"❌ Layer '{layer_name}' does not exist.")
        return
    config["active_layer"] = layer_name
    save_config(config)
    print(f"✅ Activated layer: {layer_name}")

def revert_to_layer(layer_name):
    config = load_config()
    if layer_name not in config["layers"]:
        print(f"❌ Layer '{layer_name}' does not exist.")
        return
    config["active_layer"] = layer_name
    save_config(config)
    print(f"⏪ Reverted to layer: {layer_name}")

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python lora_manager.py [list | branch_layer NAME | activate_layer NAME | revert_to_layer NAME]")
        return
    command = sys.argv[1]
    if command == "list":
        list_layers()
    elif command == "branch_layer":
        branch_layer(sys.argv[2])
    elif command == "activate_layer":
        activate_layer(sys.argv[2])
    elif command == "revert_to_layer":
        revert_to_layer(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
