"""NSFW Detection Service - REST API for content analysis."""

import os
import logging
import gc
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import numpy as np
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('nsfw_requests_total', 'Total NSFW detection requests')
REQUEST_DURATION = Histogram('nsfw_request_duration_seconds', 'NSFW detection request duration')
ERROR_COUNT = Counter('nsfw_errors_total', 'Total NSFW detection errors')

# Model placeholder - in production, load actual NSFW model
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models')
USE_GPU = os.getenv('USE_GPU', '0') == '1'
MODEL_IDLE_UNLOAD_SECONDS = int(os.getenv('MODEL_IDLE_UNLOAD_SECONDS', '900'))
MODEL_IDLE_CHECK_SECONDS = int(os.getenv('MODEL_IDLE_CHECK_SECONDS', '30'))
model_loaded = False
nsfw_model = None
_models_ready = False
model_lock = threading.Lock()
last_model_use_monotonic = time.monotonic()

# GPU detection
gpu_available = False
try:
    # Try to import TensorFlow and check for GPU
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if gpus and USE_GPU:
        gpu_available = True
        logger.info(f"GPU detected: {len(gpus)} GPU(s) available")
        for gpu in gpus:
            logger.info(f"  - {gpu.name}")
        # Configure GPU memory growth to avoid OOM
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    else:
        logger.info("Using CPU for inference")
except Exception as e:
    logger.info(f"GPU not available, using CPU: {e}")

# NSFW categories
CATEGORIES = ['drawings', 'hentai', 'neutral', 'porn', 'sexy']


def load_model():
    """Load NSFW detection model."""
    global model_loaded, nsfw_model, _models_ready, last_model_use_monotonic
    with model_lock:
        if model_loaded and nsfw_model is not None:
            last_model_use_monotonic = time.monotonic()
            return True

        try:
            # Try loading H5 model first (our custom model)
            h5_path = os.path.join(MODEL_PATH, 'nsfw', 'nsfw_model.h5')
            savedmodel_path = os.path.join(MODEL_PATH, 'nsfw', 'mobilenet_v2_140_224')

            import tensorflow as tf

            if os.path.exists(h5_path):
                logger.info("Loading NSFW H5 model from %s", h5_path)
                try:
                    nsfw_model = tf.keras.models.load_model(h5_path)
                    logger.info("Successfully loaded NSFW H5 model")
                    model_loaded = True
                    _models_ready = True

                    # Test prediction to ensure model works
                    test_input = tf.random.normal((1, 224, 224, 3))
                    _ = nsfw_model.predict(test_input, verbose=0)
                    logger.info("Model test prediction successful")
                    last_model_use_monotonic = time.monotonic()
                    return True

                except Exception as h5_error:
                    logger.error("H5 model loading failed: %s", h5_error)

            elif os.path.exists(savedmodel_path):
                logger.info("Loading NSFW SavedModel from %s", savedmodel_path)
                try:
                    nsfw_model = tf.keras.models.load_model(savedmodel_path)
                    logger.info("Successfully loaded NSFW TensorFlow SavedModel")
                    model_loaded = True
                    _models_ready = True

                    # Test prediction to ensure model works
                    test_input = tf.random.normal((1, 224, 224, 3))
                    _ = nsfw_model.predict(test_input, verbose=0)
                    logger.info("Model test prediction successful")
                    last_model_use_monotonic = time.monotonic()
                    return True

                except Exception as tf_error:
                    logger.error("SavedModel loading failed: %s", tf_error)
            else:
                logger.warning("No NSFW model found at %s or %s", h5_path, savedmodel_path)

            model_loaded = False
            _models_ready = False
            nsfw_model = None
            return False

        except Exception as e:
            logger.error("Error loading model: %s", e)
            model_loaded = False
            _models_ready = False
            nsfw_model = None
            return False


def _has_model_assets():
    """Return True when model files exist and lazy-load can succeed."""
    h5_path = os.path.join(MODEL_PATH, 'nsfw', 'nsfw_model.h5')
    savedmodel_path = os.path.join(MODEL_PATH, 'nsfw', 'mobilenet_v2_140_224')
    return os.path.exists(h5_path) or os.path.exists(savedmodel_path)


def _touch_model_use():
    """Record model usage for idle-unload tracking."""
    global last_model_use_monotonic
    last_model_use_monotonic = time.monotonic()


def unload_model(reason="idle timeout"):
    """Unload model from memory."""
    global model_loaded, nsfw_model, _models_ready
    with model_lock:
        if nsfw_model is None and not model_loaded:
            return False
        nsfw_model = None
        model_loaded = False
        _models_ready = False
        try:
            import tensorflow as tf
            tf.keras.backend.clear_session()
        except Exception:
            pass
        gc.collect()
        logger.info("NSFW model unloaded (%s)", reason)
        return True


def ensure_model_loaded():
    """Load model on demand when a request arrives."""
    if model_loaded and nsfw_model is not None:
        _touch_model_use()
        return True
    return load_model()


def _idle_unload_worker():
    """Background worker that unloads model after inactivity."""
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        logger.info("Idle model unload disabled (MODEL_IDLE_UNLOAD_SECONDS <= 0)")
        return

    while True:
        time.sleep(max(5, MODEL_IDLE_CHECK_SECONDS))
        if not model_loaded:
            continue
        idle_seconds = time.monotonic() - last_model_use_monotonic
        if idle_seconds >= MODEL_IDLE_UNLOAD_SECONDS:
            unload_model(
                reason=f'idle for {int(idle_seconds)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)')


def analyze_image(image_data):
    """Analyze image for NSFW content.
    
    Args:
        image_data: PIL Image object
        
    Returns:
        Dictionary with category scores
    """
    global nsfw_model, model_loaded
    
    try:
        # Preprocess image
        img = image_data.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img) / 255.0
        
        if not model_loaded or nsfw_model is None:
            raise RuntimeError("NSFW model is not loaded")
        
        # Prepare input for model
        input_batch = np.expand_dims(img_array, axis=0)
        
        # Get model prediction
        predictions = nsfw_model.predict(input_batch, verbose=0)[0]
        _touch_model_use()
        logger.debug(f"Real NSFW model predictions: {predictions}")
        
        results = {
            category: float(score) 
            for category, score in zip(CATEGORIES, predictions)
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    idle_seconds = int(time.monotonic() - last_model_use_monotonic)
    return jsonify({
        'status': 'healthy' if model_loaded else 'degraded',
        'model_loaded': model_loaded,
        'ready': _models_ready,
        'lazy_load_available': _has_model_assets(),
        'model_idle_unload_seconds': MODEL_IDLE_UNLOAD_SECONDS,
        'seconds_since_model_use': idle_seconds,
        'gpu_available': gpu_available,
        'gpu_enabled': USE_GPU,
        'timestamp': datetime.now().isoformat(),
        'service': 'nsfw-detector'
    })


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness endpoint — returns 200 only when the model is loaded and inference is possible."""
    if _models_ready:
        return jsonify({'status': 'ready', 'models_loaded': True})
    if _has_model_assets():
        return jsonify({
            'status': 'ready',
            'models_loaded': False,
            'lazy_load': True,
            'reason': 'Model will load on-demand for the next inference request'
        })
    return jsonify({
        'status': 'degraded',
        'models_loaded': False,
        'reason': 'NSFW model not loaded'
    }), 503


@app.route('/analyze', methods=['POST'])
@REQUEST_DURATION.time()
def analyze():
    """Analyze image for NSFW content."""
    REQUEST_COUNT.inc()
    
    try:
        # Lazy-load model if needed.
        if not ensure_model_loaded():
            ERROR_COUNT.inc()
            return jsonify({'error': 'Model not loaded', 'degraded': True}), 503
        
        # Get image from request
        if 'image' not in request.files:
            ERROR_COUNT.inc()
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            ERROR_COUNT.inc()
            return jsonify({'error': 'Empty filename'}), 400
        
        # Load and analyze image
        image_data = Image.open(io.BytesIO(file.read()))
        category_results = analyze_image(image_data)
        
        # Calculate nudity and immodesty scores from category results
        # Nudity = porn + hentai
        # Immodesty = sexy
        nudity_score = category_results.get('porn', 0) + category_results.get('hentai', 0)
        immodesty_score = category_results.get('sexy', 0)
        
        return jsonify({
            'success': True,
            'nudity': nudity_score,
            'immodesty': immodesty_score,
            'categories': category_results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


if __name__ == '__main__':
    # Start idle-unload worker (model loading is lazy on first inference request).
    threading.Thread(target=_idle_unload_worker, daemon=True, name='nsfw-idle-unloader').start()
    
    # Run Flask app
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
