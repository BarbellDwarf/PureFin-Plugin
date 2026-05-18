#!/usr/bin/env python3
"""
bootstrap_models.py — PureFin AI Services model bootstrap script.

Sets up all required model files for local/test runs so that AI services
do not return HTTP 503 due to missing models.

Usage:
    python bootstrap_models.py [--models-dir ./models] [--skip-nsfw] [--skip-violence] [--force]

What it does:
  1. NSFW model      — Downloads GantMan MobileNet NSFW SavedModel from GitHub releases.
  2. Violence model  — Bootstraps a .pth file using MobileNetV2 ImageNet weights + an
                       untrained custom head that matches the production architecture.
                       NOT trained for violence detection — test scaffold only.
  3. CLIP model      — Prints a reminder; CLIP auto-downloads from HuggingFace on startup.
"""

import argparse
import os
import shutil
import sys
import zipfile
from typing import Optional
from urllib.request import urlretrieve

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NSFW_ZIP_URLS = [
    "https://github.com/GantMan/nsfw_model/releases/download/1.2.0/mobilenet_v2_140_224.1.zip",
    "https://github.com/GantMan/nsfw_model/releases/download/1.1.0/nsfw_mobilenet_v2_140_224.zip",
]

VIOLENCE_BOOTSTRAP_NOTE = (
    "ImageNet weights only - NOT trained for violence detection - test scaffold only"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def _make_progress_hook(label: str):
    """Return a urlretrieve reporthook that prints a percentage counter."""
    last_pct = [-1]

    def _hook(count, block_size, total_size):
        if total_size <= 0:
            return
        pct = min(int(count * block_size * 100 / total_size), 100)
        if pct != last_pct[0]:
            last_pct[0] = pct
            print(f"\r  {label}: {pct:3d}%", end="", flush=True)
        if pct == 100:
            print()  # newline after 100 %

    return _hook


def _find_savedmodel_dir(root_dir: str) -> Optional[str]:
    """Locate the first directory containing a TensorFlow SavedModel."""
    for current_root, _, files in os.walk(root_dir):
        if "saved_model.pb" in files:
            return current_root
    return None


# ---------------------------------------------------------------------------
# 1. NSFW model
# ---------------------------------------------------------------------------

def bootstrap_nsfw(models_dir: str, force: bool) -> bool:
    """Download the GantMan MobileNetV2 NSFW SavedModel."""
    _print_section("NSFW Detection Model (TensorFlow SavedModel)")

    dest_dir = os.path.join(models_dir, "nsfw", "mobilenet_v2_140_224")

    # Idempotency check
    saved_model_pb = os.path.join(dest_dir, "saved_model.pb")
    if not force and os.path.isfile(saved_model_pb):
        print(f"  [SKIP] Already present: {saved_model_pb}")
        return True

    nsfw_dir = os.path.join(models_dir, "nsfw")
    os.makedirs(nsfw_dir, exist_ok=True)

    zip_path = os.path.join(nsfw_dir, "nsfw_model.zip")
    downloaded = False
    for url in NSFW_ZIP_URLS:
        print(f"  Downloading from: {url}")
        try:
            urlretrieve(url, zip_path, reporthook=_make_progress_hook("  Download"))
            downloaded = True
            break
        except Exception as exc:
            print(f"  [WARN] Download failed: {exc}", file=sys.stderr)
            try:
                os.remove(zip_path)
            except OSError:
                pass

    if not downloaded:
        print("  [ERROR] Unable to download NSFW model archive from known URLs.", file=sys.stderr)
        return False

    # Extract
    print("  Extracting archive …")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(nsfw_dir)
    except zipfile.BadZipFile as exc:
        print(f"  [ERROR] Extraction failed: {exc}", file=sys.stderr)
        return False
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    # Normalize extracted directory if release archive layout changed
    if not os.path.isfile(saved_model_pb):
        source_dir = _find_savedmodel_dir(nsfw_dir)
        if source_dir:
            if os.path.isdir(dest_dir):
                shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.move(source_dir, dest_dir)
    if not os.path.isfile(saved_model_pb):
        print(
            f"  [ERROR] Expected file not found after extraction: {saved_model_pb}",
            file=sys.stderr,
        )
        return False

    print(f"  [OK] NSFW SavedModel ready at: {dest_dir}")
    return True


# ---------------------------------------------------------------------------
# 2. Violence model (bootstrap)
# ---------------------------------------------------------------------------

def _define_violence_model_class():
    """
    Import torch/torchvision and return the ViolenceModelPyTorch class.

    The architecture must exactly match the one in
    services/content-classifier/app_pytorch.py so that torch.load() with
    load_state_dict() succeeds at inference time.
    """
    import torch.nn as nn
    from torchvision import models as tv_models

    class ViolenceModelPyTorch(nn.Module):
        def __init__(self):
            super(ViolenceModelPyTorch, self).__init__()
            mobilenet = tv_models.mobilenet_v2(weights=tv_models.MobileNet_V2_Weights.IMAGENET1K_V1)
            self.features = mobilenet.features
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(1280, 128),
                nn.ReLU(inplace=True),
                nn.Dropout(0.5),
                nn.Linear(128, 1),
                nn.Sigmoid(),
            )

        def forward(self, x):
            x = self.features(x)
            x = self.pool(x)
            x = self.classifier(x)
            return x

    return ViolenceModelPyTorch


def bootstrap_violence(models_dir: str, force: bool) -> bool:
    """Create a bootstrap .pth file with MobileNetV2 ImageNet weights."""
    _print_section("Violence Detection Model (PyTorch — bootstrap scaffold)")

    violence_dir = os.path.join(models_dir, "violence")
    pth_path = os.path.join(violence_dir, "violence_model.pth")

    # Skip if a real (non-bootstrap) model is already present
    if not force and os.path.isfile(pth_path):
        try:
            import torch
            checkpoint = torch.load(pth_path, map_location="cpu", weights_only=False)
            if not checkpoint.get("bootstrap", False):
                print("  [SKIP] A non-bootstrap violence model already exists. Leaving it untouched.")
                return True
            print("  Existing file is a bootstrap scaffold; re-bootstrapping.")
        except Exception:
            print("  Existing .pth file is unreadable; will overwrite.")

    # Try importing torch / torchvision
    try:
        import torch
    except ImportError:
        print(
            "  [SKIP] torch is not installed. Install with: pip install torch torchvision",
            file=sys.stderr,
        )
        return False

    try:
        from torchvision import models as _  # noqa: F401
    except ImportError:
        print(
            "  [SKIP] torchvision is not installed. Install with: pip install torchvision",
            file=sys.stderr,
        )
        return False

    print("  Building ViolenceModelPyTorch with MobileNetV2 ImageNet weights …")
    ViolenceModelPyTorch = _define_violence_model_class()

    try:
        model = ViolenceModelPyTorch()
        model.eval()
    except Exception as exc:
        print(f"  [ERROR] Could not instantiate model: {exc}", file=sys.stderr)
        return False

    os.makedirs(violence_dir, exist_ok=True)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "bootstrap": True,
        "note": VIOLENCE_BOOTSTRAP_NOTE,
    }

    try:
        import torch
        torch.save(checkpoint, pth_path)
    except Exception as exc:
        print(f"  [ERROR] Failed to save model: {exc}", file=sys.stderr)
        return False

    size_mb = os.path.getsize(pth_path) / (1024 * 1024)
    print(f"  [OK] Bootstrap model saved: {pth_path} ({size_mb:.1f} MB)")
    print()
    print(
        "  *** WARNING ***********************************************************\n"
        "  Violence model bootstrapped with ImageNet weights only.\n"
        "  Results will NOT be accurate for violence detection.\n"
        "  This is a test scaffold to verify the pipeline runs.\n"
        "  ***********************************************************************"
    )
    return True


# ---------------------------------------------------------------------------
# 3. CLIP model
# ---------------------------------------------------------------------------

def print_clip_info() -> None:
    _print_section("CLIP Model (content-classifier)")
    print(
        "  CLIP model will auto-download from HuggingFace on content-classifier\n"
        "  startup (~600 MB). Ensure internet access from the container.\n"
        "  The model is cached at {models_dir}/clip/ after the first download."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Bootstrap AI model files for PureFin AI services (test/local runs).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--models-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "models"),
        metavar="PATH",
        help="Root directory for model files (default: ../models relative to this script)",
    )
    parser.add_argument(
        "--skip-nsfw",
        action="store_true",
        help="Skip NSFW model download",
    )
    parser.add_argument(
        "--skip-violence",
        action="store_true",
        help="Skip violence model bootstrap",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download / re-bootstrap even if files already exist",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models_dir = os.path.realpath(args.models_dir)

    print(f"PureFin model bootstrap")
    print(f"Models directory : {models_dir}")
    print(f"Force            : {args.force}")

    os.makedirs(models_dir, exist_ok=True)

    results = {}

    if not args.skip_nsfw:
        results["nsfw"] = bootstrap_nsfw(models_dir, args.force)
    else:
        print("\n[SKIP] --skip-nsfw flag set; skipping NSFW model download.")
        results["nsfw"] = True  # not a failure

    if not args.skip_violence:
        results["violence"] = bootstrap_violence(models_dir, args.force)
    else:
        print("\n[SKIP] --skip-violence flag set; skipping violence model bootstrap.")
        results["violence"] = True

    print_clip_info()

    # Summary
    _print_section("Summary")
    all_ok = True
    for name, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nBootstrap complete. AI services should now start without HTTP 503.")
        return 0
    else:
        print("\nOne or more steps failed. Check messages above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
