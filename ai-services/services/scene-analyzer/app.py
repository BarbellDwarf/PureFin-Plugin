"""Scene Analyzer Service - Video scene detection and analysis."""

import os
import logging
import subprocess
import re
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTTP session with retries
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=[502, 503, 504],
    allowed_methods=["POST", "GET"],
)
adapter = HTTPAdapter(max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Prometheus metrics
REQUEST_COUNT = Counter('scene_analyzer_requests_total', 'Total scene analysis requests')
REQUEST_DURATION = Histogram('scene_analyzer_request_duration_seconds', 'Scene analysis request duration')
ERROR_COUNT = Counter('scene_analyzer_errors_total', 'Total scene analysis errors')

# Service URLs
NSFW_DETECTOR_URL = os.getenv('NSFW_DETECTOR_URL', 'http://nsfw-detector:3000')
CONTENT_CLASSIFIER_URL = os.getenv('CONTENT_CLASSIFIER_URL', 'http://content-classifier:3000')
USE_GPU = os.getenv('USE_GPU', '0') == '1'
USE_AMF = os.getenv('USE_AMF', '0') == '1'

# FFmpeg GPU detection cache
ffmpeg_hwaccels = []
ffmpeg_cuda_available = False
ffmpeg_amf_available = False
ffmpeg_vaapi_available = False

# TransNetV2 model cache
transnetv2_model = None
transnetv2_available = False

TRANSNET_THRESHOLD = float(os.getenv('TRANSNET_THRESHOLD', '0.5'))
MIN_SCENE_DURATION_SECONDS = float(os.getenv('MIN_SCENE_DURATION_SECONDS', '1.0'))
TRANSNET_DYNAMIC_PERCENTILE = float(os.getenv('TRANSNET_DYNAMIC_PERCENTILE', '99.5'))

def load_transnetv2():
    """Load TransNetV2 model for AI-based scene detection."""
    global transnetv2_model, transnetv2_available
    
    try:
        import torch
        from transnetv2_pytorch import TransNetV2
        
        logger.info("Loading TransNetV2 model...")
        transnetv2_model = TransNetV2()
        
        # Move to GPU if available and requested
        device = 'cuda' if USE_GPU and torch.cuda.is_available() else 'cpu'
        transnetv2_model = transnetv2_model.to(device)
        transnetv2_model.eval()
        
        transnetv2_available = True
        if device == 'cuda' and (ffmpeg_amf_available or ffmpeg_vaapi_available):
            logger.info("TransNetV2 loaded on CUDA device (hip/ROCm may be active — AMD GPU hwaccel detected)")
        else:
            logger.info("TransNetV2 model loaded successfully on device: %s", device)
        return True
    except Exception as e:
        logger.warning("Could not load TransNetV2: %s. Falling back to FFmpeg scene detection.", e)
        transnetv2_available = False
        return False

def detect_ffmpeg_hwaccel():
    """Detect FFmpeg hardware accelerators available inside the container.

    Returns:
        Tuple (hwaccels: list[str], cuda_available: bool, amf_available: bool, vaapi_available: bool)
    """
    try:
        out = subprocess.check_output(['ffmpeg', '-hide_banner', '-hwaccels'], stderr=subprocess.STDOUT, text=True)
        # Output lists available hwaccels, one per line after header
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        # Skip header lines
        accels = [item for item in lines if not item.lower().startswith('hardware acceleration methods')]
        cuda_available = any(h.lower() == 'cuda' for h in accels)
        amf_available = any(h.lower() == 'amf' for h in accels)
        vaapi_available = any(h.lower() == 'vaapi' for h in accels)
        if USE_GPU and cuda_available:
            logger.info("FFmpeg CUDA hwaccel available")
        if USE_AMF and amf_available:
            logger.info("FFmpeg AMF hwaccel available (AMD GPU)")
        if vaapi_available:
            logger.info("FFmpeg VAAPI hwaccel available")
        if not (cuda_available or amf_available or vaapi_available):
            logger.info("FFmpeg hwaccels: %s", ', '.join(accels) if accels else 'none')
        return accels, cuda_available, amf_available, vaapi_available
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning("Could not detect FFmpeg hwaccels: %s", e)
        return [], False, False, False

def ffmpeg_gpu_args():
    """Return base FFmpeg args to enable hardware acceleration when available and requested."""
    if USE_AMF and ffmpeg_amf_available:
        return ['-hwaccel', 'amf']
    elif USE_GPU and ffmpeg_cuda_available:
        # Prefer enabling decode acceleration and keeping surfaces on GPU where possible
        # We only enable hwaccel, not forcing output format, to avoid filter incompatibilities.
        return ['-hwaccel', 'cuda']
    elif USE_GPU and ffmpeg_vaapi_available:
        return ['-hwaccel', 'vaapi']
    return []


def get_video_duration(video_path):
    """Get video duration in seconds."""
    probe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    duration = float(subprocess.check_output(probe_cmd).decode().strip())
    logger.info("Video duration: %.2f seconds (%.1f minutes)", duration, duration/60)
    return duration


def _normalize_scene_probabilities(predictions):
    """Normalize TransNetV2 output to a 1D probability array."""
    import numpy as np

    if isinstance(predictions, (list, tuple)):
        raw = predictions[1] if len(predictions) > 1 else predictions[0]
    else:
        raw = predictions

    scene_probs = np.asarray(raw).squeeze()
    if scene_probs.ndim != 1:
        scene_probs = scene_probs.reshape(-1)

    scene_probs = np.nan_to_num(scene_probs, nan=0.0, posinf=1.0, neginf=0.0)
    scene_probs = np.clip(scene_probs, 0.0, 1.0)
    return scene_probs


def _select_transition_frames(scene_probs, threshold, min_gap_frames):
    """Find representative transition peaks above threshold."""
    import numpy as np

    candidate_indices = np.where(scene_probs >= threshold)[0]
    if candidate_indices.size == 0:
        return []

    def pick_peak(start_idx, end_idx):
        window = scene_probs[start_idx:end_idx + 1]
        rel_peak = int(np.argmax(window))
        return start_idx + rel_peak

    run_peaks = []
    run_start = int(candidate_indices[0])
    previous = int(candidate_indices[0])

    for raw_idx in candidate_indices[1:]:
        idx = int(raw_idx)
        if idx == previous + 1:
            previous = idx
            continue
        run_peaks.append(pick_peak(run_start, previous))
        run_start = idx
        previous = idx

    run_peaks.append(pick_peak(run_start, previous))

    # Enforce minimum spacing between boundaries while keeping the stronger peak.
    filtered_peaks = []
    for peak in run_peaks:
        if not filtered_peaks:
            filtered_peaks.append(peak)
            continue

        if peak - filtered_peaks[-1] < min_gap_frames:
            if scene_probs[peak] > scene_probs[filtered_peaks[-1]]:
                filtered_peaks[-1] = peak
        else:
            filtered_peaks.append(peak)

    return filtered_peaks


def _compute_transition_threshold(scene_probs, base_threshold):
    """Compute an adaptive threshold to avoid noisy over-segmentation."""
    import numpy as np

    if scene_probs.size < 120:
        return base_threshold

    percentile_threshold = float(np.percentile(scene_probs, TRANSNET_DYNAMIC_PERCENTILE))
    adaptive_threshold = max(base_threshold, percentile_threshold)

    # Keep headroom to avoid threshold values that suppress nearly all transitions.
    adaptive_threshold = min(adaptive_threshold, 0.98)
    return adaptive_threshold


def _build_scene_windows(duration, timestamps, min_scene_duration):
    """Create contiguous scene windows that cover the full video duration."""
    boundaries = [0.0]
    boundaries.extend(sorted({
        float(ts) for ts in timestamps
        if min_scene_duration <= float(ts) <= max(duration - min_scene_duration, min_scene_duration)
    }))
    boundaries.append(float(duration))

    scenes = []
    previous = boundaries[0]
    for boundary in boundaries[1:]:
        if boundary <= previous:
            continue
        scenes.append({
            'start': previous,
            'end': boundary,
            'duration': boundary - previous
        })
        previous = boundary

    if not scenes:
        return [{'start': 0.0, 'end': float(duration), 'duration': float(duration)}]

    # Merge tiny segments into neighbors so we avoid noisy micro-scenes.
    if min_scene_duration > 0 and len(scenes) > 1:
        merged = []
        for scene in scenes:
            if merged and scene['duration'] < min_scene_duration:
                merged[-1]['end'] = scene['end']
                merged[-1]['duration'] = merged[-1]['end'] - merged[-1]['start']
            else:
                merged.append(scene.copy())

        if len(merged) > 1 and merged[0]['duration'] < min_scene_duration:
            merged[1]['start'] = 0.0
            merged[1]['duration'] = merged[1]['end'] - merged[1]['start']
            merged = merged[1:]

        scenes = merged

    return scenes


def extract_scenes_transnetv2(video_path):
    """Extract scene boundaries using TransNetV2 AI model.
    
    Args:
        video_path: Path to video file
        
    Returns:
        List of scene dictionaries
    """
    try:
        import torch
        
        if not transnetv2_available or transnetv2_model is None:
            raise RuntimeError("TransNetV2 model not available")
        
        logger.info("Using TransNetV2 for scene detection...")
        duration = get_video_duration(video_path)
        
        predictions = transnetv2_model.predict_video(video_path)
        scene_probs = _normalize_scene_probabilities(predictions)
        
        # Get frame rate
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        fps_str = subprocess.check_output(probe_cmd).decode().strip()
        # Parse fractional frame rate like "24000/1001"
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            fps = num / den
        else:
            fps = float(fps_str)
        
        min_gap_frames = max(1, int(round(fps * MIN_SCENE_DURATION_SECONDS)))
        effective_threshold = _compute_transition_threshold(scene_probs, TRANSNET_THRESHOLD)
        scene_indices = _select_transition_frames(scene_probs, effective_threshold, min_gap_frames)

        if not scene_indices and effective_threshold > TRANSNET_THRESHOLD:
            scene_indices = _select_transition_frames(scene_probs, TRANSNET_THRESHOLD, min_gap_frames)
            effective_threshold = TRANSNET_THRESHOLD

        timestamps = [idx / fps for idx in scene_indices]

        logger.info(
            "TransNetV2 detected %d transitions at threshold %.3f",
            len(timestamps),
            effective_threshold
        )

        scenes = _build_scene_windows(duration, timestamps, MIN_SCENE_DURATION_SECONDS)
        return scenes
        
    except Exception as e:
        logger.error("TransNetV2 scene detection failed: %s", e)
        raise


def extract_scenes_sampling(video_path, interval_seconds=30):
    """Extract scenes using fixed interval sampling.
    
    Args:
        video_path: Path to video file
        interval_seconds: Sampling interval in seconds
        
    Returns:
        List of scene dictionaries
    """
    try:
        duration = get_video_duration(video_path)
        logger.info("Using fixed sampling (interval=%ds)", interval_seconds)
        
        scenes = []
        current = 0
        while current < duration:
            next_time = min(current + interval_seconds, duration)
            scenes.append({
                'start': current,
                'end': next_time,
                'duration': next_time - current
            })
            current = next_time
        
        logger.info("Created %d fixed-interval scenes", len(scenes))
        return scenes
        
    except Exception as e:
        logger.error("Fixed sampling failed: %s", e)
        raise


def extract_scenes_ffmpeg(video_path, threshold=0.3):
    """Extract scene boundaries using FFmpeg scene detection filter.
    
    Args:
        video_path: Path to video file
        threshold: Scene detection threshold (0.0-1.0)
        
    Returns:
        List of scene dictionaries
    """
    try:
        duration = get_video_duration(video_path)
        
        # Use FFmpeg scene detection
        logger.info("Using FFmpeg scene detection (threshold=%s)...", threshold)
        gpu_args = ffmpeg_gpu_args()
        cmd = [
            'ffmpeg'] + gpu_args + [
            '-i', video_path,
            '-vf', f'select=gt(scene\\,{threshold}),showinfo',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # Fallback: retry without GPU if failed
        if result.returncode != 0 and gpu_args:
            logger.warning("FFmpeg scene detection failed with GPU args, retrying on CPU...")
            cmd_fallback = ['ffmpeg', '-i', video_path, '-vf', f'select=gt(scene\\,{threshold}),showinfo', '-f', 'null', '-']
            result = subprocess.run(cmd_fallback, capture_output=True, text=True, check=False)
        logger.info("FFmpeg scene detection complete")
        
        # Parse scene timestamps from showinfo output (FFmpeg outputs to stderr)
        timestamps = []
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                match = re.search(r'pts_time:(\d+\.?\d*)', line)
                if match:
                    timestamps.append(float(match.group(1)))
        
        logger.info("Extracted %d timestamps from FFmpeg scene detection", len(timestamps))
        
        # Create scene windows
        scenes = []
        prev_time = 0.0
        for timestamp in timestamps:
            if timestamp - prev_time >= 2.0:  # Minimum 2 second scenes
                scenes.append({
                    'start': prev_time,
                    'end': min(timestamp, duration),
                    'duration': min(timestamp - prev_time, duration - prev_time)
                })
                prev_time = timestamp
        
        # Add final scene
        if prev_time < duration:
            scenes.append({
                'start': prev_time,
                'end': duration,
                'duration': duration - prev_time
            })
        
        return scenes
        
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        logger.error("FFmpeg scene detection failed: %s", e)
        raise


def extract_scenes(video_path, method='transnetv2', **kwargs):
    """Extract scene boundaries from video using specified method.
    
    Args:
        video_path: Path to video file
        method: Detection method ('transnetv2', 'ffmpeg', 'sampling')
        **kwargs: Method-specific parameters
        
    Returns:
        List of scene dictionaries
    """
    selected_method = (method or 'transnetv2').lower()

    if selected_method == 'sampling':
        interval = kwargs.get('sampling_interval', 30)
        logger.warning(
            "Sampling mode is coarse and not scene-accurate. "
            "Use transnetv2 for full shot-boundary detection."
        )
        return extract_scenes_sampling(video_path, interval)

    ffmpeg_threshold = kwargs.get('ffmpeg_scene_threshold', 0.3)

    if selected_method == 'ffmpeg':
        try:
            return extract_scenes_ffmpeg(video_path, ffmpeg_threshold)
        except Exception as ex:
            logger.warning("FFmpeg scene detection failed, falling back to TransNetV2: %s", ex)
            return extract_scenes_transnetv2(video_path)

    # Default workflow: TransNetV2 first, FFmpeg fallback.
    try:
        scenes = extract_scenes_transnetv2(video_path)
        if scenes:
            return scenes
        logger.warning("TransNetV2 produced no scenes; falling back to FFmpeg")
    except Exception as ex:
        logger.warning("TransNetV2 scene detection failed, falling back to FFmpeg: %s", ex)

    return extract_scenes_ffmpeg(video_path, ffmpeg_threshold)


def _extract_violence_score(violence_payload):
    """Extract a normalized violence score from multiple response formats."""
    violence_value = violence_payload.get('violence', 0)

    if isinstance(violence_value, dict):
        if 'general_violence' in violence_value:
            return float(violence_value.get('general_violence', 0.0))
        if 'overall_violence_score' in violence_value:
            return float(violence_value.get('overall_violence_score', 0.0))
        category_scores = violence_value.get('category_scores')
        if isinstance(category_scores, dict) and category_scores:
            if 'general_violence' in category_scores:
                return float(category_scores.get('general_violence', 0.0))
            return float(max(category_scores.values()))
        return 0.0

    if isinstance(violence_value, (int, float)):
        return float(violence_value)

    if isinstance(violence_payload.get('violence_score'), (int, float)):
        return float(violence_payload.get('violence_score'))

    return 0.0


def _build_sample_timestamps(scene, requested_samples, total_scene_count):
    """Build robust sampling timestamps inside scene boundaries."""
    sample_target = max(1, int(requested_samples))

    # Scale sample count down when the movie has many scene boundaries.
    if total_scene_count >= 1200:
        sample_target = min(sample_target, 1)
    elif total_scene_count >= 600:
        sample_target = min(sample_target, 2)
    elif total_scene_count >= 300:
        sample_target = min(sample_target, 3)

    start = float(scene['start'])
    end = float(scene['end'])
    duration = max(0.0, end - start)
    if duration <= 0:
        return [start]

    if duration <= 2:
        sample_target = 1
    elif duration <= 8:
        sample_target = min(sample_target, 2)
    elif duration <= 20:
        sample_target = min(sample_target, 3)

    padding = min(0.25, duration * 0.1)
    sample_start = start + padding
    sample_end = end - padding
    if sample_end <= sample_start:
        sample_start = start
        sample_end = max(start, end - 0.05)

    if sample_target == 1:
        midpoint = (sample_start + sample_end) / 2.0
        return [round(midpoint, 3)]

    timestamps = []
    interval = (sample_end - sample_start) / (sample_target - 1)
    for index in range(sample_target):
        timestamps.append(round(sample_start + (interval * index), 3))

    # Preserve order while de-duplicating.
    deduped = list(dict.fromkeys(timestamps))
    return deduped


def extract_frame(video_path, timestamp, output_path=None):
    """Extract a single frame from video at timestamp.
    
    Args:
        video_path: Path to video file
        timestamp: Time in seconds
        output_path: Optional output path for frame
        
    Returns:
        Path to extracted frame
    """
    try:
        if output_path is None:
            output_path = f"/tmp/processing/frame_{timestamp}.jpg"
        
        gpu_args = ffmpeg_gpu_args()
        # Use GPU decode acceleration via hwaccel; keep filters simple for compatibility
        cmd = [
            'ffmpeg'] + gpu_args + [
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0 and gpu_args:
            logger.warning("FFmpeg frame extraction failed with GPU args at %ss, retrying on CPU...", timestamp)
            cmd_fallback = ['ffmpeg', '-ss', str(timestamp), '-i', video_path, '-vframes', '1', '-q:v', '2', '-y', output_path]
            subprocess.run(cmd_fallback, check=True, capture_output=True)
        else:
            # If res was successful and check wasn't used, ensure non-zero raises
            if res.returncode != 0:
                res.check_returncode()
        return output_path
        
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, ValueError) as e:
        logger.error("Error extracting frame: %s", e)
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'use_gpu_requested': USE_GPU,
        'use_amf_requested': USE_AMF,
        'ffmpeg_cuda_available': ffmpeg_cuda_available,
        'ffmpeg_amf_available': ffmpeg_amf_available,
        'ffmpeg_vaapi_available': ffmpeg_vaapi_available,
        'ffmpeg_hwaccels': ffmpeg_hwaccels,
        'transnetv2_available': transnetv2_available,
        'timestamp': datetime.now().isoformat(),
        'service': 'scene-analyzer'
    })


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness endpoint — checks that all downstream services are ready."""
    try:
        nsfw_resp = requests.get(f"{NSFW_DETECTOR_URL}/ready", timeout=5)
        classifier_resp = requests.get(f"{CONTENT_CLASSIFIER_URL}/ready", timeout=5)

        if nsfw_resp.status_code == 200 and classifier_resp.status_code == 200:
            return jsonify({'status': 'ready', 'models_loaded': True})

        failed = 'nsfw-detector' if nsfw_resp.status_code != 200 else 'content-classifier'
        return jsonify({
            'status': 'degraded',
            'models_loaded': False,
            'reason': f'Downstream service not ready: {failed}'
        }), 503

    except requests.RequestException as e:
        return jsonify({
            'status': 'degraded',
            'models_loaded': False,
            'reason': f'Could not reach downstream services: {e}'
        }), 503


@app.route('/analyze', methods=['POST'])
@REQUEST_DURATION.time()
def analyze_video():
    """Analyze video for scenes and content."""
    REQUEST_COUNT.inc()
    
    try:
        data = request.get_json()
        
        if not data or 'video_path' not in data:
            ERROR_COUNT.inc()
            return jsonify({'error': 'No video_path provided'}), 400
        
        video_path = data['video_path']
        sample_count = data.get('sample_count', 3)
        
        # Get scene detection method and parameters
        scene_method = (data.get('scene_detection_method', 'transnetv2') or 'transnetv2').lower()
        ffmpeg_threshold = data.get('ffmpeg_scene_threshold', 0.3)
        sampling_interval = data.get('sampling_interval', 30)
        
        # Check if file exists
        if not os.path.exists(video_path):
            ERROR_COUNT.inc()
            return jsonify({'error': 'Video file not found'}), 404
        
        logger.info("Analyzing video: %s using method=%s", video_path, scene_method)
        
        # Extract scenes using specified method
        scenes = extract_scenes(
            video_path, 
            method=scene_method,
            ffmpeg_scene_threshold=ffmpeg_threshold,
            sampling_interval=sampling_interval
        )
        logger.info("Found %d scenes using %s method", len(scenes), scene_method)
        
        # If no scenes detected, use a minimal segmentation approach
        # This should not create artificial scenes, but ensure we analyze the video
        if len(scenes) == 0:
            logger.warning("No scenes detected by FFmpeg, analyzing entire video as single scene")
            probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                        '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
            duration = float(subprocess.check_output(probe_cmd).decode().strip())
            scenes = [{'start': 0, 'end': duration, 'duration': duration}]
        
        # Analyze each scene using real AI services
        results = []
        
        for i, scene in enumerate(scenes):
            try:
                timestamps = _build_sample_timestamps(scene, sample_count, len(scenes))
                
                # Extract and analyze frames
                nudity_scores = []
                violence_scores = []
                immodesty_scores = []
                
                for timestamp in timestamps:
                    frame_path = None
                    try:
                        # Extract frame
                        frame_path = extract_frame(
                            video_path,
                            timestamp,
                            f"/tmp/processing/scene_{i}_frame_{timestamp:.3f}.jpg"
                        )
                        
                        # Call NSFW detector for nudity/immodesty
                        with open(frame_path, 'rb') as f:
                            files = {'image': f}
                            nsfw_response = session.post(f"{NSFW_DETECTOR_URL}/analyze", 
                                                         files=files, timeout=60)
                        
                        if nsfw_response.status_code == 503:
                            ERROR_COUNT.inc()
                            return jsonify({
                                'error': 'Downstream service not ready',
                                'service': 'nsfw-detector',
                                'degraded': True
                            }), 503
                        if nsfw_response.status_code == 200:
                            nsfw_data = nsfw_response.json()
                            nudity_scores.append(nsfw_data.get('nudity', 0))
                            immodesty_scores.append(nsfw_data.get('immodesty', 0))
                        
                        # Call content classifier for violence
                        with open(frame_path, 'rb') as f:
                            files = {'image': f}
                            violence_response = session.post(f"{CONTENT_CLASSIFIER_URL}/classify", 
                                                            files=files, timeout=60)
                        
                        if violence_response.status_code == 503:
                            ERROR_COUNT.inc()
                            return jsonify({
                                'error': 'Downstream service not ready',
                                'service': 'content-classifier',
                                'degraded': True
                            }), 503
                        if violence_response.status_code == 200:
                            violence_data = violence_response.json()
                            violence_scores.append(_extract_violence_score(violence_data))
                    except (requests.RequestException, OSError, subprocess.CalledProcessError, ValueError, KeyError) as e:
                        logger.error("Error analyzing frame at %s: %s", timestamp, e)
                        continue
                    finally:
                        if frame_path and os.path.exists(frame_path):
                            os.remove(frame_path)
                
                # Calculate average scores for the scene
                avg_nudity = sum(nudity_scores) / len(nudity_scores) if nudity_scores else 0
                avg_violence = sum(violence_scores) / len(violence_scores) if violence_scores else 0
                avg_immodesty = sum(immodesty_scores) / len(immodesty_scores) if immodesty_scores else 0
                
                # Use max score as confidence (most confident detection)
                confidence = max([avg_nudity, avg_violence, avg_immodesty]) if any([nudity_scores, violence_scores, immodesty_scores]) else 0
                
                result = {
                    'start': scene['start'],
                    'end': scene['end'],
                    'duration': scene['duration'],
                    'analysis': {
                        'nudity': avg_nudity,
                        'immodesty': avg_immodesty,
                        'violence': avg_violence,
                        'confidence': confidence
                    }
                }
                results.append(result)
                
                logger.info("Scene %d/%d: violence=%.3f, nudity=%.3f, immodesty=%.3f", i+1, len(scenes), avg_violence, avg_nudity, avg_immodesty)
                
            except (requests.RequestException, OSError, subprocess.CalledProcessError, ValueError, KeyError) as e:
                logger.error("Error analyzing scene %d: %s", i, e)
                # Add scene with zero scores if analysis fails
                results.append({
                    'start': scene['start'],
                    'end': scene['end'],
                    'duration': scene['duration'],
                    'analysis': {
                        'nudity': 0,
                        'immodesty': 0,
                        'violence': 0,
                        'confidence': 0
                    }
                })
        
        return jsonify({
            'success': True,
            'schema_version': '1.0',
            'video_path': video_path,
            'scene_count': len(scenes),
            'scenes': results,
            'model_versions': {
                'nsfw-mobilenet': '1.0.0',
                'violence-classifier': '1.0.0'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except (ValueError, FileNotFoundError, requests.RequestException, subprocess.CalledProcessError) as e:
        ERROR_COUNT.inc()
        logger.error("Error processing request: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


if __name__ == '__main__':
    port = int(os.getenv('PORT', '3000'))
    
    # Detect FFmpeg HW acceleration support
    accels_detected, cuda_ok, amf_ok, vaapi_ok = detect_ffmpeg_hwaccel()
    ffmpeg_hwaccels = accels_detected
    ffmpeg_cuda_available = cuda_ok
    ffmpeg_amf_available = amf_ok
    ffmpeg_vaapi_available = vaapi_ok
    
    # Load TransNetV2 model
    load_transnetv2()
    
    # Create temp directory for frame processing
    os.makedirs('/tmp/processing', exist_ok=True)
    
    app.run(host='0.0.0.0', port=port, debug=False)
