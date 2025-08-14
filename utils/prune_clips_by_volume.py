#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Optional, Tuple

try:
    from pydub import AudioSegment
except Exception as e:
    AudioSegment = None


def dbfs_from_audio(path: str, metric: str) -> Optional[float]:
    '''
    Compute dBFS from audio if JSON sidecar is missing or lacks the metric.
    metric: 'max' or 'avg'
    '''
    if AudioSegment is None:
        return None
    try:
        audio = AudioSegment.from_file(path)
        if metric == "max":
            return float(audio.max_dBFS)
        else:
            # avg == overall RMS-based dBFS
            return float(audio.dBFS if audio.dBFS != float("-inf") else -100.0)
    except Exception as e:
        print(f"⚠️  Could not compute dBFS for {os.path.basename(path)}: {e}")
        return None


def read_metric_from_json(json_path: str, metric: str) -> Optional[float]:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        key = "max_dbfs" if metric == "max" else "avg_dbfs"
        if key in data and isinstance(data[key], (int, float)):
            return float(data[key])
        return None
    except Exception:
        return None


def discover_pairs(root: str, recursive: bool) -> Tuple[int, list[Tuple[str, Optional[str]]]]:
    '''
    Return the list of (wav_path, json_path_or_None). Optionally recurse.
    '''
    pairs = []
    count = 0
    if recursive:
        walker = os.walk(root)
    else:
        walker = [(root, [], os.listdir(root) if os.path.isdir(root) else [])]

    for dirpath, _dirnames, filenames in walker:
        for name in filenames:
            if not name.lower().endswith(".wav"):
                continue
            wav_path = os.path.join(dirpath, name)
            json_path = os.path.splitext(wav_path)[0] + ".json"
            pairs.append((wav_path, json_path if os.path.exists(json_path) else None))
            count += 1
    return count, pairs


def human_bytes(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def prune(root: str, threshold: float, metric: str, recursive: bool, dry_run: bool, force: bool) -> int:
    total_files, pairs = discover_pairs(root, recursive)
    if total_files == 0:
        print("No .wav files found.")
        return 0

    print(f"🔎 Scanning {total_files} WAV files in '{root}' (recursive={recursive})")
    print(f"• Metric: {metric} dBFS • Threshold: {threshold} dBFS (delete if value < threshold)")
    if dry_run:
        print("• Mode: DRY RUN (no deletions)")

    to_delete = []
    kept = 0

    for wav_path, json_path in pairs:
        value = None
        # Prefer JSON sidecar if available
        if json_path:
            value = read_metric_from_json(json_path, metric)
        if value is None:
            value = dbfs_from_audio(wav_path, metric)
        if value is None:
            print(f"   – Skipping (no metric): {os.path.relpath(wav_path, root)}")
            kept += 1
            continue

        rel = os.path.relpath(wav_path, root)
        if value < threshold:
            print(f"   🗑️  Marked for delete ({metric}={value:.2f} dBFS): {rel}")
            to_delete.append((wav_path, json_path))
        else:
            print(f"   ✅ Keep ({metric}={value:.2f} dBFS): {rel}")
            kept += 1

    if not to_delete:
        print("\nNothing to delete. All files meet or exceed the threshold.")
        return 0

    bytes_freed = 0
    deletions = 0

    if dry_run:
        print(f"\nDRY RUN: {len(to_delete)} files would be deleted (plus sidecars if present).")
        return 0

    if not force:
        resp = input(f"\nAbout to delete {len(to_delete)} files (and JSON sidecars). Proceed? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return 0

    for wav_path, json_path in to_delete:
        try:
            bytes_freed += os.path.getsize(wav_path)
        except Exception:
            pass
        try:
            os.remove(wav_path)
            deletions += 1
        except Exception as e:
            print(f"⚠️  Could not delete WAV: {wav_path} ({e})")

        if json_path and os.path.exists(json_path):
            try:
                bytes_freed += os.path.getsize(json_path)
            except Exception:
                pass
            try:
                os.remove(json_path)
            except Exception as e:
                print(f"⚠️  Could not delete JSON: {json_path} ({e})")

    print(f"\\n✅ Deleted {deletions} WAV file(s). Freed approximately {human_bytes(bytes_freed)}.")
    print(f"✅ Kept {kept} WAV file(s).")
    return deletions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Prune quiet audio clips (and JSON sidecars) below a dBFS threshold."
    )
    parser.add_argument(
        "-d", "--dir", default="./recordings/clips",
        help="Directory containing .wav clips (default: ./recordings/clips)"
    )
    parser.add_argument(
        "-t", "--threshold", type=float, default=-35.0,
        help="Threshold in dBFS; delete files with metric value BELOW this (default: -35.0)"
    )
    parser.add_argument(
        "-m", "--metric", choices=["max", "avg"], default="max",
        help="Which metric to compare against threshold (default: max)"
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true",
        help="Recurse into subdirectories"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be deleted without deleting"
    )
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="Do not ask for confirmation before deleting"
    )

    args = parser.parse_args(argv)

    # Basic sanity on path
    if not os.path.isdir(args.dir):
        print(f"Directory not found: {args.dir}")
        return 2

    if AudioSegment is None:
        print("⚠️  pydub not available; will rely on JSON sidecars for metrics.")
        print("    Install with: pip install pydub")
        print("    Also ensure ffmpeg is installed to compute dBFS from audio.")

    return prune(
        root=args.dir,
        threshold=args.threshold,
        metric=args.metric,
        recursive=args.recursive,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())