"""NSFW Detection Service - REST API using a HuggingFace image classifier.

Two-model approach:
  1. NSFW binary/multi-class model → nudity score (explicit content)
  2. CLIP zero-shot classifier     → immodesty score (revealing clothing)

The CLIP zero-shot approach produces semantically meaningful immodesty scores
that distinguish bikinis/swimwear from ordinary clothed scenes, which binary
NSFW models cannot do reliably.
"""

import gc
import io
import logging
import os
import threading
import time
from datetime import datetime

import torch
from flask import Flask, jsonify, request
from PIL import Image, ImageOps
from prometheus_client import Counter, Histogram, generate_latest
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
    CLIPModel,
    CLIPProcessor,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
HTTP_ACCESS_LOGS = os.getenv("HTTP_ACCESS_LOGS", "0") == "1"
if not HTTP_ACCESS_LOGS:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Prometheus metrics
REQUEST_COUNT = Counter("nsfw_requests_total", "Total NSFW detection requests")
REQUEST_DURATION = Histogram("nsfw_request_duration_seconds", "NSFW detection request duration")
ERROR_COUNT = Counter("nsfw_errors_total", "Total NSFW detection errors")

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models")
# Primary NSFW model for nudity/explicit detection.
# AdamCodd/vit-base-nsfw-detector: binary sfw/nsfw.
# Multi-class models (drawings/hentai/neutral/porn/sexy) give better discrimination.
NSFW_MODEL_ID = os.getenv("NSFW_MODEL_ID", "AdamCodd/vit-base-nsfw-detector").strip()
NSFW_MODEL_REVISION = os.getenv("NSFW_MODEL_REVISION", "").strip() or None
NSFW_MODEL_SUBDIR = os.getenv("NSFW_MODEL_SUBDIR", "nsfw").strip()
# CLIP model for immodesty zero-shot detection.
# Uses semantic text prompts to score revealing clothing without explicit content.
CLIP_MODEL_ID = os.getenv("CLIP_MODEL_ID", "openai/clip-vit-base-patch32").strip()
CLIP_MODEL_SUBDIR = os.getenv("CLIP_MODEL_SUBDIR", "clip").strip()
CLIP_ENABLED = os.getenv("CLIP_ENABLED", "1") == "1"
USE_GPU = os.getenv("USE_GPU", "0") == "1"
MODEL_IDLE_UNLOAD_SECONDS = int(os.getenv("MODEL_IDLE_UNLOAD_SECONDS", "900"))
MODEL_IDLE_CHECK_SECONDS = int(os.getenv("MODEL_IDLE_CHECK_SECONDS", "30"))

# CLIP zero-shot prompts for immodesty classification.
# Uses 3-class discriminative softmax: class 0 is the immodesty target.
# Competitors must be semantically DISTANT so CLIP can cleanly separate them.
# "fully clothed people" as a competitor fails because it is too semantically
# close to the target and steals probability even for revealing scenes.
# "a racing car or street scene" and "people indoors" are general enough to
# work across diverse movie content while being clearly non-revealing.
_CLIP_CLASSES = [
    "a person wearing swimwear or bikini outdoors",  # class 0: target → immodesty
    "a racing car or street scene",                  # class 1: action/vehicles
    "people indoors",                                # class 2: indoor/clothed
]

# Runtime state — NSFW model
model_loaded = False
_models_ready = False
image_processor = None
nsfw_model = None
label_map = {}
model_lock = threading.Lock()
last_model_use_monotonic = time.monotonic()

# Runtime state — CLIP model
clip_loaded = False
clip_model = None
clip_processor = None
clip_lock = threading.Lock()

# Device selection — ROCm exposes itself as "cuda" to PyTorch
device = torch.device("cuda" if (USE_GPU and torch.cuda.is_available()) else "cpu")
gpu_available = USE_GPU and torch.cuda.is_available()
logger.info("NSFW detector device: %s (gpu_available=%s)", device, gpu_available)


def _local_model_dir() -> str:
    return os.path.join(MODEL_PATH, NSFW_MODEL_SUBDIR)


def _has_model_assets() -> bool:
    d = _local_model_dir()
    return os.path.isdir(d) and any(
        f.endswith((".safetensors", ".bin", ".pt"))
        for f in os.listdir(d)
    )


def _touch_model_use():
    global last_model_use_monotonic
    last_model_use_monotonic = time.monotonic()


def load_model() -> bool:
    global model_loaded, _models_ready, image_processor, nsfw_model, label_map

    with model_lock:
        if model_loaded and nsfw_model is not None:
            _touch_model_use()
            return True

        local_dir = _local_model_dir()
        has_local = _has_model_assets()
        source = local_dir if has_local else NSFW_MODEL_ID
        local_files_only = has_local

        logger.info("Loading NSFW model from: %s (device=%s)", source, device)
        try:
            proc = AutoImageProcessor.from_pretrained(
                source, revision=NSFW_MODEL_REVISION if not has_local else None,
                local_files_only=local_files_only
            )
            mdl = AutoModelForImageClassification.from_pretrained(
                source, revision=NSFW_MODEL_REVISION if not has_local else None,
                local_files_only=local_files_only
            )
            mdl.to(device)
            mdl.eval()

            lmap = {}
            if hasattr(mdl.config, "id2label"):
                lmap = {v.lower(): k for k, v in mdl.config.id2label.items()}
            logger.info("NSFW model labels: %s", list(lmap.keys()))

            image_processor = proc
            nsfw_model = mdl
            label_map = lmap
            model_loaded = True
            _models_ready = True
            _touch_model_use()
            logger.info("NSFW model loaded successfully on %s", device)
            return True

        except Exception as e:
            logger.error("NSFW model load failed: %s", e)
            image_processor = None
            nsfw_model = None
            model_loaded = False
            _models_ready = False
            return False


def unload_model(reason: str = "idle timeout"):
    global model_loaded, _models_ready, image_processor, nsfw_model

    with model_lock:
        if nsfw_model is None and not model_loaded:
            return False
        nsfw_model = None
        image_processor = None
        model_loaded = False
        _models_ready = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("NSFW model unloaded (%s)", reason)
        return True


def ensure_model_loaded() -> bool:
    if model_loaded and nsfw_model is not None:
        _touch_model_use()
        return True
    return load_model()


def _local_clip_dir() -> str:
    return os.path.join(MODEL_PATH, CLIP_MODEL_SUBDIR)


def _has_clip_assets() -> bool:
    d = _local_clip_dir()
    return os.path.isdir(d) and any(
        f.endswith((".safetensors", ".bin", ".pt"))
        for f in os.listdir(d)
    )


def load_clip_model() -> bool:
    """Load CLIP model for zero-shot immodesty detection."""
    global clip_loaded, clip_model, clip_processor

    if not CLIP_ENABLED:
        return False

    with clip_lock:
        if clip_loaded and clip_model is not None:
            return True

        local_dir = _local_clip_dir()
        has_local = _has_clip_assets()
        source = local_dir if has_local else CLIP_MODEL_ID

        logger.info("Loading CLIP model from: %s (device=%s)", source, device)
        try:
            clip_processor = CLIPProcessor.from_pretrained(source)
            clip_model = CLIPModel.from_pretrained(source)
            clip_model.to(device)
            clip_model.eval()
            clip_loaded = True
            logger.info("CLIP model loaded successfully on %s", device)
            return True
        except Exception as e:
            logger.error("CLIP model load failed: %s", e)
            clip_model = None
            clip_processor = None
            clip_loaded = False
            return False


def unload_clip_model(reason: str = "idle timeout"):
    global clip_loaded, clip_model, clip_processor
    with clip_lock:
        if clip_model is None:
            return False
        clip_model = None
        clip_processor = None
        clip_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("CLIP model unloaded (%s)", reason)
        return True


def ensure_clip_loaded() -> bool:
    if clip_loaded and clip_model is not None:
        return True
    return load_clip_model()


def clip_immodesty_score(img: Image.Image) -> float:
    """Return immodesty score using CLIP zero-shot N-class classification.

    Returns P(class 0 = revealing clothing) from a softmax over discriminative
    class prompts. The competitors must be semantically distant so CLIP can
    cleanly separate them; a generic 'fully clothed' binary fails because its
    cosine similarity stays close to the positive prompt for all content.

    Returns a value in [0, 1] where higher = more revealing.
    """
    if not clip_loaded or clip_model is None:
        return 0.0

    try:
        inputs = clip_processor(
            text=_CLIP_CLASSES,
            images=[img],
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = clip_model(**inputs).logits_per_image[0]  # [num_classes]
            probs = torch.softmax(logits, dim=0).tolist()

        # P(class 0) = P(revealing clothing)
        return float(probs[0])
    except Exception as e:
        logger.warning("CLIP immodesty scoring failed: %s", e)
        return 0.0


def _idle_unload_worker():
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        logger.info("Idle model unload disabled (MODEL_IDLE_UNLOAD_SECONDS <= 0)")
        return
    while True:
        time.sleep(max(5, MODEL_IDLE_CHECK_SECONDS))
        idle = time.monotonic() - last_model_use_monotonic
        if idle >= MODEL_IDLE_UNLOAD_SECONDS:
            if model_loaded:
                unload_model(reason=f"idle for {int(idle)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)")
            if clip_loaded:
                unload_clip_model(reason=f"idle for {int(idle)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)")


def _augment(img: Image.Image):
    """Yield original + mirror for mild TTA."""
    yield img
    yield ImageOps.mirror(img)


def classify_image(img: Image.Image) -> dict:
    """Run NSFW classification and return raw label scores."""
    frames = list(_augment(img))
    inputs = image_processor(images=frames, return_tensors="pt").to(device)

    with torch.no_grad():
        logits = nsfw_model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).mean(dim=0)

    scores = {}
    for i, p in enumerate(probs.tolist()):
        label = nsfw_model.config.id2label.get(i, str(i)).lower()
        scores[label] = p

    _touch_model_use()
    return scores


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})


@app.route("/health", methods=["GET"])
def health_check():
    idle_seconds = int(time.monotonic() - last_model_use_monotonic)
    return jsonify({
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "ready": _models_ready,
        "lazy_load_available": _has_model_assets(),
        "model_id": NSFW_MODEL_ID,
        "clip_enabled": CLIP_ENABLED,
        "clip_loaded": clip_loaded,
        "clip_model_id": CLIP_MODEL_ID if CLIP_ENABLED else None,
        "model_idle_unload_seconds": MODEL_IDLE_UNLOAD_SECONDS,
        "seconds_since_model_use": idle_seconds,
        "gpu_available": gpu_available,
        "gpu_enabled": USE_GPU,
        "device": str(device),
        "timestamp": datetime.now().isoformat(),
        "service": "nsfw-detector",
    })


@app.route("/ready", methods=["GET"])
def ready():
    if _models_ready:
        return jsonify({"status": "ready", "models_loaded": True})
    if _has_model_assets():
        return jsonify({
            "status": "ready",
            "models_loaded": False,
            "lazy_load": True,
            "reason": "Model will load on-demand",
        })
    if NSFW_MODEL_ID:
        return jsonify({
            "status": "ready",
            "models_loaded": False,
            "lazy_download": True,
            "reason": "Model will download and load on first inference request",
        })
    return jsonify({
        "status": "degraded",
        "models_loaded": False,
        "reason": "NSFW model not loaded",
    }), 503


@app.route("/analyze", methods=["POST"])
@REQUEST_DURATION.time()
def analyze():
    REQUEST_COUNT.inc()
    try:
        if not ensure_model_loaded():
            ERROR_COUNT.inc()
            return jsonify({"error": "Model not loaded", "degraded": True}), 503

        if "image" not in request.files:
            ERROR_COUNT.inc()
            return jsonify({"error": "No image provided"}), 400

        file = request.files["image"]
        if not file.filename:
            ERROR_COUNT.inc()
            return jsonify({"error": "Empty filename"}), 400

        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        scores = classify_image(img)

        # Map NSFW model scores to nudity.
        # Multi-class models (drawings/hentai/neutral/porn/sexy):
        #   nudity    = porn_score + hentai_score
        #   nsfw_fallback_immodesty = sexy_score
        # Binary models (sfw/nsfw or normal/nsfw):
        #   nudity    = nsfw_score
        #   nsfw_fallback_immodesty = nsfw_score * 0.4 (heuristic)
        nudity = scores.get("porn", 0.0) + scores.get("hentai", 0.0)
        nsfw_fallback_immodesty = scores.get("sexy", 0.0)
        if nudity == 0.0 and nsfw_fallback_immodesty == 0.0:
            nsfw_score = scores.get("nsfw", scores.get("unsafe", 0.0))
            nudity = nsfw_score
            nsfw_fallback_immodesty = nsfw_score * 0.4

        # Use CLIP zero-shot for immodesty if available.
        # CLIP semantically scores "revealing clothing" vs "clothed person"
        # and produces meaningful immodesty scores for swimwear/bikinis that
        # binary NSFW models cannot distinguish from safe content.
        if CLIP_ENABLED and ensure_clip_loaded():
            immodesty = clip_immodesty_score(img)
        else:
            immodesty = nsfw_fallback_immodesty

        return jsonify({
            "success": True,
            "nudity": nudity,
            "immodesty": immodesty,
            "categories": scores,
            "clip_immodesty": immodesty if CLIP_ENABLED and clip_loaded else None,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        ERROR_COUNT.inc()
        logger.error("Error processing request: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest()


if __name__ == "__main__":
    threading.Thread(target=_idle_unload_worker, daemon=True, name="nsfw-idle-unloader").start()
    if CLIP_ENABLED:
        threading.Thread(target=load_clip_model, daemon=True, name="nsfw-clip-preload").start()
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
