# Phase 2B: Content Detection Pipeline

## Overview
Design and implement the end-to-end pipeline that turns media files into timestamped segment files for filtering, using AI models, scene detection, and configurable thresholds.

## Prerequisites
- Phase 1B and Phase 2A completed
- AI services deployed and accessible
- Plugin development environment ready

## Pipeline Goals
- Efficient batch processing of library items
- Accurate segment timestamp generation
- Hybrid data merging with community-curated segments
- Configurable sensitivity per category and per user

## Tasks

### Task 1: Scene Boundary Detection
**Duration**: 1-2 days
**Priority**: Critical

#### Subtasks:
1. **FFmpeg Scene Detection**
   ```bash
   ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null - 2> scenes.log
   ```
   - Parse `showinfo` logs to extract scene change timestamps
   - Calibrate threshold (0.3-0.5) per content type [fast cuts vs long takes]

2. **I-Frame Extraction**
   ```bash
   ffprobe -select_streams v:0 -show_frames -show_entries frame=pkt_pts_time,pict_type -of csv input.mp4 | grep I
   ```
   - Use I-frames as candidate points for low-latency seeking during playback

3. **Segment Windowing**
   - Aggregate detected cuts into segment windows (min 2s, max 60s)
   - Expand windows to include leading/trailing buffers for accuracy (±0.5s)

#### Acceptance Criteria:
- [ ] Scene timestamps extracted with <100ms error
- [ ] Buffering applied to segments
- [ ] I-frame index generated

### Task 2: Visual Content Classification
**Duration**: 2-3 days
**Priority**: Critical

#### Subtasks:
1. **Keyframe Sampling per Segment**
   - Sample 3-5 frames per segment (start/mid/end)
   - Downscale to 224x224 for consistent model input

2. **Multi-Model Inference**
   - Run NSFW, nudity, immodesty, and violence detectors on sampled frames
   - Aggregate scores per segment (max, mean, majority vote)

3. **Confidence Scoring**
   - Compute overall segment confidence with category weights
   - Flag low-confidence segments for review

#### Acceptance Criteria:
- [ ] Frame sampling stable across codecs
- [ ] Inference outputs normalized to [0,1]
- [ ] Aggregation strategy configurable

### Task 3: Audio Profanity Detection
**Duration**: 2 days
**Priority**: High

#### Subtasks:
1. **Segment-Aligned Transcription**
   - Extract audio per segment with ffmpeg `-ss`/`-to`
   - Transcribe with Whisper (base/small) for timestamps

2. **Profanity Event Detection**
   - Run profanity detector on segment transcripts
   - Map detected words to precise time offsets

3. **Severity and Action Mapping**
   - Classify events as mild/strong/extreme
   - Define actions: mute N seconds around event; skip segment for extreme

#### Acceptance Criteria:
- [ ] Word-level timestamps produced
- [ ] Profanity events stored with start/end
- [ ] Action mapping respects user sensitivity settings

### Task 4: Segment File Format and Storage
**Duration**: 1 day
**Priority**: Critical

#### Subtasks:
1. **Segment JSON Schema**
   ```json
   {
     "media_id": "<jellyfin-id>",
     "version": 1,
     "segments": [
       {
         "start": 120.5,
         "end": 135.8,
         "categories": ["immodesty", "nudity"],
         "scores": {"immodesty": 0.82, "nudity": 0.35},
         "action": "skip",
         "source": "ai",
         "confidence": 0.78
       }
     ]
   }
   ```

2. **Local Storage Strategy**
   - Store under `/segments/<library>/<media_id>.json`
   - Maintain checksum/index for quick lookup

3. **Caching and Invalidations**
   - Recompute when media file hash changes
   - Version segment files for reproducibility

#### Acceptance Criteria:
- [ ] JSON schema validated
- [ ] Files created per media item
- [ ] Cache invalidation works on changes

### Task 5: Hybrid Data Merging
**Duration**: 1-2 days
**Priority**: High

#### Subtasks:
1. **Import Community Segments**
   - Fetch MovieContentFilter data by title/year/hash
   - Normalize to local schema

2. **Merge Logic**
   - Prefer community segments; augment with AI gaps
   - Resolve overlaps: choose higher-confidence or union with smallest gap

3. **Provenance Tracking**
   - Preserve `source` field: `community`, `ai`, `manual`
   - Retain original IDs for round-trips

#### Acceptance Criteria:
- [ ] Community data imported successfully
- [ ] Merge rules deterministic and test-covered
- [ ] Provenance preserved in output

### Task 6: Quality Control & Review
**Duration**: 2 days
**Priority**: Medium

#### Subtasks:
1. **Human-in-the-Loop UI (optional service)**
   - Simple web UI to review flagged segments
   - Approve/reject and adjust timestamps

2. **Confidence Thresholds**
   - Global and per-category thresholds
   - Auto-flag segments near boundary for review

3. **Metrics & Reporting**
   - Precision/recall estimates via sampled manual checks
   - Processing throughput and resource usage

#### Acceptance Criteria:
- [ ] Review workflow operational
- [ ] Thresholds configurable per profile
- [ ] Metrics exported (Prometheus/JSON)

## Deliverables
- Scene detection scripts and services
- AI aggregation and scoring modules
- Profanity detection integration
- Segment JSON schema and storage layer
- Merge engine with community data support
- Review UI (if implemented) and metrics

## Performance Targets
- 1080p: >= 2x real-time on GPU; >= 0.5x on CPU
- Segment timestamp accuracy: ±0.3s typical, ±0.5s worst-case
- Profanity alignment error: < 250ms median

## Next Steps
- Integrate with Jellyfin plugin (Phase 3A/3C)
- Expose pipeline via REST for plugin to trigger per-media analysis
- Add unit/integration tests for all modules