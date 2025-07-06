import os


def filter_existing_files(file_list, base_dir):
    """
    Filters out paths from file_list that don't exist on disk.
    If a path is relative, it's resolved against base_dir.
    """
    valid_files = []
    for path in file_list:
        abs_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if os.path.exists(abs_path):
            valid_files.append(path)
        else:
            print(f"⚠️ Skipping missing file: {abs_path}")
    return valid_files