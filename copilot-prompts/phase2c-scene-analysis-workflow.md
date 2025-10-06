# Phase 2C: Scene Analysis Workflow

## Overview
Define the detailed workflow for breaking videos into scenes, classifying each scene for content categories (nudity, immodesty, violence), and generating precise start/end timestamps for playback filtering.

## Objectives
- Robust scene segmentation across codecs and content styles
- High-confidence classification using ensemble models
- Precise timestamps with buffered edges for seamless playback actions

## Workflow Stages

### Stage 1: Ingest & Preprocessing
1. Validate media container and codecs (MP4, MKV, AVI)
2. Normalize framerate and timebase references via ffprobe
3. Generate media fingerprint (hash + duration + bitrate)
4. Extract audio stream map and subtitle tracks

### Stage 2: Scene Boundary Discovery
1. FFmpeg-based scene cut detection with adaptive thresholds
2. Cue point extraction via I-frames to align seeks
3. Temporal smoothing to merge micro-cuts (<2s) into parent scenes
4. Minimum/maximum scene length enforcement (2s/180s)

### Stage 3: Keyframe Sampling & Feature Extraction
1. Sample frames at scene start/mid/end (±5 frames)
2. Extract embeddings using pre-trained CNN/ViT backbones
3. Generate body-pose landmarks and segmentation masks
4. Compute exposed area ratios and clothing-type inference

### Stage 4: Category Classification (Ensemble)
1. Nudity classifier (partial/full/suggestive)
2. Immodesty estimator (exposed areas + clothing type)
3. Violence detector (weapons/blood/fighting)
4. Adult content aggregator (NSFW + nudity fusion)

### Stage 5: Decision & Timestamping
1. Apply sensitivity thresholds per profile (strict/moderate/permissive)
2. Determine action per scene: skip, mute, blur, none
3. Buffer timestamps (lead/trail 300ms) for seamless playback
4. Create segment JSON record with confidence and provenance

### Stage 6: Audio Profanity Overlay
1. Align Whisper word timestamps to scene windows
2. Insert micro-segments for profanity muting (word ±250ms)
3. Merge overlaps and produce consolidated actions

### Stage 7: Output & Storage
1. Write segments to `/segments/<library>/<media_id>.json`
2. Update index and checksum
3. Emit metrics and logs for QA

## Data Structures

### Segment Record
```json
{
  "start": 120.3,
  "end": 141.7,
  "categories": ["immodesty"],
  "scores": {"immodesty": 0.82},
  "action": "skip",
  "buffer": {"lead": 0.3, "trail": 0.3},
  "provenance": {"source": "ai", "models": ["nsfw_v2", "vit_nudity_1.0"]},
  "confidence": 0.78
}
```

### Profanity Micro-Segment
```json
{
  "start": 305.12,
  "end": 306.04,
  "categories": ["profanity"],
  "severity": "strong",
  "action": "mute",
  "provenance": {"source": "stt+lexicon"}
}
```

## Error Handling & Recovery
- Fallback to conservative thresholds when models fail
- Skip scenes with unreadable frames; log warnings
- Retry policy for transient I/O errors
- Circuit breaker on model timeouts; mark segments for later review

## Performance Optimizations
- Batch inference across scenes
- GPU acceleration through CUDA/TensorRT where available
- Frame caching for repeated access
- Early exit when scores below minimal thresholds

## QA & Validation
- Random-sample audits against ground truth
- Per-category ROC curves and threshold tuning
- Drift detection on model outputs across new content
- A/B tests for buffer sizes and user perception of skips

## Deliverables
- End-to-end scene analysis service implementation
- Configurable sensitivity profiles and action mapping
- Segment JSON writer with schema validation
- Metrics dashboard and logs for operations