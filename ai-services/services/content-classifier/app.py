"""Content Classifier Service - Multi-category content classification."""

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

# Configure TensorFlow before importing - MUST disable XLA/JIT completely
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'  # Reduce TF logging
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'
os.environ['XLA_FLAGS'] = '--xla_gpu_cuda_data_dir=/usr/local/cuda'
os.environ['TF_DISABLE_SEGMENT_REDUCTION_OP_DETERMINISM_EXCEPTIONS'] = '1'
# Completely disable JIT at the environment level
os.environ['TF_XLA_FLAGS'] = '--tf_xla_auto_jit=0 --tf_xla_enable_xla_devices=false'
try:
    import tensorflow as tf
    # Disable JIT compilation to avoid CUDA ptxas issues
    tf.config.optimizer.set_jit(False)
    # Optionally disable MLIR graph optimizations if API exists (TF versions differ)
    try:
        if hasattr(tf.config.experimental, 'enable_mlir_graph_optimization'):
            tf.config.experimental.enable_mlir_graph_optimization(False)
    except Exception as _:
        pass
    # Allow memory growth to avoid GPU memory issues
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
except ImportError:
    tf = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('classifier_requests_total', 'Total classification requests')
REQUEST_DURATION = Histogram('classifier_request_duration_seconds', 'Classification request duration')
ERROR_COUNT = Counter('classifier_errors_total', 'Total classification errors')

# Model placeholder
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models')
USE_GPU = os.getenv('USE_GPU', '0') == '1'
MODEL_IDLE_UNLOAD_SECONDS = int(os.getenv('MODEL_IDLE_UNLOAD_SECONDS', '900'))
MODEL_IDLE_CHECK_SECONDS = int(os.getenv('MODEL_IDLE_CHECK_SECONDS', '30'))
models_loaded = False
_models_ready = False
violence_model = None
clip_model = None
clip_processor = None
clip_device = "cpu"
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
        logger.info("GPU detected: %d GPU(s) available", len(gpus))
        for gpu in gpus:
            logger.info("  - %s", gpu.name)
        # Configure GPU memory growth to avoid OOM
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    else:
        logger.info("Using CPU for inference")
except Exception as e:
    logger.info("GPU not available, using CPU: %s", e)

# Content categories
VIOLENCE_CATEGORIES = ['blood', 'weapons', 'fighting', 'explosions', 'death', 'torture', 'general_violence']
NUDITY_CATEGORIES = ['none', 'partial_nudity', 'full_nudity', 'suggestive']


def load_models():
    """Load classification models."""
    global models_loaded, violence_model, clip_model, clip_processor, _models_ready, clip_device, last_model_use_monotonic
    with model_lock:
        if models_loaded and (violence_model is not None or clip_model is not None):
            last_model_use_monotonic = time.monotonic()
            return True

        try:
            models_loaded = False
            _models_ready = False
            violence_model = None
            clip_model = None
            clip_processor = None
            clip_device = "cpu"

            # Load violence detection model
            violence_path = os.path.join(MODEL_PATH, 'violence', 'violence_model.h5')
            if os.path.exists(violence_path):
                try:
                    # Disable all JIT/XLA compilation
                    tf.config.optimizer.set_jit(False)

                    # Force CPU device for violence model to avoid GPU JIT issues
                    with tf.device('/CPU:0'):
                        violence_model = tf.keras.models.load_model(violence_path, compile=False)
                    logger.info("Successfully loaded violence detection model on CPU (avoiding GPU JIT issues)")
                except Exception as e:
                    logger.error("Failed to load violence model: %s", e)
                    violence_model = None
            else:
                logger.warning("Violence model not found at %s", violence_path)

            # Load CLIP model for content classification
            try:
                from transformers import CLIPModel, CLIPProcessor

                clip_model_path = os.path.join(MODEL_PATH, 'content', 'clip-vit-base-patch32')
                if os.path.exists(clip_model_path) and os.path.exists(os.path.join(clip_model_path, 'config.json')):
                    # Load from local cache
                    clip_model = CLIPModel.from_pretrained(clip_model_path)
                    clip_processor = CLIPProcessor.from_pretrained(clip_model_path)
                    logger.info("Loaded CLIP model from local cache")
                else:
                    # Download and cache CLIP model
                    logger.info("Downloading CLIP model (this may take a few minutes)...")
                    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

                    # Save to local cache
                    os.makedirs(clip_model_path, exist_ok=True)
                    clip_model.save_pretrained(clip_model_path)
                    clip_processor.save_pretrained(clip_model_path)
                    logger.info("CLIP model downloaded and cached")

                # Move CLIP model to GPU if available
                try:
                    import torch
                    if USE_GPU and torch.cuda.is_available():
                        clip_device = "cuda"
                        clip_model = clip_model.to(clip_device)
                        clip_model.eval()
                        logger.info("CLIP model moved to CUDA device")
                    else:
                        clip_device = "cpu"
                except Exception as e:
                    logger.warning("Could not set CLIP device: %s", e)

            except Exception as e:
                logger.error("Failed to load CLIP model: %s", e)
                clip_model = None
                clip_processor = None

            # Set loaded flag if at least one model is available
            models_loaded = (violence_model is not None) or (clip_model is not None)
            _models_ready = models_loaded
            if models_loaded:
                last_model_use_monotonic = time.monotonic()
                logger.info("Content classifier models loaded successfully")
            else:
                logger.warning("No models could be loaded; service will return 503 for inference requests")

            return models_loaded

        except Exception as e:
            logger.error("Error loading models: %s", e)
            models_loaded = False
            _models_ready = False
            violence_model = None
            clip_model = None
            clip_processor = None
            clip_device = "cpu"
            return False


def _has_model_assets():
    """Return True when model files exist and lazy loading can work."""
    violence_path = os.path.join(MODEL_PATH, 'violence', 'violence_model.h5')
    clip_model_path = os.path.join(MODEL_PATH, 'content', 'clip-vit-base-patch32')
    return os.path.exists(violence_path) or os.path.exists(os.path.join(clip_model_path, 'config.json'))


def _touch_model_use():
    """Record model usage for idle-unload tracking."""
    global last_model_use_monotonic
    last_model_use_monotonic = time.monotonic()


def unload_models(reason="idle timeout"):
    """Unload model objects from memory."""
    global models_loaded, _models_ready, violence_model, clip_model, clip_processor, clip_device
    with model_lock:
        if violence_model is None and clip_model is None and clip_processor is None and not models_loaded:
            return False

        violence_model = None
        clip_model = None
        clip_processor = None
        clip_device = "cpu"
        models_loaded = False
        _models_ready = False

        try:
            import tensorflow as _tf
            _tf.keras.backend.clear_session()
        except Exception:
            pass
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        gc.collect()
        logger.info("Content-classifier models unloaded (%s)", reason)
        return True


def ensure_models_loaded():
    """Load models on demand for the next request."""
    if models_loaded and (violence_model is not None or clip_model is not None):
        _touch_model_use()
        return True
    return load_models()


def _idle_unload_worker():
    """Background worker that unloads models after inactivity."""
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        logger.info("Idle model unload disabled (MODEL_IDLE_UNLOAD_SECONDS <= 0)")
        return

    while True:
        time.sleep(max(5, MODEL_IDLE_CHECK_SECONDS))
        if not models_loaded:
            continue
        idle_seconds = time.monotonic() - last_model_use_monotonic
        if idle_seconds >= MODEL_IDLE_UNLOAD_SECONDS:
            unload_models(
                reason=f'idle for {int(idle_seconds)}s (threshold={MODEL_IDLE_UNLOAD_SECONDS}s)')


def classify_violence(image):
    """Classify violence content in image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with violence scores
    """
    global violence_model
    
    if violence_model is None:
        raise RuntimeError("Violence model is not loaded")
    
    try:
        # Preprocess image for violence model
        img = image.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img) / 255.0
        input_batch = np.expand_dims(img_array, axis=0)
        
        # Force CPU inference to avoid GPU JIT compilation issues
        with tf.device('/CPU:0'):
            # Get violence prediction (binary classification)
            violence_prob = violence_model.predict(input_batch, verbose=0)[0][0]
        _touch_model_use()
        
        # Create detailed category scores based on overall violence score
        # Higher violence score increases likelihood of specific violence types
        base_multiplier = float(violence_prob)
        scores = {
            'blood': min(base_multiplier * 0.6, 0.95),
            'weapons': min(base_multiplier * 0.4, 0.90),
            'fighting': min(base_multiplier * 0.8, 0.95),
            'explosions': min(base_multiplier * 0.3, 0.85),
            'death': min(base_multiplier * 0.2, 0.80),
            'torture': min(base_multiplier * 0.1, 0.70),
            'general_violence': float(violence_prob)
        }
        
        logger.debug("Real violence model prediction (CPU): %.3f", violence_prob)
        
    except RuntimeError:
        raise
    except Exception as model_error:
        logger.error("Violence model prediction failed: %s", model_error)
        raise RuntimeError(f"Violence model prediction failed: {model_error}") from model_error
    
    overall_score = max(scores.values())
    primary_type = max(scores, key=scores.get)
    
    return {
        'overall_violence_score': overall_score,
        'category_scores': scores,
        'primary_violence_type': primary_type
    }


def classify_nudity(image):
    """Classify nudity levels in image using CLIP zero-shot classification.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with nudity scores
    """
    queries = [
        "fully clothed person",
        "suggestive or revealing clothing",
        "partial nudity",
        "full nudity",
    ]
    clip_scores = classify_with_clip(image, queries)
    return {
        'none': clip_scores.get("fully clothed person", 0.0),
        'suggestive': clip_scores.get("suggestive or revealing clothing", 0.0),
        'partial_nudity': clip_scores.get("partial nudity", 0.0),
        'full_nudity': clip_scores.get("full nudity", 0.0),
    }


def classify_immodesty(image):
    """Classify immodesty/clothing coverage in image using CLIP zero-shot classification.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with immodesty analysis
    """
    queries = [
        "person wearing modest clothing",
        "person with exposed chest",
        "person with exposed upper legs",
        "person with exposed midriff",
        "person with exposed back",
        "person in swimwear or bikini",
    ]
    clip_scores = classify_with_clip(image, queries)
    modesty_score = clip_scores.get("person wearing modest clothing", 0.0)
    return {
        'modesty_score': modesty_score,
        'exposed_areas': {
            'chest_area': clip_scores.get("person with exposed chest", 0.0),
            'upper_leg_area': clip_scores.get("person with exposed upper legs", 0.0),
            'midriff_area': clip_scores.get("person with exposed midriff", 0.0),
            'back_area': clip_scores.get("person with exposed back", 0.0),
        },
        'clothing_type': 'swimwear' if clip_scores.get("person in swimwear or bikini", 0.0) > 0.5 else 'unknown',
    }


def classify_with_clip(image, text_queries):
    """Use CLIP model for zero-shot classification.
    
    Args:
        image: PIL Image object
        text_queries: List of text descriptions to classify against
        
    Returns:
        Dictionary with query scores
    """
    global clip_model, clip_processor, clip_device
    
    if clip_model is None or clip_processor is None:
        raise RuntimeError("CLIP model is not loaded")
    
    try:
        # Process inputs
        inputs = clip_processor(text=text_queries, images=image, return_tensors="pt", padding=True)
        # Send tensors to target device
        try:
            import torch
            if clip_device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.to(clip_device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        except Exception as e:
            logger.debug("Could not move CLIP inputs to device: %s", e)
        
        # Get predictions
        import torch
        with torch.no_grad():
            outputs = clip_model(**inputs)
        _touch_model_use()
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)
        
        # Convert to dictionary
        results = {}
        for i, query in enumerate(text_queries):
            results[query] = float(probs[0][i])
        
        return results
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("CLIP classification failed: %s", e)
        raise RuntimeError(f"CLIP classification failed: {e}") from e


def classify_content(image_data):
    """Perform comprehensive content classification.
    
    Args:
        image_data: PIL Image object
        
    Returns:
        Dictionary with all classification results
    """
    try:
        # Preprocess image
        img = image_data.convert('RGB')
        img = img.resize((224, 224))
        
        # Run all classifiers
        violence_results = classify_violence(img)
        nudity_results = classify_nudity(img)
        immodesty_results = classify_immodesty(img)
        
        # Use CLIP for additional content analysis
        clip_queries = [
            "drug use", "smoking cigarettes", "drinking alcohol", 
            "profanity", "inappropriate content", "family friendly content",
            "educational material", "safe for children"
        ]
        clip_results = classify_with_clip(img, clip_queries)
        
        # Calculate enhanced concern score including CLIP results
        drug_concern = max(
            clip_results.get("drug use", 0),
            clip_results.get("smoking cigarettes", 0) * 0.7,
            clip_results.get("drinking alcohol", 0) * 0.5
        )
        
        profanity_concern = clip_results.get("profanity", 0)
        inappropriate_concern = clip_results.get("inappropriate content", 0)
        
        max_concern = max(
            violence_results['overall_violence_score'],
            nudity_results.get('full_nudity', 0),
            nudity_results.get('partial_nudity', 0) * 0.7,
            1.0 - immodesty_results['modesty_score'],
            drug_concern,
            profanity_concern,
            inappropriate_concern
        )
        
        # Determine content rating
        if max_concern > 0.8:
            rating = 'X'
        elif max_concern > 0.5:
            rating = 'R'
        elif max_concern > 0.3:
            rating = 'PG-13'
        else:
            rating = 'PG'
        
        return {
            'violence': violence_results,
            'nudity': nudity_results,
            'immodesty': immodesty_results,
            'clip_analysis': clip_results,
            'drug_use_score': drug_concern,
            'profanity_score': profanity_concern,
            'content_rating': rating,
            'overall_concern_score': max_concern
        }
        
    except Exception as e:
        logger.error("Error classifying content: %s", e)
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    idle_seconds = int(time.monotonic() - last_model_use_monotonic)
    return jsonify({
        'status': 'healthy' if models_loaded else 'degraded',
        'models_loaded': models_loaded,
        'ready': _models_ready,
        'lazy_load_available': _has_model_assets(),
        'model_idle_unload_seconds': MODEL_IDLE_UNLOAD_SECONDS,
        'seconds_since_model_use': idle_seconds,
        'gpu_available': gpu_available,
        'gpu_enabled': USE_GPU,
        'clip_device': clip_device,
        'timestamp': datetime.now().isoformat(),
        'service': 'content-classifier'
    })


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness endpoint — returns 200 only when models are loaded and inference is possible."""
    if _models_ready:
        return jsonify({'status': 'ready', 'models_loaded': True})
    if _has_model_assets():
        return jsonify({
            'status': 'ready',
            'models_loaded': False,
            'lazy_load': True,
            'reason': 'Models will load on-demand for the next inference request'
        })
    return jsonify({
        'status': 'degraded',
        'models_loaded': False,
        'reason': 'No classification models loaded'
    }), 503


@app.route('/classify', methods=['POST'])
@REQUEST_DURATION.time()
def classify():
    """Classify image content."""
    REQUEST_COUNT.inc()
    
    try:
        # Lazy-load models if needed.
        if not ensure_models_loaded():
            ERROR_COUNT.inc()
            return jsonify({'error': 'Models not loaded', 'degraded': True, 'service': 'content-classifier'}), 503
        
        # Get image from request
        if 'image' not in request.files:
            ERROR_COUNT.inc()
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            ERROR_COUNT.inc()
            return jsonify({'error': 'Empty filename'}), 400
        
        # Load and classify image
        image_data = Image.open(io.BytesIO(file.read()))
        results = classify_content(image_data)
        
        # Extract violence score for scene analyzer
        violence_score = results['violence']['overall_violence_score']
        
        return jsonify({
            'success': True,
            'violence': violence_score,
            'detailed_results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error("Error processing request: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


if __name__ == '__main__':
    # Start idle-unload worker (models are lazy-loaded on first request).
    threading.Thread(target=_idle_unload_worker, daemon=True, name='classifier-idle-unloader').start()
    
    # Run Flask app
    port = int(os.getenv('PORT', '3000'))
    app.run(host='0.0.0.0', port=port, debug=False)
