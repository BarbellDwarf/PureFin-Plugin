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
model_loaded = False

# NSFW categories
CATEGORIES = ['drawings', 'hentai', 'neutral', 'porn', 'sexy']


def load_model():
    """Load NSFW detection model."""
    global model_loaded
    try:
        # In production, load actual TensorFlow model
        # model = tf.keras.models.load_model(os.path.join(MODEL_PATH, 'nsfw_model'))
        logger.info(f"Model loading simulated from {MODEL_PATH}")
        model_loaded = True
        return True
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False


def analyze_image(image_data):
    """Analyze image for NSFW content.
    
    Args:
        image_data: PIL Image object
        
    Returns:
        Dictionary with category scores
    """
    try:
        # Preprocess image
        img = image_data.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img) / 255.0
        
        # In production, use actual model prediction
        # predictions = model.predict(np.expand_dims(img_array, axis=0))[0]
        
        # Mock predictions for development
        predictions = [0.05, 0.02, 0.85, 0.03, 0.05]  # Mostly neutral
        
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
        results = analyze_image(image_data)
        
        return jsonify({
            'success': True,
            'results': results,
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
