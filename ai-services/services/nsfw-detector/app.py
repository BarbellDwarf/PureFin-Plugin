"""NSFW Detection Service - REST API using a HuggingFace image classifier."""

import gc
import io
import logging
import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, request
from PIL import Image, ImageOps
from prometheus_client import Counter, Histogram, generate_latest

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("nsfw_requests_total", "Total NSFW detection requests")
REQUEST_DURATION = Histogram("nsfw_request_duration_seconds", "NSFW detection request duration")
ERROR_COUNT = Counter("nsfw_errors_total", "Total NSFW detection errors")

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models")
NSFW_MODEL_ID = os.getenv("NSFW_MODEL_ID", "AdamCodd/vit-base-nsfw-detector").strip()
NSFW_MODEL_REVISION = os.getenv("NSFW_MODEL_REVISION", "").strip() or None
NSFW_MODEL_SUBDIR = os.getenv("NSFW_MODEL_SUBDIR", "nsfw").strip()
USE_GPU = os.getenv("USE_GPU", "0") == "1"
MODEL_IDLE_UNLOAD_SECONDS = int(os.getenv("MODEL_IDLE_UNLOAD_SECONDS", "900"))
MODEL_IDLE_CHECK_SECONDS = int(os.getenv("MODEL_IDLE_CHECK_SECONDS", "30"))

# Runtime state
model_loaded = False
_models_ready = False
image_processor = None
nsfw_model = None
label_map = {}
model_lock = threading.Lock()
last_model_use_monotonic = time.monotonic()

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


def _idle_unload_worker():
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        logger.info("Idle model unload disabled (MODEL_IDLE_UNLOAD_SECONDS <= 0)")
        return
    while True:
        time.sleep(max(5, MODEL_IDLE_CHECK_SECONDS))
        if not model_loaded:
            continue
        idle = time.monotonic() - last_model_use_monotonic
        if idle >= MODEL_IDLE_UNLOAD_SECONDS:
            unload_model(reason=f"idle for {int(idle)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)")


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

        # Map multi-class scores to the expected API contract.
        # AdamCodd model: drawings, hentai, neutral, porn, sexy
        # Fallback for binary models (normal/nsfw)
        nudity = scores.get("porn", 0.0) + scores.get("hentai", 0.0)
        immodesty = scores.get("sexy", 0.0)
        if nudity == 0.0 and immodesty == 0.0:
            nsfw_score = scores.get("nsfw", scores.get("unsafe", 0.0))
            nudity = nsfw_score
            immodesty = nsfw_score * 0.4

        return jsonify({
            "success": True,
            "nudity": nudity,
            "immodesty": immodesty,
            "categories": scores,
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
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
