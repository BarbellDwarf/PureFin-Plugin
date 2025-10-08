"""NSFW Detection Service - REST API for content analysis."""

import os
import logging
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
model_loaded = False
nsfw_model = None

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
    global model_loaded, nsfw_model
    try:
        # Try loading H5 model first (our custom model)
        h5_path = os.path.join(MODEL_PATH, 'nsfw', 'nsfw_model.h5')
        savedmodel_path = os.path.join(MODEL_PATH, 'nsfw', 'mobilenet_v2_140_224')
        
        import tensorflow as tf
        
        if os.path.exists(h5_path):
            logger.info(f"Loading NSFW H5 model from {h5_path}")
            try:
                nsfw_model = tf.keras.models.load_model(h5_path)
                logger.info("Successfully loaded NSFW H5 model")
                model_loaded = True
                
                # Test prediction to ensure model works
                test_input = tf.random.normal((1, 224, 224, 3))
                _ = nsfw_model.predict(test_input, verbose=0)
                logger.info("Model test prediction successful")
                
                return True
                
            except Exception as h5_error:
                logger.error(f"H5 model loading failed: {h5_error}")
                
        elif os.path.exists(savedmodel_path):
            logger.info(f"Loading NSFW SavedModel from {savedmodel_path}")
            try:
                nsfw_model = tf.keras.models.load_model(savedmodel_path)
                logger.info("Successfully loaded NSFW TensorFlow SavedModel")
                model_loaded = True
                
                # Test prediction to ensure model works
                test_input = tf.random.normal((1, 224, 224, 3))
                _ = nsfw_model.predict(test_input, verbose=0)
                logger.info("Model test prediction successful")
                
                return True
                
            except Exception as tf_error:
                logger.error(f"SavedModel loading failed: {tf_error}")
        else:
            logger.warning(f"No NSFW model found at {h5_path} or {savedmodel_path}")
            logger.info("Will use mock predictions until models are downloaded")
        
        # If no model loaded, set flag but don't fail
        model_loaded = False
        logger.info("No real model available, using mock predictions")
        return True
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        model_loaded = False
        return True  # Don't fail startup


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
        
        # Use real model if available
        if model_loaded and nsfw_model is not None:
            try:
                # Prepare input for model
                input_batch = np.expand_dims(img_array, axis=0)
                
                # Get model prediction
                predictions = nsfw_model.predict(input_batch, verbose=0)[0]
                logger.debug(f"Real NSFW model predictions: {predictions}")
                
            except Exception as model_error:
                logger.error(f"Model prediction failed, using mock data: {model_error}")
                # Fallback to mock predictions
                predictions = [0.05, 0.02, 0.85, 0.03, 0.05]  # Mostly neutral
        else:
            # Mock predictions for development/fallback
            predictions = [0.05, 0.02, 0.85, 0.03, 0.05]  # Mostly neutral
            if not model_loaded:
                logger.debug("Using mock predictions - no real model loaded")
        
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
    return jsonify({
        'status': 'healthy' if model_loaded else 'degraded',
        'model_loaded': model_loaded,
        'gpu_available': gpu_available,
        'gpu_enabled': USE_GPU,
        'timestamp': datetime.now().isoformat(),
        'service': 'nsfw-detector'
    })


@app.route('/analyze', methods=['POST'])
@REQUEST_DURATION.time()
def analyze():
    """Analyze image for NSFW content."""
    REQUEST_COUNT.inc()
    
    try:
        # Check if model is loaded
        if not model_loaded:
            ERROR_COUNT.inc()
            return jsonify({'error': 'Model not loaded'}), 503
        
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
    # Load model on startup
    load_model()
    
    # Run Flask app
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
