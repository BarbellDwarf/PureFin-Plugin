"""Violence Detection Service - REST API using a HuggingFace image classifier."""

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
REQUEST_COUNT = Counter("violence_requests_total", "Total violence detector requests")
REQUEST_DURATION = Histogram("violence_request_duration_seconds", "Violence detector request duration")
ERROR_COUNT = Counter("violence_errors_total", "Total violence detector errors")

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models")
MODEL_PROFILES = {
    "speed": {
        "model_id": "nghiabntl/vit-base-violence-detection",
        "tta_passes": 1,
        "description": "Fastest startup/inference profile.",
    },
    "balanced": {
        "model_id": "jaranohaal/vit-base-violence-detection",
        "tta_passes": 1,
        "description": "Default balanced profile.",
    },
    "quality": {
        "model_id": "framasoft/vit-base-violence-detection",
        "tta_passes": 2,
        "description": "Higher quality profile using test-time augmentation.",
    },
}

VIOLENCE_MODEL_PROFILE = os.getenv("VIOLENCE_MODEL_PROFILE", "balanced").strip().lower()
if VIOLENCE_MODEL_PROFILE not in MODEL_PROFILES:
    logger.warning(
        "Unknown VIOLENCE_MODEL_PROFILE '%s'. Falling back to 'balanced'.",
        VIOLENCE_MODEL_PROFILE,
    )
    VIOLENCE_MODEL_PROFILE = "balanced"

VIOLENCE_MODEL_ID = (
    os.getenv("VIOLENCE_MODEL_ID", "").strip()
    or MODEL_PROFILES[VIOLENCE_MODEL_PROFILE]["model_id"]
)
VIOLENCE_MODEL_REVISION = os.getenv("VIOLENCE_MODEL_REVISION", "").strip() or None
VIOLENCE_MODEL_SUBDIR = (
    os.getenv("VIOLENCE_MODEL_SUBDIR", "").strip()
    or os.path.join("violence", VIOLENCE_MODEL_PROFILE)
)
VIOLENCE_TTA_PASSES = int(
    os.getenv("VIOLENCE_TTA_PASSES", str(MODEL_PROFILES[VIOLENCE_MODEL_PROFILE]["tta_passes"]))
)
USE_GPU = os.getenv("USE_GPU", "0") == "1"
MODEL_IDLE_UNLOAD_SECONDS = int(os.getenv("MODEL_IDLE_UNLOAD_SECONDS", "900"))
MODEL_IDLE_CHECK_SECONDS = int(os.getenv("MODEL_IDLE_CHECK_SECONDS", "30"))

# Runtime state
model_loaded = False
_models_ready = False
image_processor = None
violence_model = None
label_map = {}
model_lock = threading.Lock()
last_model_use_monotonic = time.monotonic()


def _resolve_device() -> str:
    """Pick an inference device based on runtime support and USE_GPU flag."""
    if USE_GPU and torch.cuda.is_available():
        return "cuda"
    if USE_GPU and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


DEVICE = _resolve_device()


def _model_dir() -> str:
    return os.path.join(MODEL_PATH, VIOLENCE_MODEL_SUBDIR)


def _touch_model_use() -> None:
    """Record last model use time for idle unload logic."""
    global last_model_use_monotonic
    last_model_use_monotonic = time.monotonic()


def _has_model_assets() -> bool:
    """Return True when a local cached HF model is present."""
    model_dir = _model_dir()
    if not os.path.isdir(model_dir):
        return False
    if not os.path.isfile(os.path.join(model_dir, "config.json")):
        return False
    has_weights = (
        os.path.isfile(os.path.join(model_dir, "model.safetensors"))
        or os.path.isfile(os.path.join(model_dir, "pytorch_model.bin"))
    )
    return has_weights


def _normalize_label(label: str) -> str:
    return label.strip().lower().replace("-", "_").replace(" ", "_")


def _extract_violence_score(scores: dict[str, float]) -> float:
    """Pick the violence probability from model output labels."""
    if not scores:
        return 0.0

    normalized = {_normalize_label(k): float(v) for k, v in scores.items()}

    for key in ("violence", "violent", "general_violence"):
        if key in normalized:
            return max(0.0, min(1.0, normalized[key]))

    for key, value in normalized.items():
        if "violence" in key or "violent" in key:
            return max(0.0, min(1.0, value))

    for key in ("non_violence", "nonviolent", "not_violent"):
        if key in normalized and len(normalized) == 2:
            return max(0.0, min(1.0, 1.0 - normalized[key]))

    # Last-resort fallback: use the max score from all labels.
    return max(0.0, min(1.0, max(normalized.values())))


def load_model() -> bool:
    """Load the violence classifier model from local cache or HuggingFace."""
    global model_loaded, _models_ready, image_processor, violence_model, label_map
    with model_lock:
        if model_loaded and image_processor is not None and violence_model is not None:
            _touch_model_use()
            return True

        model_loaded = False
        _models_ready = False
        image_processor = None
        violence_model = None
        label_map = {}

        try:
            model_dir = _model_dir()
            os.makedirs(model_dir, exist_ok=True)

            if _has_model_assets():
                logger.info("Loading violence model from local cache: %s", model_dir)
                image_processor = AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
                violence_model = AutoModelForImageClassification.from_pretrained(
                    model_dir, local_files_only=True
                )
            else:
                logger.info("Downloading violence model from HuggingFace: %s", VIOLENCE_MODEL_ID)
                image_processor = AutoImageProcessor.from_pretrained(
                    VIOLENCE_MODEL_ID, revision=VIOLENCE_MODEL_REVISION
                )
                violence_model = AutoModelForImageClassification.from_pretrained(
                    VIOLENCE_MODEL_ID, revision=VIOLENCE_MODEL_REVISION
                )
                image_processor.save_pretrained(model_dir)
                violence_model.save_pretrained(model_dir)
                logger.info("Cached violence model at %s", model_dir)

            violence_model.to(DEVICE)
            violence_model.eval()

            raw_map = getattr(violence_model.config, "id2label", {}) or {}
            label_map = {int(k): str(v) for k, v in raw_map.items()}
            if not label_map:
                label_map = {0: "non_violence", 1: "violence"}

            model_loaded = True
            _models_ready = True
            _touch_model_use()
            logger.info("Violence model ready on device=%s", DEVICE)
            return True
        except Exception as ex:  # noqa: BLE001 - service must surface structured failure
            logger.error("Failed to load violence model: %s", ex, exc_info=True)
            model_loaded = False
            _models_ready = False
            image_processor = None
            violence_model = None
            label_map = {}
            return False


def unload_model(reason: str = "idle timeout") -> bool:
    """Unload model and release memory."""
    global model_loaded, _models_ready, image_processor, violence_model, label_map
    with model_lock:
        if image_processor is None and violence_model is None and not model_loaded:
            return False

        image_processor = None
        violence_model = None
        label_map = {}
        model_loaded = False
        _models_ready = False

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Violence model unloaded (%s)", reason)
        return True


def ensure_model_loaded() -> bool:
    """Lazy-load model on first inference request."""
    if model_loaded and image_processor is not None and violence_model is not None:
        _touch_model_use()
        return True
    return load_model()


def _idle_unload_worker() -> None:
    """Background worker that unloads model after inactivity."""
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        logger.info("Idle unload disabled (MODEL_IDLE_UNLOAD_SECONDS <= 0)")
        return

    while True:
        time.sleep(max(5, MODEL_IDLE_CHECK_SECONDS))
        if not model_loaded:
            continue
        idle_seconds = time.monotonic() - last_model_use_monotonic
        if idle_seconds >= MODEL_IDLE_UNLOAD_SECONDS:
            unload_model(reason=f"idle for {int(idle_seconds)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)")


def analyze_violence(image_data: Image.Image) -> dict:
    """Run violence classification for one image."""
    if image_processor is None or violence_model is None:
        raise RuntimeError("Violence model is not loaded")

    image = image_data.convert("RGB")
    inference_images = [image]
    if VIOLENCE_TTA_PASSES > 1:
        inference_images.append(ImageOps.mirror(image))

    accumulated_scores = {}
    for inference_image in inference_images:
        inputs = image_processor(images=inference_image, return_tensors="pt")
        inputs = {k: v.to(DEVICE) if hasattr(v, "to") else v for k, v in inputs.items()}

        with torch.no_grad():
            logits = violence_model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1)[0].cpu().tolist()

        for idx, score in enumerate(probabilities):
            label = label_map.get(idx, f"class_{idx}")
            accumulated_scores[label] = accumulated_scores.get(label, 0.0) + float(score)

    scores = {}
    divisor = max(1, len(inference_images))
    for label, score in accumulated_scores.items():
        scores[label] = score / divisor

    top_label = max(scores, key=scores.get)
    violence_score = _extract_violence_score(scores)
    _touch_model_use()

    return {
        "violence": float(violence_score),
        "violence_score": float(violence_score),
        "label": top_label,
        "scores": scores,
    }


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    idle_seconds = int(time.monotonic() - last_model_use_monotonic)
    return jsonify(
        {
            "status": "healthy" if model_loaded else "degraded",
            "model_loaded": model_loaded,
            "ready": _models_ready,
            "lazy_load_available": _has_model_assets() or bool(VIOLENCE_MODEL_ID),
            "model_idle_unload_seconds": MODEL_IDLE_UNLOAD_SECONDS,
            "seconds_since_model_use": idle_seconds,
            "gpu_available": torch.cuda.is_available(),
            "gpu_enabled": USE_GPU,
            "device": DEVICE,
            "model_profile": VIOLENCE_MODEL_PROFILE,
            "model_id": VIOLENCE_MODEL_ID,
            "tta_passes": VIOLENCE_TTA_PASSES,
            "available_profiles": MODEL_PROFILES,
            "timestamp": datetime.now().isoformat(),
            "service": "violence-detector",
        }
    )


@app.route("/ready", methods=["GET"])
def ready():
    """Readiness endpoint."""
    if _models_ready:
        return jsonify({"status": "ready", "models_loaded": True})
    if _has_model_assets():
        return jsonify(
            {
                "status": "ready",
                "models_loaded": False,
                "lazy_load": True,
                "reason": "Model will load on-demand for the next inference request",
            }
        )
    if VIOLENCE_MODEL_ID:
        return jsonify(
            {
                "status": "ready",
                "models_loaded": False,
                "lazy_download": True,
                "reason": "Model will download and load on first inference request",
            }
        )
    return jsonify(
        {
            "status": "degraded",
            "models_loaded": False,
            "reason": "No model assets configured",
        }
    ), 503


@app.route("/analyze", methods=["POST"])
@REQUEST_DURATION.time()
def analyze():
    """Analyze one image for violence."""
    REQUEST_COUNT.inc()
    try:
        if not ensure_model_loaded():
            ERROR_COUNT.inc()
            return jsonify({"error": "Model not loaded", "degraded": True, "service": "violence-detector"}), 503

        if "image" not in request.files:
            ERROR_COUNT.inc()
            return jsonify({"error": "No image provided"}), 400

        image_file = request.files["image"]
        if image_file.filename == "":
            ERROR_COUNT.inc()
            return jsonify({"error": "Empty filename"}), 400

        image_data = Image.open(io.BytesIO(image_file.read()))
        result = analyze_violence(image_data)

        return jsonify(
            {
                "success": True,
                **result,
                "model": {
                    "id": VIOLENCE_MODEL_ID,
                    "profile": VIOLENCE_MODEL_PROFILE,
                    "revision": VIOLENCE_MODEL_REVISION,
                    "device": DEVICE,
                    "tta_passes": VIOLENCE_TTA_PASSES,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as ex:  # noqa: BLE001 - service must surface structured failure
        ERROR_COUNT.inc()
        logger.error("Violence analysis error: %s", ex, exc_info=True)
        return jsonify({"error": str(ex)}), 500


@app.route("/unload", methods=["POST"])
def unload():
    """Unload model manually."""
    unloaded = unload_model(reason="manual unload endpoint")
    return jsonify(
        {
            "success": True,
            "unloaded": unloaded,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


if __name__ == "__main__":
    threading.Thread(
        target=_idle_unload_worker,
        daemon=True,
        name="violence-idle-unloader",
    ).start()

    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=False)
