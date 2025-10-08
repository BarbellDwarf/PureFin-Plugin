# Phase 2D: Implement Real AI Models for Content Detection

## Current Status
✅ Infrastructure is working correctly:
- Plugin loads and runs successfully
- Scene detection finds 1384 scenes (FFmpeg scene detection working)
- AI services respond with 200 OK
- API integration is functional

❌ All AI services are using mock predictions:
- NSFW Detector: Hardcoded `[0.05, 0.02, 0.85, 0.03, 0.05]`
- Content Classifier: Hardcoded mock values
- Violence Detection: Defaulting to 0.050
- Result: No segments created (all scores below thresholds)

## Objective
Replace mock AI predictions with real pre-trained models for violence detection, NSFW/nudity detection, and content classification.

## Implementation Plan

### Step 1: NSFW/Nudity Detection Model
**Model**: Use the open-source NSFW detector model (NudeNet or NSFW_ResNet)
- **Model Source**: https://github.com/GantMan/nsfw_model (Yahoo's open NSFW model)
- **Alternative**: https://github.com/notAI-tech/NudeNet
- **Format**: TensorFlow/Keras SavedModel or H5
- **Categories**: porn, sexy, hentai, neutral, drawings
- **Action Items**:
  1. Add model download script to `ai-services/services/nsfw-detector/`
  2. Download pre-trained weights to `ai-services/models/nsfw/`
  3. Update `app.py` to load and use real model instead of mock predictions
  4. Add model initialization on service startup
  5. Update Dockerfile to include model files

### Step 2: Violence Detection Model
**Model**: Use a violence detection classifier (can use a fine-tuned ResNet50 or Violence Detection Dataset models)
- **Model Source**: 
  - Option 1: Fine-tune ResNet50 on RWF-2000 violence dataset
  - Option 2: Use pre-trained violence detector from Hugging Face
  - Option 3: Use action recognition model (Kinetics-400) and classify violent actions
- **Categories**: violent, fighting, shooting, weapon, neutral
- **Action Items**:
  1. Identify and download suitable violence detection model
  2. Add model to `ai-services/models/violence/`
  3. Create new violence detection service or integrate into content-classifier
  4. Update scene-analyzer to use real violence predictions
  5. Map model outputs to violence scores (0.0-1.0)

### Step 3: Content Classifier (Drug Use, Profanity Detection)
**Approach**: Use multi-label image classification + audio analysis
- **Visual Content**: Use CLIP or similar for general content classification
- **Text/Profanity**: If available, use audio transcription + profanity filter
- **Model Source**: 
  - CLIP from OpenAI: https://github.com/openai/CLIP
  - For audio: Whisper for transcription + profanity filter
- **Action Items**:
  1. Implement CLIP-based content classification
  2. Add semantic search for drug paraphernalia, inappropriate content
  3. Optional: Add audio transcription for profanity detection
  4. Update content-classifier service with real model

### Step 4: Model Download and Setup Scripts
**Create automated setup process**:
- **Script**: `ai-services/scripts/download-models.py`
  - Downloads all required models
  - Verifies checksums
  - Extracts to correct directories
  - Validates model loading
- **Docker Integration**: Update docker-compose to run download on first start
- **Documentation**: Update README with model sources and licenses

### Step 5: Optimize Performance
**GPU Acceleration**:
- Ensure TensorFlow GPU support is enabled
- Batch process frames when possible
- Use GPU for frame extraction (NVDEC) where applicable
- Add model warmup on service startup

**Efficiency Improvements**:
- Reduce sample count for scenes (currently 3 samples per scene)
- Implement adaptive sampling (more samples for suspicious content)
- Add result caching for similar frames
- Use lower resolution for initial screening (224x224)

### Step 6: Testing and Validation
**Test with Real Content**:
- Run on John Wick (expected: high violence scores)
- Run on Mean Girls (expected: low scores)
- Run on action movies (expected: moderate-high violence)
- Verify segment files are created with realistic scores
- Check that segments have correct timestamps

**Performance Benchmarks**:
- Measure processing time per video
- Monitor GPU utilization
- Verify accuracy of detections
- Test different video lengths

## Detailed Implementation Steps

### Phase A: NSFW Detector (Highest Priority)
```bash
# 1. Download Yahoo NSFW Model
cd ai-services/models
mkdir -p nsfw
cd nsfw
wget https://github.com/GantMan/nsfw_model/releases/download/1.2.0/mobilenet_v2_140_224.zip
unzip mobilenet_v2_140_224.zip
```

**Update nsfw-detector/app.py**:
- Load TensorFlow model from `/app/models/nsfw/`
- Replace mock predictions with `model.predict()`
- Add preprocessing pipeline (resize to 224x224, normalize)
- Add error handling for model loading failures

### Phase B: Violence Detection
**Option 1: Use Action Recognition Model**
```bash
# Download I3D or SlowFast model pre-trained on Kinetics-400
# Models available from: https://github.com/facebookresearch/SlowFast
```

**Option 2: Fine-tune ResNet50**
```python
# Use transfer learning with violence detection datasets:
# - RWF-2000: Real-world fights
# - Hockey Fight Dataset
# - Movies Fight Detection Dataset
```

### Phase C: Content Classifier
**CLIP Integration**:
```bash
# Install CLIP
pip install git+https://github.com/openai/CLIP.git

# Download CLIP model (will auto-download on first use)
# ViT-B/32 is good balance of speed/accuracy
```

**Update content-classifier/app.py**:
- Load CLIP model
- Use text prompts for classification:
  - "drug use", "smoking", "drinking alcohol"
  - "profanity", "inappropriate content"
  - "family friendly", "educational content"
- Return scores based on CLIP similarity

## File Structure After Implementation
```
ai-services/
├── models/
│   ├── nsfw/
│   │   ├── mobilenet_v2_140_224/
│   │   └── README.md
│   ├── violence/
│   │   ├── violence_detector.h5
│   │   └── README.md
│   └── content/
│       ├── clip-vit-b-32/
│       └── README.md
├── scripts/
│   ├── download-models.py
│   ├── test-models.py
│   └── benchmark.py
└── services/
    ├── nsfw-detector/
    │   ├── app.py (updated with real model)
    │   └── requirements.txt (add tensorflow)
    ├── content-classifier/
    │   ├── app.py (updated with CLIP)
    │   └── requirements.txt (add clip)
    └── scene-analyzer/
        └── app.py (already working)
```

## Expected Results After Implementation

### Before (Current - Mock Models):
- Fast & Furious: 1384 scenes, all scores 0.050, **0 segments created**
- John Wick: All scores 0.050, **0 segments created**
- Processing: ~12,000 API calls, all returning mock data

### After (Real Models):
- Fast & Furious: 1384 scenes, varied scores, **~50-100 segments created** for action sequences
- John Wick: **~150-200 segments created** for fight scenes (high violence)
- Processing: Same number of calls but with real AI inference
- Segment files contain actionable timestamp data

## Success Criteria
✅ All three AI services load real models successfully
✅ NSFW detector returns varied scores (not just 0.05)
✅ Violence detection identifies fight scenes in John Wick
✅ Content classifier returns meaningful category predictions
✅ Segment files are created with scores above threshold (>0.4)
✅ Processing completes within reasonable time (<5 min per video)
✅ GPU utilization is >0% during analysis

## Resources and References
- Yahoo NSFW Model: https://github.com/GantMan/nsfw_model
- NudeNet: https://github.com/notAI-tech/NudeNet
- CLIP: https://github.com/openai/CLIP
- SlowFast (Violence): https://github.com/facebookresearch/SlowFast
- RWF-2000 Dataset: http://cvlab.hanyang.ac.kr/rwf-2000/
- TensorFlow Model Zoo: https://github.com/tensorflow/models

## Implementation Timeline
1. **Hour 1**: Download and setup NSFW model (Phase A)
2. **Hour 2**: Integrate NSFW model into service and test
3. **Hour 3**: Setup violence detection model (Phase B)
4. **Hour 4**: Integrate violence detection and test
5. **Hour 5**: Setup CLIP for content classification (Phase C)
6. **Hour 6**: End-to-end testing and optimization

## Next Steps
Execute this plan step by step, starting with the NSFW detector as it has the most mature open-source models available.
