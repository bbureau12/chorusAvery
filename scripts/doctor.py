import argparse
import shutil
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "chorusAvery.db"
ROOT_DB_PATH = ROOT / "chorusAvery.db"
REQUIRED_DIRS = [
    ROOT / "recordings" / "raw",
    ROOT / "recordings" / "chunks",
    ROOT / "recordings" / "clips",
    ROOT / "recordings" / "training_data",
    ROOT / "models",
    ROOT / "data",
    ROOT / "db",
]
REQUIRED_TABLES = [
    "SourceFiles",
    "Clips",
    "ClipAnnotations",
    "Species",
    "NonAnimalSounds",
    "Detections",
]
REQUIRED_BIRDNET_FILES = [
    ROOT / "BirdNET-Analyzer" / "BirdNET_GLOBAL_MODEL" / "model.tflite",
    ROOT / "BirdNET-Analyzer" / "BirdNET_GLOBAL_MODEL" / "labels.txt",
    ROOT / "BirdNET-Analyzer" / "BirdNET_GLOBAL_MODEL" / "metadata.json",
]


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def check_python() -> bool:
    if sys.version_info >= (3, 10):
        ok(f"Python version is {sys.version.split()[0]} (>= 3.10)")
        return True
    fail(f"Python version is {sys.version.split()[0]} (< 3.10)")
    return False


def check_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        ok("ffmpeg is available on PATH")
        return True
    fail("ffmpeg not found on PATH")
    return False


def check_dirs() -> bool:
    success = True
    for directory in REQUIRED_DIRS:
        if directory.exists() and directory.is_dir():
            ok(f"Directory exists: {directory.relative_to(ROOT)}")
        else:
            fail(f"Missing directory: {directory.relative_to(ROOT)}")
            success = False
    return success


def check_db_file() -> bool:
    if DB_PATH.exists():
        ok(f"DB file exists: {DB_PATH.relative_to(ROOT)}")
    else:
        fail(f"Missing DB file: {DB_PATH.relative_to(ROOT)}")
        return False

    if ROOT_DB_PATH.exists():
        warn(
            "Found additional DB at repo root (chorusAvery.db). "
            "Prefer using db/chorusAvery.db only."
        )
    return True


def check_db_tables() -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
    except Exception as exc:
        fail(f"Could not read DB tables: {exc}")
        return False

    success = True
    for table in REQUIRED_TABLES:
        if table in tables:
            ok(f"DB table found: {table}")
        else:
            fail(f"Missing DB table: {table}")
            success = False
    return success


def check_birdnet_assets() -> bool:
    success = True
    for file_path in REQUIRED_BIRDNET_FILES:
        if file_path.exists():
            ok(f"BirdNET asset found: {file_path.relative_to(ROOT)}")
        else:
            fail(f"Missing BirdNET asset: {file_path.relative_to(ROOT)}")
            success = False
    return success


def run_checks(skip_birdnet: bool) -> bool:
    print("Chorus Avery Doctor")
    print(f"Repository root: {ROOT}")
    print()

    results = [
        check_python(),
        check_ffmpeg(),
        check_dirs(),
        check_db_file(),
        check_db_tables(),
    ]
    if not skip_birdnet:
        results.append(check_birdnet_assets())

    return all(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight checks for Chorus Avery.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any check fails.",
    )
    parser.add_argument(
        "--skip-birdnet",
        action="store_true",
        help="Skip BirdNET model file checks.",
    )
    args = parser.parse_args()

    success = run_checks(skip_birdnet=args.skip_birdnet)

    print()
    if success:
        print("Preflight passed.")
        raise SystemExit(0)

    print("Preflight found issues.")
    if args.strict:
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
