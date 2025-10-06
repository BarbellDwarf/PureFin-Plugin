# Phase 2A: AI Model Integration

## Overview
Integrate and configure AI models for content detection, including NSFW detection, immodesty classification, violence detection, and profanity filtering with proper model management and optimization.

## Prerequisites
- Phase 1B: AI Service Infrastructure completed
- AI services running and accessible
- Model storage directories configured
- Python development environment setup

## Tasks

### Task 1: NSFW and Nudity Detection Models
**Duration**: 4-5 hours
**Priority**: Critical

#### Subtasks:
1. **Integrate NSFW.js Model**
   ```python
   # services/nsfw-detector/models/nsfw_model.py
   import tensorflow as tf
   import numpy as np
   from PIL import Image
   
   class NSFWDetector:
       def __init__(self, model_path):
           self.model = tf.keras.models.load_model(model_path)
           self.classes = ['drawings', 'hentai', 'neutral', 'porn', 'sexy']
   
       def predict(self, image_data):
           # Preprocess image
           img = Image.open(image_data).convert('RGB')
           img = img.resize((224, 224))
           img_array = np.array(img) / 255.0
           img_array = np.expand_dims(img_array, axis=0)
   
           # Make prediction
           predictions = self.model.predict(img_array)[0]
           
           return {
               class_name: float(prediction) 
               for class_name, prediction in zip(self.classes, predictions)
           }
   ```

2. **Custom Nudity Classification Model**
   ```python
   # services/nsfw-detector/models/nudity_classifier.py
   import cv2
   import numpy as np
   from tensorflow import keras
   
   class NudityClassifier:
       def __init__(self, model_path):
           self.model = keras.models.load_model(model_path)
           self.categories = {
               'none': 0,
               'partial_nudity': 1,
               'full_nudity': 2,
               'suggestive': 3
           }
   
       def classify_nudity_level(self, image):
           processed_img = self.preprocess_image(image)
           prediction = self.model.predict(processed_img)
           
           confidence_scores = {}
           for category, index in self.categories.items():
               confidence_scores[category] = float(prediction[0][index])
   
           return confidence_scores
   
       def preprocess_image(self, image):
           # Resize and normalize image
           img = cv2.resize(image, (224, 224))
           img = img.astype('float32') / 255.0
           return np.expand_dims(img, axis=0)
   ```

3. **Model Performance Optimization**
   ```python
   # services/nsfw-detector/models/model_optimizer.py
   class ModelOptimizer:
       @staticmethod
       def optimize_for_inference(model_path, output_path):
           # Convert to TensorFlow Lite for better performance
           converter = tf.lite.TFLiteConverter.from_saved_model(model_path)
           converter.optimizations = [tf.lite.Optimize.DEFAULT]
           tflite_model = converter.convert()
           
           with open(output_path, 'wb') as f:
               f.write(tflite_model)
   
       @staticmethod
       def batch_predict(model, images, batch_size=32):
           results = []
           for i in range(0, len(images), batch_size):
               batch = images[i:i+batch_size]
               batch_results = model.predict(batch)
               results.extend(batch_results)
           return results
   ```

#### Acceptance Criteria:
- [ ] NSFW.js model loads and makes predictions
- [ ] Custom nudity classifier functional
- [ ] Model optimization reduces inference time by >30%
- [ ] Batch processing supports multiple images

### Task 2: Immodesty Detection System
**Duration**: 5-6 hours
**Priority**: Critical

#### Subtasks:
1. **Clothing and Skin Detection**
   ```python
   # services/content-classifier/models/immodesty_detector.py
   import mediapipe as mp
   import cv2
   import numpy as np
   
   class ImmodesttyDetector:
       def __init__(self):
           self.mp_pose = mp.solutions.pose
           self.mp_drawing = mp.solutions.drawing_utils
           self.pose = self.mp_pose.Pose(
               static_image_mode=True,
               model_complexity=2,
               enable_segmentation=True,
               min_detection_confidence=0.5
           )
   
       def detect_exposed_areas(self, image):
           rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
           results = self.pose.process(rgb_image)
           
           exposed_areas = {
               'chest_area': 0.0,
               'upper_leg_area': 0.0,
               'midriff_area': 0.0,
               'back_area': 0.0
           }
   
           if results.pose_landmarks:
               exposed_areas = self.analyze_pose_landmarks(
                   results.pose_landmarks, 
                   results.segmentation_mask,
                   image.shape
               )
   
           return exposed_areas
   
       def analyze_pose_landmarks(self, landmarks, segmentation_mask, image_shape):
           # Analyze body landmarks to detect clothing coverage
           h, w = image_shape[:2]
           
           # Key body points for immodesty detection
           key_points = {
               'left_shoulder': landmarks.landmark[11],
               'right_shoulder': landmarks.landmark[12],
               'left_hip': landmarks.landmark[23],
               'right_hip': landmarks.landmark[24],
               'left_knee': landmarks.landmark[25],
               'right_knee': landmarks.landmark[26]
           }
   
           # Calculate exposure ratios for different body areas
           exposure_analysis = self.calculate_exposure_ratios(
               key_points, segmentation_mask, h, w
           )
   
           return exposure_analysis
   ```

2. **Clothing Type Classification**
   ```python
   # services/content-classifier/models/clothing_classifier.py
   class ClothingClassifier:
       def __init__(self, model_path):
           self.model = tf.keras.models.load_model(model_path)
           self.clothing_types = [
               'conservative', 'casual', 'revealing', 'swimwear', 
               'lingerie', 'athletic_wear', 'formal'
           ]
   
       def classify_clothing(self, image, person_bbox):
           # Extract person region of interest
           person_roi = self.extract_person_roi(image, person_bbox)
           
           # Preprocess for classification
           processed_roi = self.preprocess_clothing_image(person_roi)
           
           # Predict clothing type
           predictions = self.model.predict(processed_roi)
           
           results = {}
           for i, clothing_type in enumerate(self.clothing_types):
               results[clothing_type] = float(predictions[0][i])
   
           return results
   
       def assess_modesty_level(self, clothing_results, exposed_areas):
           # Combine clothing type and exposure analysis
           modesty_score = 1.0  # Start with fully modest
           
           # Adjust based on clothing type
           if clothing_results['revealing'] > 0.5:
               modesty_score -= 0.3
           if clothing_results['swimwear'] > 0.5:
               modesty_score -= 0.4
           if clothing_results['lingerie'] > 0.5:
               modesty_score -= 0.6
   
           # Adjust based on exposed areas
           for area, exposure in exposed_areas.items():
               modesty_score -= exposure * 0.2
   
           return max(0.0, modesty_score)
   ```

3. **Sensitivity Configuration System**
   ```python
   # services/content-classifier/config/sensitivity_config.py
   class SensitivityConfig:
       SENSITIVITY_LEVELS = {
           'strict': {
               'nudity_threshold': 0.1,
               'immodesty_threshold': 0.2,
               'exposed_skin_threshold': 0.15,
               'clothing_strictness': 0.8
           },
           'moderate': {
               'nudity_threshold': 0.3,
               'immodesty_threshold': 0.5,
               'exposed_skin_threshold': 0.4,
               'clothing_strictness': 0.6
           },
           'permissive': {
               'nudity_threshold': 0.7,
               'immodesty_threshold': 0.8,
               'exposed_skin_threshold': 0.7,
               'clothing_strictness': 0.4
           }
       }
   
       @classmethod
       def should_flag_content(cls, analysis_results, sensitivity_level):
           thresholds = cls.SENSITIVITY_LEVELS[sensitivity_level]
           
           # Check nudity
           if analysis_results.get('nudity_score', 0) > thresholds['nudity_threshold']:
               return True, 'nudity'
   
           # Check immodesty
           if analysis_results.get('immodesty_score', 0) > thresholds['immodesty_threshold']:
               return True, 'immodesty'
   
           # Check exposed skin
           total_exposure = sum(analysis_results.get('exposed_areas', {}).values())
           if total_exposure > thresholds['exposed_skin_threshold']:
               return True, 'exposed_skin'
   
           return False, None
   ```

#### Acceptance Criteria:
- [ ] Pose detection identifies body landmarks accurately
- [ ] Clothing classification distinguishes clothing types
- [ ] Exposed area calculation provides quantified metrics
- [ ] Sensitivity levels produce different filtering results

### Task 3: Violence and Adult Content Detection
**Duration**: 3-4 hours
**Priority**: High

#### Subtasks:
1. **Violence Detection Model**
   ```python
   # services/content-classifier/models/violence_detector.py
   import cv2
   import numpy as np
   from tensorflow import keras
   
   class ViolenceDetector:
       def __init__(self, model_path):
           self.model = keras.models.load_model(model_path)
           self.violence_categories = [
               'blood', 'weapons', 'fighting', 'explosions', 
               'death', 'torture', 'general_violence'
           ]
   
       def detect_violence(self, image):
           processed_img = self.preprocess_image(image)
           predictions = self.model.predict(processed_img)
           
           violence_scores = {}
           for i, category in enumerate(self.violence_categories):
               violence_scores[category] = float(predictions[0][i])
   
           # Calculate overall violence score
           overall_score = max(violence_scores.values())
           
           return {
               'overall_violence_score': overall_score,
               'category_scores': violence_scores,
               'primary_violence_type': max(violence_scores, key=violence_scores.get)
           }
   
       def preprocess_image(self, image):
           # Resize and normalize for violence detection
           img = cv2.resize(image, (224, 224))
           img = img.astype('float32') / 255.0
           return np.expand_dims(img, axis=0)
   ```

2. **Adult Content Classification**
   ```python
   # services/content-classifier/models/adult_content_detector.py
   class AdultContentDetector:
       def __init__(self, nsfw_model, nudity_model):
           self.nsfw_model = nsfw_model
           self.nudity_model = nudity_model
   
       def classify_adult_content(self, image):
           # Get NSFW scores
           nsfw_results = self.nsfw_model.predict(image)
           nudity_results = self.nudity_model.classify_nudity_level(image)
   
           # Combine results for comprehensive adult content detection
           adult_score = max(
               nsfw_results.get('porn', 0),
               nsfw_results.get('sexy', 0),
               nudity_results.get('full_nudity', 0),
               nudity_results.get('partial_nudity', 0) * 0.7
           )
   
           return {
               'adult_content_score': adult_score,
               'nsfw_breakdown': nsfw_results,
               'nudity_breakdown': nudity_results,
               'content_rating': self.determine_content_rating(adult_score)
           }
   
       def determine_content_rating(self, adult_score):
           if adult_score > 0.8:
               return 'X'  # Adult only
           elif adult_score > 0.5:
               return 'R'  # Restricted
           elif adult_score > 0.3:
               return 'PG-13'  # Parental guidance
           else:
               return 'PG'  # General audience
   ```

#### Acceptance Criteria:
- [ ] Violence detection identifies different violence types
- [ ] Adult content classification provides content ratings
- [ ] Combined scoring system works accurately
- [ ] Performance meets real-time requirements

### Task 4: Audio Profanity Detection
**Duration**: 3-4 hours
**Priority**: High

#### Subtasks:
1. **Audio Transcription Service**
   ```python
   # services/scene-analyzer/audio/transcription_service.py
   import whisper
   import librosa
   
   class AudioTranscriptionService:
       def __init__(self, model_name='base'):
           self.whisper_model = whisper.load_model(model_name)
   
       def transcribe_audio_segment(self, audio_file, start_time, end_time):
           # Load audio segment
           audio_data, sample_rate = librosa.load(
               audio_file, 
               sr=16000, 
               offset=start_time, 
               duration=end_time - start_time
           )
   
           # Transcribe with timestamps
           result = self.whisper_model.transcribe(
               audio_data, 
               word_timestamps=True
           )
   
           return {
               'text': result['text'],
               'segments': result['segments'],
               'words': result.get('words', [])
           }
   ```

2. **Profanity Detection System**
   ```python
   # services/content-classifier/audio/profanity_detector.py
   import re
   from profanity_check import predict as is_profane
   from profanity_check import predict_prob as profanity_prob
   
   class ProfanityDetector:
       def __init__(self):
           # Load profanity word lists for different severity levels
           self.mild_profanity = self.load_word_list('mild_profanity.txt')
           self.strong_profanity = self.load_word_list('strong_profanity.txt')
           self.extreme_profanity = self.load_word_list('extreme_profanity.txt')
   
       def analyze_profanity(self, transcription_data):
           text = transcription_data['text']
           segments = transcription_data['segments']
           
           profanity_events = []
           
           for segment in segments:
               segment_text = segment['text']
               start_time = segment['start']
               end_time = segment['end']
   
               # Check for profanity
               if is_profane(segment_text):
                   profanity_score = profanity_prob(segment_text)
                   severity = self.determine_profanity_severity(segment_text)
   
                   profanity_events.append({
                       'start_time': start_time,
                       'end_time': end_time,
                       'text': segment_text,
                       'profanity_score': profanity_score,
                       'severity': severity,
                       'type': 'profanity'
                   })
   
           return profanity_events
   
       def determine_profanity_severity(self, text):
           text_lower = text.lower()
           
           if any(word in text_lower for word in self.extreme_profanity):
               return 'extreme'
           elif any(word in text_lower for word in self.strong_profanity):
               return 'strong'
           elif any(word in text_lower for word in self.mild_profanity):
               return 'mild'
           else:
               return 'none'
   ```

#### Acceptance Criteria:
- [ ] Audio transcription produces accurate text with timestamps
- [ ] Profanity detection identifies different severity levels
- [ ] Timing information aligns with audio segments
- [ ] Performance suitable for batch processing

## Deliverables

### Model Integration Deliverables:
1. **NSFW Detection Service** - Comprehensive nudity and adult content detection
2. **Immodesty Classification System** - Clothing and exposure analysis
3. **Violence Detection Module** - Multi-category violence classification  
4. **Audio Profanity Detector** - Speech-to-text profanity identification

### Configuration Deliverables:
1. **Sensitivity Configuration** - User-adjustable filtering thresholds
2. **Model Management System** - Automated model loading and optimization
3. **Performance Monitoring** - Model inference performance tracking
4. **API Documentation** - Complete endpoint specifications

## Verification Steps

### Model Accuracy Testing:
1. Test with known positive/negative samples
2. Validate sensitivity threshold behavior  
3. Benchmark performance against target metrics
4. Cross-validate with human annotation data

### Integration Testing:
1. Verify all models load successfully
2. Test API endpoints respond correctly
3. Validate output format consistency
4. Confirm resource usage within limits

## Performance Targets

### Accuracy Requirements:
- NSFW Detection: >90% precision, >85% recall
- Immodesty Classification: >80% accuracy across clothing types
- Violence Detection: >85% accuracy for obvious violence
- Profanity Detection: >95% accuracy for common profanity

### Performance Requirements:
- Image Analysis: <2 seconds per frame
- Audio Transcription: <1x real-time processing
- Model Loading: <30 seconds on service start
- Memory Usage: <6GB total across all models

## Next Phase Dependencies

This phase enables:
- Phase 2B: Content Detection Pipeline
- Phase 2C: Scene Analysis Workflow  
- Phase 3A: Plugin Core Development

## Success Metrics
- [ ] All AI models integrated and functional
- [ ] Accuracy targets met for each content type
- [ ] Performance requirements satisfied
- [ ] Sensitivity configuration working
- [ ] API documentation complete

## Resources
- [TensorFlow Model Optimization](https://www.tensorflow.org/model_optimization)
- [MediaPipe Pose Detection](https://google.github.io/mediapipe/solutions/pose.html)
- [Whisper Audio Transcription](https://github.com/openai/whisper)