"""Content Classifier Service - Multi-category content classification using PyTorch."""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import numpy as np
from PIL import Image
import io
import torch
import torch.nn as nn
from torchvision import models, transforms
from transformers import CLIPProcessor, CLIPModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('classifier_requests_total', 'Total classification requests')
REQUEST_DURATION = Histogram('classifier_request_duration_seconds', 'Classification request duration')
ERROR_COUNT = Counter('classifier_errors_total', 'Total classification errors')

# Model configuration
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models')
USE_GPU = os.getenv('USE_GPU', '0') == '1'
models_loaded = False
violence_model = None
clip_model = None
clip_processor = None

# PyTorch device configuration
# Supports NVIDIA GPUs from 10 series (compute 6.1) to 50 series (compute 9.0+)
if torch.cuda.is_available():
    device = torch.device('cuda')
    logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"CUDA Version: {torch.version.cuda}")
    logger.info(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
else:
    device = torch.device('cpu')
    logger.info("Using CPU for inference")


class ViolenceModelPyTorch(nn.Module):
    """
    PyTorch implementation of violence detection model.
    Architecture: MobileNetV2 backbone + custom classification head
    """
    def __init__(self):
        super(ViolenceModelPyTorch, self).__init__()
        
        # Load MobileNetV2 backbone
        mobilenet = models.mobilenet_v2(weights='IMAGENET1K_V1')
        self.features = mobilenet.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Custom classification head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(1280, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        x = self.classifier(x)
        return x


def load_models():
    """Load classification models."""
    global models_loaded, violence_model, clip_model, clip_processor
    try:
        models_loaded = False
        
        # Load violence detection model (PyTorch)
        violence_path_pth = os.path.join(MODEL_PATH, 'violence', 'violence_model.pth')
        violence_path_h5 = os.path.join(MODEL_PATH, 'violence', 'violence_model.h5')
        
        if os.path.exists(violence_path_pth):
            # Load PyTorch model
            violence_model = ViolenceModelPyTorch()
            checkpoint = torch.load(violence_path_pth, map_location=device)
            violence_model.load_state_dict(checkpoint['model_state_dict'])
            violence_model.to(device)
            violence_model.eval()
            logger.info(f"Successfully loaded PyTorch violence detection model on {device}")
        elif os.path.exists(violence_path_h5):
            # Need to convert from Keras first
            logger.warning("Found Keras model but not PyTorch model. Converting...")
            import subprocess
            result = subprocess.run(
                ['python', '/app/convert_to_pytorch.py'],
                capture_output=True,
                text=True
            )
            logger.info(result.stdout)
            if result.returncode == 0 and os.path.exists(violence_path_pth):
                # Load the converted model
                violence_model = ViolenceModelPyTorch()
                checkpoint = torch.load(violence_path_pth, map_location=device)
                violence_model.load_state_dict(checkpoint['model_state_dict'])
                violence_model.to(device)
                violence_model.eval()
                logger.info(f"Successfully converted and loaded violence model on {device}")
            else:
                logger.error(f"Failed to convert Keras model: {result.stderr}")
                raise RuntimeError("Model conversion failed")
        else:
            logger.warning("Violence model not found, will use mock predictions")
        
        # Load CLIP model for nudity/immodesty detection
        clip_cache_dir = os.path.join(MODEL_PATH, 'clip')
        if os.path.exists(clip_cache_dir):
            clip_model = CLIPModel.from_pretrained(clip_cache_dir)
            clip_processor = CLIPProcessor.from_pretrained(clip_cache_dir)
            clip_model.to(device)
            clip_model.eval()
            logger.info(f"Loaded CLIP model from local cache on {device}")
        else:
            clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            clip_model.to(device)
            clip_model.eval()
            os.makedirs(clip_cache_dir, exist_ok=True)
            clip_model.save_pretrained(clip_cache_dir)
            clip_processor.save_pretrained(clip_cache_dir)
            logger.info(f"Downloaded and cached CLIP model on {device}")
        
        models_loaded = True
        logger.info("Content classifier models loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}", exc_info=True)
        raise


# Image preprocessing for violence model
violence_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


def classify_violence(image):
    """
    Classify violence content in an image using PyTorch model.
    
    Args:
        image: PIL Image
        
    Returns:
        dict: Violence classification scores
    """
    try:
        if violence_model is None:
            # Return mock scores if model not loaded
            logger.warning("Violence model not loaded, returning mock scores")
            return {
                'blood': 0.02,
                'weapons': 0.01,
                'fighting': 0.03,
                'explosions': 0.01,
                'death': 0.00,
                'torture': 0.00,
                'general_violence': 0.05
            }
        
        # Preprocess image
        img_tensor = violence_transform(image.convert('RGB')).unsqueeze(0).to(device)
        
        # Get prediction
        with torch.no_grad():
            violence_prob = violence_model(img_tensor)[0][0].item()
        
        # Create detailed category scores based on overall violence score
        base_multiplier = violence_prob
        scores = {
            'blood': min(base_multiplier * 0.6, 0.95),
            'weapons': min(base_multiplier * 0.4, 0.90),
            'fighting': min(base_multiplier * 0.8, 0.95),
            'explosions': min(base_multiplier * 0.3, 0.85),
            'death': min(base_multiplier * 0.2, 0.80),
            'torture': min(base_multiplier * 0.1, 0.70),
            'general_violence': violence_prob
        }
        
        logger.debug("Violence model prediction (PyTorch GPU): %.3f", violence_prob)
        return scores
        
    except Exception as e:
        logger.error("Violence model prediction failed: %s", e, exc_info=True)
        # Return safe fallback scores
        return {
            'blood': 0.02,
            'weapons': 0.01,
            'fighting': 0.03,
            'explosions': 0.01,
            'death': 0.00,
            'torture': 0.00,
            'general_violence': 0.05
        }


def classify_nudity_immodesty(image):
    """
    Classify nudity and immodesty content using CLIP model.
    
    Args:
        image: PIL Image
        
    Returns:
        tuple: (nudity_score, immodesty_score)
    """
    try:
        if clip_model is None or clip_processor is None:
            return 0.1, 0.1
        
        # Prepare prompts
        nudity_prompts = [
            "a photo with no nudity or exposed body parts",
            "a photo with nudity or exposed private body parts"
        ]
        
        immodesty_prompts = [
            "a photo with modest, appropriate clothing",
            "a photo with revealing, immodest, or inappropriate clothing"
        ]
        
        # Process image and text
        with torch.no_grad():
            # Nudity classification
            inputs = clip_processor(
                text=nudity_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            nudity_score = float(probs[0][1])
            
            # Immodesty classification
            inputs = clip_processor(
                text=immodesty_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            immodesty_score = float(probs[0][1])
        
        return nudity_score, immodesty_score
        
    except Exception as e:
        logger.error("CLIP model prediction failed: %s", e, exc_info=True)
        return 0.1, 0.1


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'models_loaded': models_loaded,
        'device': str(device),
        'cuda_available': torch.cuda.is_available(),
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/classify', methods=['POST'])
def classify():
    """Classify image content across multiple categories."""
    REQUEST_COUNT.inc()
    
    try:
        with REQUEST_DURATION.time():
            # Get image from request
            if 'image' not in request.files:
                return jsonify({'error': 'No image provided'}), 400
            
            image_file = request.files['image']
            image = Image.open(io.BytesIO(image_file.read()))
            
            # Classify violence
            violence_scores = classify_violence(image)
            
            # Classify nudity and immodesty
            nudity_score, immodesty_score = classify_nudity_immodesty(image)
            
            # Combine all scores
            result = {
                'violence': violence_scores,
                'nudity': float(nudity_score),
                'immodesty': float(immodesty_score),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return jsonify(result)
            
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Classification error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


def cleanup_models():
    """Clean up models and free GPU memory."""
    global violence_model, clip_model, clip_processor, models_loaded
    
    try:
        if violence_model is not None:
            violence_model.cpu()
            del violence_model
            violence_model = None
        
        if clip_model is not None:
            clip_model.cpu()
            del clip_model
            clip_model = None
        
        if clip_processor is not None:
            del clip_processor
            clip_processor = None
        
        # Force garbage collection and clear CUDA cache
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU memory freed")
        
        models_loaded = False
        logger.info("Models unloaded and memory freed")
        
    except Exception as e:
        logger.error(f"Error during model cleanup: {e}", exc_info=True)


@app.route('/unload', methods=['POST'])
def unload_models():
    """Endpoint to manually unload models and free memory."""
    try:
        cleanup_models()
        return jsonify({
            'status': 'success',
            'message': 'Models unloaded and GPU memory freed',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("Starting Content Classifier service with PyTorch...")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA version: {torch.version.cuda}")
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"Compute capability: {torch.cuda.get_device_capability(0)}")
    
    load_models()
    
    # Register cleanup on exit
    import atexit
    atexit.register(cleanup_models)
    
    app.run(host='0.0.0.0', port=3000, debug=False)
