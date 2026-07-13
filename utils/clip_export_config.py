import json
import os
import shutil
from pathlib import Path

from utils.entityfinder import EntityFinder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
SESSION_CONFIG_PATH = RECORDINGS_DIR / "clip_export_config.json"
PREFERENCES_PATH = RECORDINGS_DIR / "clip_export_preferences.json"


def _read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    os.replace(temporary_path, path)


def normalize_existing_directory(raw_path):
    if raw_path is None:
        return None
    expanded = Path(os.path.expandvars(os.path.expanduser(str(raw_path).strip())))
    try:
        resolved = expanded.resolve()
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def load_default_export_directory(preferences_path=PREFERENCES_PATH):
    preferences = _read_json(preferences_path)
    if not isinstance(preferences, dict):
        return None
    return normalize_existing_directory(preferences.get("export_directory"))


def save_default_export_directory(directory, preferences_path=PREFERENCES_PATH):
    verified_directory = normalize_existing_directory(directory)
    if verified_directory is None:
        raise ValueError("Export destination must be an existing directory.")
    _write_json(preferences_path, {"export_directory": str(verified_directory)})
    return verified_directory


def save_session_config(species, export_directory, session_path=SESSION_CONFIG_PATH):
    verified_directory = normalize_existing_directory(export_directory)
    if verified_directory is None:
        raise ValueError("Export destination must be an existing directory.")
    normalized_species = [
        {"id": int(species_id), "name": str(name)}
        for species_id, name in species
    ]
    if not normalized_species:
        raise ValueError("At least one species must be selected.")
    _write_json(session_path, {
        "species": normalized_species,
        "export_directory": str(verified_directory),
    })


def clear_session_config(session_path=SESSION_CONFIG_PATH):
    try:
        Path(session_path).unlink()
    except FileNotFoundError:
        pass


def select_species(finder, first_query):
    selected_species = []
    query = first_query
    while query:
        matches = finder.search_species(query)
        if not matches:
            print(f"No species found matching '{query}'.")
        else:
            print(f"\nFound {len(matches)} matches:")
            for index, (_, name) in enumerate(matches, 1):
                print(f"{index}. {name}")

            selection = input(
                "Select number(s) separated by commas, or leave blank to skip: "
            ).strip()
            if selection:
                try:
                    indexes = [int(value.strip()) - 1 for value in selection.split(",")]
                    if any(not 0 <= index < len(matches) for index in indexes):
                        raise ValueError("selection is out of range")
                    for index in indexes:
                        if matches[index] not in selected_species:
                            selected_species.append(matches[index])
                            print(f"Added: {matches[index][1]}")
                except ValueError as error:
                    print(f"Invalid selection: {error}")

        query = input(
            "Enter another species search term, or press ENTER when done: "
        ).strip()
    return selected_species


def prompt_for_export_directory():
    default_directory = load_default_export_directory()
    while True:
        default_text = f" [{default_directory}]" if default_directory else ""
        entered_path = input(f"Export destination{default_text}: ").strip()
        candidate = entered_path or default_directory
        if candidate is None:
            print("A destination path is required.")
            continue
        try:
            return save_default_export_directory(candidate)
        except ValueError:
            print("Directory does not exist. Please enter an existing directory.")


def configure_selected_species_export(db_path):
    first_query = input(
        "Monitor and export selected species? Enter a species search term, "
        "or press ENTER to continue normally: "
    ).strip()
    if not first_query:
        clear_session_config()
        print("Selected-species export disabled for this labeling session.")
        return None

    finder = EntityFinder(db_path)
    try:
        selected_species = select_species(finder, first_query)
    finally:
        finder.close()

    if not selected_species:
        clear_session_config()
        print("No species selected; selected-species export disabled.")
        return None

    export_directory = prompt_for_export_directory()
    save_session_config(selected_species, export_directory)
    selected_names = ", ".join(name for _, name in selected_species)
    print(f"Selected-species export enabled: {selected_names}")
    print(f"Export destination: {export_directory}")
    return selected_species, export_directory


def load_session_config(session_path=SESSION_CONFIG_PATH):
    config = _read_json(session_path)
    if not isinstance(config, dict):
        return None

    export_directory = normalize_existing_directory(config.get("export_directory"))
    species = config.get("species")
    if export_directory is None or not isinstance(species, list):
        return None

    try:
        species_ids = {int(item["id"]) for item in species}
    except (KeyError, TypeError, ValueError):
        return None
    if not species_ids:
        return None

    return {
        "species_ids": species_ids,
        "export_directory": export_directory,
    }


def _available_destination(destination_directory, filename):
    candidate = destination_directory / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 1
    while True:
        candidate = destination_directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def export_clip_if_selected(source_path, labels, species_list, config):
    if not config:
        return None

    species_set = set(species_list)
    selected_species_ids = config["species_ids"]
    matches = [
        (item_id, name) for item_id, name in labels
        if (item_id, name) in species_set and item_id in selected_species_ids
    ]
    if not matches:
        return None

    source_path = Path(source_path)
    destination = _available_destination(
        Path(config["export_directory"]), source_path.name
    )
    shutil.copy2(source_path, destination)
    return destination
