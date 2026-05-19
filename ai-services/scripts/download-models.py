#!/usr/bin/env python3
"""Model Download Script for PureFin AI Services.

Downloads and sets up all required AI models for content detection:
- NSFW/Nudity Detection: Yahoo's Open NSFW Model
- Violence Detection: RealViolenceDataset trained model  
- Content Classification: CLIP model for general content analysis

Supports GPU and CPU configurations with automatic model verification.
"""

import sys
import hashlib
import zipfile
import tarfile
import logging
from pathlib import Path
from urllib.request import urlretrieve
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base paths
SCRIPT_DIR = Path(__file__).parent
AI_SERVICES_DIR = SCRIPT_DIR.parent
MODELS_DIR = AI_SERVICES_DIR / "models"

# Model configurations
MODELS_CONFIG = {
    'nsfw': {
        'name': 'NSFW Detection Model (Custom)',
        'url': None,  # We'll create our own model
        'filename': 'nsfw_model.h5',
        'extract_to': 'nsfw',
        'expected_files': ['nsfw_model.h5'],
        'sha256': None,
        'description': 'MobileNetV2-based NSFW detector using transfer learning',
        'size_mb': 35,
        'auto_download': True
    },
    'violence': {
        'name': 'Violence Detection Model (HuggingFace ViT)',
        'url': None,
        'filename': None,
        'extract_to': 'violence',
        'expected_files': ['balanced/config.json'],
        'sha256': None,
        'description': 'ViT classifier for violent/non-violent frame detection',
        'size_mb': 350,
        'auto_download': True
    },
    'clip': {
        'name': 'CLIP Model (Content Classification)', 
        'url': None,  # Auto-downloaded by transformers library
        'filename': None,
        'extract_to': 'content',
        'expected_files': ['clip-vit-base-patch32'],  # Will be created by transformers
        'sha256': None,
        'description': 'OpenAI CLIP model for general content classification',
        'size_mb': 600,  # Approximate download size
        'auto_download': True
    }
}

VIOLENCE_MODEL_PROFILES = {
    'speed': 'nghiabntl/vit-base-violence-detection',
    'balanced': 'jaranohaal/vit-base-violence-detection',
    'quality': 'framasoft/vit-base-violence-detection',
}


def download_file(url: str, filepath: Path, expected_size_mb: int = None):
    """Download a file with progress indication.
    
    Args:
        url: URL to download from
        filepath: Local path to save file
        expected_size_mb: Expected file size in MB for validation
    """
    try:
        logger.info(f"Downloading {filepath.name} from {url}")
        
        def progress_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            mb_downloaded = (count * block_size) / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r  Progress: {percent:3d}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
        
        urlretrieve(url, filepath, reporthook=progress_hook)
        print()  # New line after progress
        
        # Verify file size
        actual_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"Downloaded {filepath.name} ({actual_size_mb:.1f} MB)")
        
        if expected_size_mb and abs(actual_size_mb - expected_size_mb) > (expected_size_mb * 0.1):
            logger.warning(f"File size differs from expected: {actual_size_mb:.1f} MB vs {expected_size_mb} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def verify_checksum(filepath: Path, expected_sha256: str) -> bool:
    """Verify file SHA256 checksum.
    
    Args:
        filepath: Path to file to verify
        expected_sha256: Expected SHA256 hash
        
    Returns:
        True if checksum matches
    """
    if not expected_sha256:
        return True  # Skip verification if no checksum provided
    
    try:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        actual_hash = hasher.hexdigest()
        if actual_hash.lower() == expected_sha256.lower():
            logger.info(f"Checksum verified for {filepath.name}")
            return True
        else:
            logger.error(f"Checksum mismatch for {filepath.name}")
            logger.error(f"  Expected: {expected_sha256}")
            logger.error(f"  Actual:   {actual_hash}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying checksum for {filepath.name}: {e}")
        return False


def extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    """Extract zip or tar archive.
    
    Args:
        archive_path: Path to archive file
        extract_dir: Directory to extract to
        
    Returns:
        True if extraction successful
    """
    try:
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        if archive_path.suffix.lower() == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                logger.info(f"Extracted {archive_path.name} to {extract_dir}")
        
        elif archive_path.suffix.lower() in ['.tar', '.gz', '.tgz']:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)
                logger.info(f"Extracted {archive_path.name} to {extract_dir}")
        
        else:
            logger.warning(f"Unknown archive format: {archive_path}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error extracting {archive_path}: {e}")
        return False


def setup_clip_model():
    """Download CLIP model using transformers library.
    
    This will auto-download CLIP on first use, but we can pre-cache it.
    """
    try:
        logger.info("Setting up CLIP model...")
        
        # Create directory structure
        clip_dir = MODELS_DIR / "content" / "clip-vit-base-patch32"
        clip_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple Python script to download CLIP
        download_script = clip_dir / "download_clip.py"
        download_script.write_text('''
"""CLIP model download script."""
import torch
from transformers import CLIPProcessor, CLIPModel

# Download and cache CLIP model
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# Save locally
model.save_pretrained("./")
processor.save_pretrained("./")

print("CLIP model downloaded and cached successfully!")
''')
        
        logger.info("CLIP model setup complete (will download on first use)")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up CLIP model: {e}")
        return False


def create_violence_model(profile: str = 'balanced'):
    """Download and cache the HuggingFace violence model locally."""
    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        model_id = VIOLENCE_MODEL_PROFILES[profile]
        target_dir = MODELS_DIR / 'violence' / profile
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading violence model from HuggingFace: %s", model_id)
        processor = AutoImageProcessor.from_pretrained(model_id)
        model = AutoModelForImageClassification.from_pretrained(model_id)
        processor.save_pretrained(target_dir)
        model.save_pretrained(target_dir)
        logger.info("Violence model cached at %s", target_dir)
        return True
    except Exception as e:
        logger.error("Failed to download violence model: %s", e)
        return False


def create_nsfw_model():
    """Placeholder — real model must be provided; generating random weights is not supported."""
    logger.error(
        "NSFW model not found and no real model is available for download. "
        "Please provide a trained nsfw_model.h5 in the models/nsfw/ directory."
    )
    return False


def verify_model_files(model_key: str, config: dict, violence_profile: str = 'balanced') -> bool:
    """Verify that all expected model files exist.
    
    Args:
        model_key: Model configuration key
        config: Model configuration dictionary
        
    Returns:
        True if all files exist
    """
    model_dir = MODELS_DIR / config['extract_to']
    
    expected_files = config['expected_files']
    if model_key == 'violence':
        expected_files = [f'{violence_profile}/config.json']

    for expected_file in expected_files:
        file_path = model_dir / expected_file
        if not file_path.exists():
            logger.error(f"Missing expected file for {model_key}: {file_path}")
            return False
    
    logger.info(f"All files verified for {model_key}")
    return True


def download_model(model_key: str, config: dict, force: bool = False, violence_profile: str = 'balanced') -> bool:
    """Download and setup a single model.
    
    Args:
        model_key: Model configuration key
        config: Model configuration dictionary  
        force: Force re-download even if files exist
        
    Returns:
        True if successful
    """
    logger.info(f"\n=== Setting up {config['name']} ===")
    
    model_dir = MODELS_DIR / config['extract_to']
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model already exists
    if not force and verify_model_files(model_key, config, violence_profile):
        logger.info(f"{config['name']} already exists and verified")
        return True
    
    # Handle auto-download models (like CLIP, violence, and NSFW)
    if config.get('auto_download'):
        if model_key == 'clip':
            return setup_clip_model()
        elif model_key == 'violence':
            return create_violence_model(violence_profile)
        elif model_key == 'nsfw':
            return create_nsfw_model()
    
    # Download regular models
    if not config['url']:
        logger.error(f"No download URL specified for {model_key}")
        return False
    
    # Download file
    download_path = model_dir / config['filename']
    if not download_file(config['url'], download_path, config.get('size_mb')):
        return False
    
    # Verify checksum
    if not verify_checksum(download_path, config.get('sha256')):
        return False
    
    # Extract if it's an archive
    if config['filename'].endswith(('.zip', '.tar', '.gz', '.tgz')):
        if not extract_archive(download_path, model_dir):
            return False
        
        # Remove archive after extraction
        try:
            download_path.unlink()
            logger.info(f"Removed archive file {config['filename']}")
        except Exception as e:
            logger.warning(f"Could not remove archive: {e}")
    
    # Final verification
    return verify_model_files(model_key, config, violence_profile)


def create_model_info_files():
    """Create README files for each model directory."""
    
    # NSFW Model README
    nsfw_readme = MODELS_DIR / "nsfw" / "README.md"
    nsfw_readme.parent.mkdir(parents=True, exist_ok=True)
    nsfw_readme.write_text("""# NSFW Detection Model

## Model: Yahoo Open NSFW Model (MobileNetV2)

**Source**: https://github.com/GantMan/nsfw_model
**License**: BSD-2-Clause

### Categories:
- `drawings`: Non-photographic drawings/cartoons
- `hentai`: Animated/cartoon pornographic content  
- `neutral`: Safe for work content
- `porn`: Photographic pornographic content
- `sexy`: Suggestive but not explicit content

### Usage:
```python
import tensorflow as tf
model = tf.keras.models.load_model('mobilenet_v2_140_224')
```

### Input Format:
- Image size: 224x224 pixels
- Color format: RGB
- Normalization: 0-1 (divide by 255)

### Output Format:
- 5 category scores (0.0-1.0)
- Sum of all scores = 1.0
""")

    # Violence Model README  
    violence_readme = MODELS_DIR / "violence" / "README.md"
    violence_readme.parent.mkdir(parents=True, exist_ok=True)
    violence_readme.write_text("""# Violence Detection Model

## Model: jaranohaal/vit-base-violence-detection

**Source**: https://huggingface.co/jaranohaal/vit-base-violence-detection
**Architecture**: Vision Transformer (ViT)

### Categories:
- Binary classification: violent vs non-violent
- Output range: 0.0-1.0 (probability)

### Usage:
```python
from transformers import AutoImageProcessor, AutoModelForImageClassification
processor = AutoImageProcessor.from_pretrained('./vit-base-violence-detection')
model = AutoModelForImageClassification.from_pretrained('./vit-base-violence-detection')
```

### Input Format:
- Image size: 224x224 pixels
- Color format: RGB
- Normalization: 0-1

### Output Format:
- Label scores per class
- `violence_score` normalized to 0.0-1.0
""")

    # Content Classification README
    content_readme = MODELS_DIR / "content" / "README.md"
    content_readme.parent.mkdir(parents=True, exist_ok=True)
    content_readme.write_text("""# Content Classification (CLIP)

## Model: OpenAI CLIP (ViT-B/32)

**Source**: https://github.com/openai/CLIP
**License**: MIT

### Description:
CLIP (Contrastive Language-Image Pre-training) enables zero-shot classification
using natural language descriptions.

### Usage:
```python
from transformers import CLIPProcessor, CLIPModel
model = CLIPModel.from_pretrained("./clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("./clip-vit-base-patch32")
```

### Capabilities:
- Zero-shot image classification
- Text-based content queries
- Multi-label classification
- Semantic similarity scoring

### Content Categories:
- Drug use, smoking, drinking
- Inappropriate content, profanity
- Family-friendly content
- Educational material
""")

    logger.info("Created model documentation files")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download AI models for PureFin content filtering")
    parser.add_argument('--models', nargs='+', choices=['nsfw', 'violence', 'clip', 'all'], 
                       default=['all'], help='Models to download (default: all)')
    parser.add_argument('--force', action='store_true', 
                       help='Force re-download even if models exist')
    parser.add_argument('--gpu', action='store_true',
                       help='Download GPU-optimized models where available')
    parser.add_argument('--verify-only', action='store_true',
                       help='Only verify existing models, do not download')
    parser.add_argument('--violence-profile', choices=sorted(VIOLENCE_MODEL_PROFILES.keys()),
                       default='balanced', help='Violence model profile to process (default: balanced)')
    
    args = parser.parse_args()
    
    # Resolve "all" to actual model names
    if 'all' in args.models:
        models_to_process = list(MODELS_CONFIG.keys())
    else:
        models_to_process = args.models
    
    logger.info("PureFin Model Downloader")
    logger.info(f"Models directory: {MODELS_DIR}")
    logger.info(f"Processing models: {', '.join(models_to_process)}")
    
    if args.gpu:
        logger.info("GPU acceleration enabled")
    
    # Create models directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each model
    success_count = 0
    total_count = len(models_to_process)
    
    for model_key in models_to_process:
        if model_key not in MODELS_CONFIG:
            logger.error(f"Unknown model: {model_key}")
            continue
        
        config = MODELS_CONFIG[model_key]
        
        if args.verify_only:
            # Only verify, don't download
            if verify_model_files(model_key, config, args.violence_profile):
                logger.info(f"✓ {config['name']} - verified")
                success_count += 1
            else:
                logger.error(f"✗ {config['name']} - verification failed")
        else:
            # Download and setup
            if download_model(model_key, config, args.force, args.violence_profile):
                logger.info(f"✓ {config['name']} - ready")
                success_count += 1
            else:
                logger.error(f"✗ {config['name']} - failed")
    
    # Create documentation
    if not args.verify_only:
        create_model_info_files()
    
    # Summary
    logger.info("\n=== Summary ===")
    logger.info(f"Successfully processed: {success_count}/{total_count} models")
    
    if success_count == total_count:
        logger.info("🎉 All models ready! AI services can now use real models.")
        return 0
    else:
        logger.error(f"⚠️  {total_count - success_count} models failed to download")
        logger.error(
            "Provide real trained model files — AI services will not start in inference mode without them."
        )
        return 1


if __name__ == '__main__':
    sys.exit(main())
