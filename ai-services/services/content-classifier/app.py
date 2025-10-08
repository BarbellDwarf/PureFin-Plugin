"""Content Classifier Service - Multi-category content classification."""

import os
import logging
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
models_loaded = False
violence_model = None
clip_model = None
clip_processor = None
clip_device = "cpu"

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
    global models_loaded, violence_model, clip_model, clip_processor
    try:
        models_loaded = False
        
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
                
                logger.info("Violence model loaded successfully (using CPU inference)")
                
            except Exception as e:
                logger.error("Failed to load violence model: %s", e)
                violence_model = None
        else:
            logger.warning("Violence model not found at %s", violence_path)
            violence_model = None
        
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
                global clip_device
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
        
        if models_loaded:
            logger.info("Content classifier models loaded successfully")
        else:
            logger.warning("No real models loaded, will use mock predictions")
        
        return True
        
    except Exception as e:
        logger.error("Error loading models: %s", e)
        models_loaded = False
        return True  # Don't fail startup


def classify_violence(image):
    """Classify violence content in image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary with violence scores
    """
    global violence_model
    
    try:
        # Use real violence model if available
        if violence_model is not None:
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
                
            except Exception as model_error:
                logger.error("Violence model prediction failed: %s", model_error)
                # Fallback to mock predictions
                scores = {
                    'blood': 0.02,
                    'weapons': 0.01,
                    'fighting': 0.03,
                    'explosions': 0.01,
                    'death': 0.00,
                    'torture': 0.00,
                    'general_violence': 0.05
                }
        else:
            # Mock predictions for development/fallback
            scores = {
                'blood': 0.02,
                'weapons': 0.01,
                'fighting': 0.03,
                'explosions': 0.01,
                'death': 0.00,
                'torture': 0.00,
                'general_violence': 0.05
            }
            logger.debug("Using mock violence predictions - no real model loaded")
        
        overall_score = max(scores.values())
        primary_type = max(scores, key=scores.get)
        
        return {
            'overall_violence_score': overall_score,
            'category_scores': scores,
            'primary_violence_type': primary_type
        }
        
    except Exception as e:
        logger.error("Error in violence classification: %s", e)
        # Return safe fallback
        return {
            'overall_violence_score': 0.05,
            'category_scores': {
                'blood': 0.01, 'weapons': 0.01, 'fighting': 0.01,
                'explosions': 0.01, 'death': 0.00, 'torture': 0.00,
                'general_violence': 0.05
            },
            'primary_violence_type': 'general_violence'
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


def classify_with_clip(image, text_queries):
    """Use CLIP model for zero-shot classification.
    
    Args:
        image: PIL Image object
        text_queries: List of text descriptions to classify against
        
    Returns:
        Dictionary with query scores
    """
    global clip_model, clip_processor, clip_device
    
    try:
        if clip_model is not None and clip_processor is not None:
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
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            # Convert to dictionary
            results = {}
            for i, query in enumerate(text_queries):
                results[query] = float(probs[0][i])
            
            return results
        else:
            # Return mock scores if CLIP not available
            return {query: 0.1 for query in text_queries}
            
    except Exception as e:
        logger.error("CLIP classification failed: %s", e)
        return {query: 0.1 for query in text_queries}


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
    return jsonify({
        'status': 'healthy' if models_loaded else 'degraded',
        'models_loaded': models_loaded,
        'gpu_available': gpu_available,
        'gpu_enabled': USE_GPU,
        'clip_device': clip_device,
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
    # Load models on startup
    load_models()
    
    # Run Flask app
    port = int(os.getenv('PORT', '3000'))
    app.run(host='0.0.0.0', port=port, debug=False)
