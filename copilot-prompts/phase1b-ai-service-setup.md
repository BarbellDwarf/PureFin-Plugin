# Phase 1B: AI Service Infrastructure Setup

## Overview
Establish the containerized AI service infrastructure for content analysis, including model deployment, API services, and integration with media processing tools.

## Prerequisites
- Docker Desktop installed and running
- Minimum 16GB RAM (32GB recommended for GPU acceleration)
- 100GB+ free disk space for models and processing
- NVIDIA GPU (optional but recommended for performance)

## Tasks

### Task 1: Container Architecture Setup
**Duration**: 2-3 hours
**Priority**: Critical

#### Subtasks:
1. **Create Docker Compose Configuration**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   services:
     nsfw-detector:
       build: ./services/nsfw-detector
       ports:
         - "3001:3000"
       volumes:
         - ./models:/app/models
         - ./temp:/tmp/processing
       environment:
         - MODEL_PATH=/app/models
         - PROCESSING_DIR=/tmp/processing
   
     scene-analyzer:
       build: ./services/scene-analyzer
       ports:
         - "3002:3000"
       volumes:
         - /path/to/jellyfin/media:/media:ro
         - ./temp:/tmp/processing
       depends_on:
         - nsfw-detector
   
     content-classifier:
       build: ./services/content-classifier
       ports:
         - "3003:3000"
       volumes:
         - ./models:/app/models
         - ./temp:/tmp/processing
   ```

2. **Setup Service Directory Structure**
   ```
   ai-services/
   ├── docker-compose.yml
   ├── models/
   ├── temp/
   ├── services/
   │   ├── nsfw-detector/
   │   ├── scene-analyzer/
   │   └── content-classifier/
   └── scripts/
   ```

3. **Configure Network and Volumes**
   - Create dedicated Docker network for services
   - Set up shared volumes for model storage
   - Configure temporary processing directories

#### Acceptance Criteria:
- [ ] Docker Compose file validates successfully
- [ ] Service directory structure created
- [ ] Networks and volumes properly configured
- [ ] Services can communicate internally

### Task 2: NSFW Detection Service
**Duration**: 3-4 hours
**Priority**: Critical

#### Subtasks:
1. **Create NSFW Detection Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   RUN apt-get update && apt-get install -y \
       libgl1-mesa-glx \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender-dev \
       libgomp1
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   EXPOSE 3000
   CMD ["python", "app.py"]
   ```

2. **Implement NSFW Detection API**
   ```python
   # services/nsfw-detector/app.py
   from flask import Flask, request, jsonify
   import tensorflow as tf
   from PIL import Image
   import numpy as np
   
   app = Flask(__name__)
   model = None
   
   def load_model():
       global model
       # Load NSFW.js model or equivalent
       model = tf.keras.models.load_model('/app/models/nsfw_model')
   
   @app.route('/analyze', methods=['POST'])
   def analyze_image():
       # Implementation for image analysis
       pass
   ```

3. **Download and Configure Models**
   - NSFW.js TensorFlow model
   - Custom nudity detection models
   - Immodesty classification models

4. **Create Model Management Scripts**
   ```bash
   #!/bin/bash
   # scripts/download_models.sh
   mkdir -p models
   cd models
   
   # Download NSFW.js model
   wget https://github.com/infinitered/nsfwjs/releases/download/v2.4.2/mobilenet_v2_140_224.tar.gz
   tar -xzf mobilenet_v2_140_224.tar.gz
   
   # Download additional models as needed
   ```

#### Acceptance Criteria:
- [ ] NSFW detection service builds successfully
- [ ] API responds to health checks
- [ ] Models load without errors
- [ ] Basic image analysis functional

### Task 3: Scene Analysis Service
**Duration**: 3-4 hours
**Priority**: Critical

#### Subtasks:
1. **Setup FFmpeg Integration**
   ```dockerfile
   FROM python:3.9-slim
   
   RUN apt-get update && apt-get install -y \
       ffmpeg \
       libavcodec-dev \
       libavformat-dev \
       libswscale-dev
   
   # Copy application files
   # Install Python dependencies
   ```

2. **Implement Scene Detection API**
   ```python
   # services/scene-analyzer/app.py
   import ffmpeg
   from flask import Flask, request, jsonify
   
   app = Flask(__name__)
   
   @app.route('/analyze', methods=['POST'])
   def analyze_video():
       video_path = request.json['video_path']
       
       # Extract scenes using FFmpeg
       scenes = extract_scenes(video_path)
       
       # Analyze each scene for content
       results = []
       for scene in scenes:
           frame = extract_frame(video_path, scene['timestamp'])
           analysis = analyze_frame(frame)
           results.append({
               'timestamp': scene['timestamp'],
               'duration': scene['duration'],
               'analysis': analysis
           })
       
       return jsonify(results)
   ```

3. **Scene Detection Algorithm**
   ```python
   def extract_scenes(video_path, threshold=0.3):
       probe = ffmpeg.probe(video_path)
       duration = float(probe['streams'][0]['duration'])
       
       # Use FFmpeg scene detection
       scenes = []
       # Implementation for scene boundary detection
       
       return scenes
   ```

#### Acceptance Criteria:
- [ ] Scene analysis service builds and runs
- [ ] FFmpeg integration functional
- [ ] Scene detection algorithm works
- [ ] API returns structured results

### Task 4: Content Classification Service
**Duration**: 2-3 hours
**Priority**: High

#### Subtasks:
1. **Multi-Model Classification Setup**
   ```python
   # services/content-classifier/app.py
   class ContentClassifier:
       def __init__(self):
           self.nudity_model = load_nudity_model()
           self.violence_model = load_violence_model()
           self.immodesty_model = load_immodesty_model()
   
       def classify_content(self, image):
           results = {
               'nudity': self.nudity_model.predict(image),
               'violence': self.violence_model.predict(image),
               'immodesty': self.immodesty_model.predict(image)
           }
           return results
   ```

2. **Implement Classification Categories**
   - Nudity levels (none, partial, full)
   - Immodesty categories (revealing clothing, swimwear, etc.)
   - Violence detection (blood, weapons, fighting)
   - Adult content classification

3. **Configure Thresholds and Sensitivity**
   ```python
   CLASSIFICATION_THRESHOLDS = {
       'nudity': {
           'strict': 0.1,
           'moderate': 0.3,
           'permissive': 0.7
       },
       'immodesty': {
           'strict': 0.2,
           'moderate': 0.5,
           'permissive': 0.8
       }
   }
   ```

#### Acceptance Criteria:
- [ ] Content classifier service operational
- [ ] Multiple content categories supported
- [ ] Configurable sensitivity thresholds
- [ ] Structured classification output

### Task 5: Service Orchestration and Testing
**Duration**: 2-3 hours
**Priority**: High

#### Subtasks:
1. **Create Service Health Checks**
   ```python
   @app.route('/health')
   def health_check():
       return jsonify({
           'status': 'healthy',
           'model_loaded': model is not None,
           'timestamp': datetime.now().isoformat()
       })
   ```

2. **Implement Service Discovery**
   - Configure service endpoints
   - Set up load balancing if needed
   - Create service registry mechanism

3. **Create Integration Tests**
   ```python
   # tests/test_integration.py
   def test_full_pipeline():
       # Test video -> scenes -> classification -> results
       pass
   
   def test_service_communication():
       # Test inter-service API calls
       pass
   ```

4. **Performance Monitoring Setup**
   - Add logging and metrics collection
   - Configure performance monitoring
   - Set up alert thresholds

#### Acceptance Criteria:
- [ ] All services start and communicate
- [ ] Health checks return positive status
- [ ] Integration tests pass
- [ ] Performance metrics collected

## Deliverables

### Infrastructure Deliverables:
1. **Docker Compose Configuration** - Multi-service orchestration
2. **Service Dockerfiles** - Containerized AI services
3. **Model Management Scripts** - Automated model download/setup
4. **API Documentation** - Service endpoint specifications

### Code Deliverables:
1. **NSFW Detection Service** - Image content analysis API
2. **Scene Analysis Service** - Video processing and scene detection
3. **Content Classification Service** - Multi-category content analysis
4. **Health Check and Monitoring** - Service status and performance tracking

## Verification Steps

### Manual Testing:
1. Start all services with `docker-compose up`
2. Verify health endpoints respond correctly
3. Test basic image analysis functionality
4. Confirm inter-service communication

### Automated Testing:
1. Run integration test suite
2. Performance benchmark tests
3. Load testing for concurrent requests

## Performance Targets

### Response Times:
- Image analysis: < 2 seconds per frame
- Scene detection: < 0.5x real-time for video processing
- Health checks: < 100ms response

### Resource Usage:
- Memory: < 4GB per service under normal load
- CPU: < 80% utilization during processing
- Disk I/O: Efficient caching to minimize reads

## Troubleshooting

### Common Issues:
1. **Model Loading Failures**
   - Check model file paths and permissions
   - Verify model format compatibility
   - Ensure sufficient memory allocation

2. **Service Communication Errors**
   - Verify Docker network configuration
   - Check port availability and conflicts
   - Review firewall settings

3. **Performance Issues**
   - Monitor resource usage and bottlenecks
   - Optimize model inference settings
   - Consider GPU acceleration setup

## Next Phase Dependencies

This phase enables:
- Phase 2A: AI Model Integration
- Phase 2B: Content Detection Pipeline
- Phase 3A: Plugin Core Development

## Success Metrics
- [ ] All AI services operational and accessible
- [ ] Model inference functional for test content
- [ ] Service health monitoring active
- [ ] Integration with media processing confirmed
- [ ] Performance meets target thresholds

## Resources
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [TensorFlow Serving Guide](https://www.tensorflow.org/tfx/guide/serving)
- [FFmpeg Python Documentation](https://github.com/kkroening/ffmpeg-python)