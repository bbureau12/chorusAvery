import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

# === Configuration ===
MAIN_DRIVE = Path("/mnt/usb_main")
BACKUP_DRIVE = Path("/mnt/usb_backup")
ARCHIVE_DRIVE = Path("/mnt/usb_archive")  # Optional; only used when archiving
DRIVE_MANIFEST_NAME = "disk_manifest.json"
MASTER_TRACKER = Path("./master_file_index.json")
LOW_SPACE_THRESHOLD_BYTES = 12 * 1024 ** 3  # 12 GB

# === Utility Functions ===
def calculate_sha256(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_all_files(base_path):
    file_list = []
    for root, _, files in os.walk(base_path):
        for name in files:
            path = Path(root) / name
            rel_path = path.relative_to(base_path)
            file_list.append(rel_path)
    return file_list

def load_manifest(drive_path):
    manifest_path = drive_path / DRIVE_MANIFEST_NAME
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            return json.load(f)
    return {"disk_id": str(drive_path.name), "last_updated": None, "files": []}

def save_manifest(drive_path, manifest_data):
    manifest_data["last_updated"] = datetime.utcnow().isoformat()
    manifest_path = drive_path / DRIVE_MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)

def update_drive_manifest(drive_path):
    manifest = {"disk_id": str(drive_path.name), "files": []}
    for rel_path in get_all_files(drive_path):
        full_path = drive_path / rel_path
        file_info = {
            "path": str(rel_path),
            "size_bytes": full_path.stat().st_size,
            "modified": datetime.utcfromtimestamp(full_path.stat().st_mtime).isoformat(),
            "sha256": calculate_sha256(full_path)
        }
        manifest["files"].append(file_info)
    save_manifest(drive_path, manifest)
    return manifest

def sync_backup(main_path, backup_path):
    print(f"🔄 Syncing from {main_path} to {backup_path}")
    for rel_path in get_all_files(main_path):
        src = main_path / rel_path
        dest = backup_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
    update_drive_manifest(backup_path)

def check_space_and_archive(main_path, archive_path):
    usage = shutil.disk_usage(main_path)
    free_bytes = usage.free
    if free_bytes < LOW_SPACE_THRESHOLD_BYTES:
        print("⚠️ Low space on main drive. Preparing archive.")
        archive_files(main_path, archive_path)

def archive_files(main_path, archive_path):
    archive_path.mkdir(parents=True, exist_ok=True)
    all_files = sorted(get_all_files(main_path), key=lambda p: (main_path / p).stat().st_mtime)
    used = shutil.disk_usage(archive_path).used
    total = shutil.disk_usage(archive_path).total
    space_remaining = total - used

    moved = 0
    for rel_path in all_files:
        src = main_path / rel_path
        size = src.stat().st_size
        if size < space_remaining:
            dest = archive_path / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dest)
            space_remaining -= size
            moved += 1
        else:
            break

    print(f"📦 Archived {moved} file(s) to {archive_path}")
    update_drive_manifest(main_path)
    update_drive_manifest(archive_path)

# === Main CLI Entry Point ===
def main():
    print("📁 File Tracking System")

    MAIN_DRIVE.mkdir(parents=True, exist_ok=True)
    BACKUP_DRIVE.mkdir(parents=True, exist_ok=True)

    print(f"📂 Scanning main drive: {MAIN_DRIVE}")
    update_drive_manifest(MAIN_DRIVE)

    input("🔌 Please mount the backup drive and press Enter to continue...")
    sync_backup(MAIN_DRIVE, BACKUP_DRIVE)

    check_space_and_archive(MAIN_DRIVE, ARCHIVE_DRIVE)

    print("✅ Done.")

if __name__ == "__main__":
    main()
