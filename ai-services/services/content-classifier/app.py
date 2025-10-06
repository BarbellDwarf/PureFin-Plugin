"""Content Classifier Service - Multi-category content classification."""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import numpy as np
from PIL import Image
import io
import cv2

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
models_loaded = False

# Content categories
VIOLENCE_CATEGORIES = ['blood', 'weapons', 'fighting', 'explosions', 'death', 'torture', 'general_violence']
NUDITY_CATEGORIES = ['none', 'partial_nudity', 'full_nudity', 'suggestive']


def load_models():
    """Load classification models."""
    global models_loaded
    try:
        # In production, load actual models
        logger.info(f"Models loading simulated from {MODEL_PATH}")
        models_loaded = True
        return True
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        return False


def classify_violence(image):
    """Classify violence content in image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with violence scores
    """
    # Mock predictions for development
    scores = {
        'blood': 0.02,
        'weapons': 0.01,
        'fighting': 0.03,
        'explosions': 0.01,
        'death': 0.00,
        'torture': 0.00,
        'general_violence': 0.05
    }
    
    overall_score = max(scores.values())
    primary_type = max(scores, key=scores.get)
    
    return {
        'overall_violence_score': overall_score,
        'category_scores': scores,
        'primary_violence_type': primary_type
    }


def classify_nudity(image):
    """Classify nudity levels in image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with nudity scores
    """
    # Mock predictions for development
    scores = {
        'none': 0.85,
        'partial_nudity': 0.10,
        'full_nudity': 0.03,
        'suggestive': 0.02
    }
    
    return scores


def classify_immodesty(image):
    """Classify immodesty/clothing coverage in image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with immodesty analysis
    """
    # Mock analysis for development
    return {
        'modesty_score': 0.85,
        'exposed_areas': {
            'chest_area': 0.05,
            'upper_leg_area': 0.10,
            'midriff_area': 0.02,
            'back_area': 0.03
        },
        'clothing_type': 'casual'
    }


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
        
        # Determine overall content rating
        max_concern = max(
            violence_results['overall_violence_score'],
            nudity_results.get('full_nudity', 0),
            nudity_results.get('partial_nudity', 0) * 0.7,
            1.0 - immodesty_results['modesty_score']
        )
        
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
            'content_rating': rating,
            'overall_concern_score': max_concern
        }
        
    except Exception as e:
        logger.error(f"Error classifying content: {e}")
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy' if models_loaded else 'degraded',
        'models_loaded': models_loaded,
        'timestamp': datetime.now().isoformat(),
        'service': 'content-classifier'
    })


@app.route('/classify', methods=['POST'])
@REQUEST_DURATION.time()
def classify():
    """Classify image content."""
    REQUEST_COUNT.inc()
    
    try:
        # Check if models are loaded
        if not models_loaded:
            ERROR_COUNT.inc()
            return jsonify({'error': 'Models not loaded'}), 503
        
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
    # Load models on startup
    load_models()
    
    # Run Flask app
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
