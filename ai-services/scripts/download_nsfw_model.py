#!/usr/bin/env python3
"""
download_nsfw_model.py — Download the GantMan MobileNetV2 NSFW SavedModel.

Single-purpose script that downloads and verifies the open-source NSFW
detection model published at:
  https://github.com/GantMan/nsfw_model/releases/tag/1.1.0

Usage:
    python download_nsfw_model.py [--models-dir ./models]

The script is idempotent: if the SavedModel directory already contains
saved_model.pb it exits with success without re-downloading.
"""

import argparse
import os
import shutil
import sys
import zipfile
from typing import Optional
from urllib.request import urlretrieve

NSFW_ZIP_URLS = [
    "https://github.com/GantMan/nsfw_model/releases/download/1.2.0/mobilenet_v2_140_224.1.zip",
    "https://github.com/GantMan/nsfw_model/releases/download/1.1.0/nsfw_mobilenet_v2_140_224.zip",
]

SAVEDMODEL_DIR_NAME = "mobilenet_v2_140_224"
SAVEDMODEL_PB = "saved_model.pb"


def _progress_hook(count, block_size, total_size):
    if total_size <= 0:
        return
    pct = min(int(count * block_size * 100 / total_size), 100)
    print(f"\r  Downloading: {pct:3d}%", end="", flush=True)
    if pct == 100:
        print()


def _find_savedmodel_dir(root_dir: str) -> Optional[str]:
    for current_root, _, files in os.walk(root_dir):
        if SAVEDMODEL_PB in files:
            return current_root
    return None


def download_nsfw_model(models_dir: str) -> bool:
    nsfw_dir = os.path.join(models_dir, "nsfw")
    dest_dir = os.path.join(nsfw_dir, SAVEDMODEL_DIR_NAME)
    saved_model_pb = os.path.join(dest_dir, SAVEDMODEL_PB)

    # Idempotency check
    if os.path.isfile(saved_model_pb):
        print(f"[SKIP] SavedModel already present: {saved_model_pb}")
        return True

    os.makedirs(nsfw_dir, exist_ok=True)
    zip_path = os.path.join(nsfw_dir, "nsfw_model.zip")

    # Download
    print("Source :")
    downloaded = False
    for url in NSFW_ZIP_URLS:
        print(f"  - {url}")
        try:
            urlretrieve(url, zip_path, reporthook=_progress_hook)
            downloaded = True
            break
        except Exception as exc:
            print(f"  [WARN] Download failed: {exc}", file=sys.stderr)
            try:
                os.remove(zip_path)
            except OSError:
                pass
    if not downloaded:
        print("[ERROR] Download failed from all known URLs.", file=sys.stderr)
        return False
    print(f"Target : {nsfw_dir}")

    # Verify the zip is readable before extraction
    if not zipfile.is_zipfile(zip_path):
        print("[ERROR] Downloaded file is not a valid zip archive.", file=sys.stderr)
        try:
            os.remove(zip_path)
        except OSError:
            pass
        return False

    # Extract
    print("Extracting …")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(nsfw_dir)
    except zipfile.BadZipFile as exc:
        print(f"[ERROR] Extraction failed: {exc}", file=sys.stderr)
        return False
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    # Normalize directory when release archive uses a different top-level name
    if not os.path.isfile(saved_model_pb):
        source_dir = _find_savedmodel_dir(nsfw_dir)
        if source_dir:
            if os.path.isdir(dest_dir):
                shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.move(source_dir, dest_dir)

    # Verify
    if not os.path.isfile(saved_model_pb):
        print(
            f"[ERROR] {SAVEDMODEL_PB} not found after extraction.\n"
            f"        Expected location: {saved_model_pb}",
            file=sys.stderr,
        )
        return False

    # List top-level contents for visibility
    try:
        entries = os.listdir(dest_dir)
        print(f"SavedModel contents ({len(entries)} items):")
        for entry in sorted(entries):
            print(f"  {entry}")
    except OSError:
        pass

    print(f"\n[OK] NSFW SavedModel ready at: {dest_dir}")
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download the GantMan MobileNetV2 NSFW SavedModel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--models-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "models"),
        metavar="PATH",
        help="Root models directory (default: ../models relative to this script)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models_dir = os.path.realpath(args.models_dir)
    print(f"Models directory: {models_dir}\n")

    if download_nsfw_model(models_dir):
        return 0
    else:
        print("\nNSFW model download failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
