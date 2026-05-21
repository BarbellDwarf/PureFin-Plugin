"""Profanity Detector Service - Audio-based profanity detection using Whisper ASR.

This service transcribes the audio track of a video file and identifies time-coded
segments that contain profane language. It is designed to run alongside the other
PureFin AI services and is called by the scene-analyzer when PROFANITY_DETECTOR_URL
is configured.

Current status
--------------
The Whisper model is loaded on first use.  If the ``openai-whisper`` package is not
installed (or model loading fails) the service starts in *degraded mode* and returns
profanity=0.0 for all segments so that the rest of the pipeline continues to work.
Enabling the full Whisper integration requires only that the package and the model
weights are present (see README / SETUP.md).
"""

import os
import logging
import subprocess
import threading
import time
import re
from datetime import datetime

from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
HTTP_ACCESS_LOGS = os.getenv('HTTP_ACCESS_LOGS', '0') == '1'
if not HTTP_ACCESS_LOGS:
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter('profanity_detector_requests_total', 'Total profanity detection requests')
REQUEST_DURATION = Histogram('profanity_detector_request_duration_seconds', 'Request duration')
ERROR_COUNT = Counter('profanity_detector_errors_total', 'Total errors')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_SIZE = os.getenv('WHISPER_MODEL_SIZE', 'base')  # tiny, base, small, medium, large
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models')
USE_GPU = os.getenv('USE_GPU', '0') == '1'
PROCESSING_DIR = os.getenv('PROCESSING_DIR', '/tmp/processing')

# Profanity word list — extend as needed.  Matching is case-insensitive and
# matches whole words only (surrounded by word boundaries).
_PROFANITY_WORDS = [
    r'\bfuck\b', r'\bfucking\b', r'\bfucked\b', r'\bfucker\b',
    r'\bshit\b', r'\bshitty\b', r'\bbitch\b', r'\basshole\b',
    r'\bdamn\b', r'\bbastard\b', r'\bcunt\b', r'\bdick\b',
    r'\bcrap\b', r'\bwhore\b', r'\bslut\b', r'\bass\b',
    r'\bhell\b', r'\bpiss\b',
]
_PROFANITY_RE = re.compile('|'.join(_PROFANITY_WORDS), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Whisper model state
# ---------------------------------------------------------------------------
_model = None
_model_lock = threading.Lock()
_model_available = False
_model_load_error: str | None = None
_model_device = 'cpu'
_service_start_time = time.time()


def _load_model(force_device: str | None = None):
    """Load Whisper model on first use."""
    global _model, _model_available, _model_load_error, _model_device
    with _model_lock:
        if _model is not None and force_device is None:
            return _model_available
        try:
            import whisper  # openai-whisper
            import torch
            device = force_device or ('cuda' if USE_GPU and torch.cuda.is_available() else 'cpu')
            if USE_GPU and device == 'cpu':
                logger.warning("USE_GPU=1 but no GPU runtime detected; falling back to CPU")
            logger.info("Loading Whisper '%s' model on %s ...", MODEL_SIZE, device)
            _model = whisper.load_model(MODEL_SIZE, device=device)
            _model_available = True
            _model_device = device
            logger.info("Whisper model loaded successfully")
        except ImportError:
            _model_load_error = "openai-whisper not installed — running in degraded mode"
            logger.warning(_model_load_error)
        except Exception as e:  # noqa: BLE001
            _model_load_error = f"Whisper model load failed: {e}"
            logger.error(_model_load_error)
        return _model_available


def _extract_audio(video_path: str, output_path: str) -> bool:
    """Extract mono 16 kHz audio track from a video file via FFmpeg."""
    try:
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-ar', '16000', '-ac', '1', '-f', 'wav',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("Audio extraction failed: %s", e)
        return False


def _score_text(text: str) -> float:
    """Return a 0.0–1.0 profanity confidence based on word-match density."""
    if not text:
        return 0.0
    words = text.split()
    if not words:
        return 0.0
    matches = len(_PROFANITY_RE.findall(text))
    # Clamp: up to 5 hits per 10 words = 1.0 confidence.
    return min(1.0, matches / max(1, len(words)) * 10)


def _analyze_video(video_path: str):
    """Return a list of per-segment profanity scores mapped to scene timestamps.

    Each element is ``{"start": float, "end": float, "profanity": float}``.
    Falls back to a single zero-score segment covering the whole video when
    Whisper is unavailable.
    """
    if not _model_available:
        _load_model()

    if not _model_available:
        logger.debug("Whisper unavailable — returning 0.0 for entire video")
        try:
            probe = subprocess.check_output(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                timeout=30
            )
            duration = float(probe.decode().strip())
        except Exception:
            duration = 0.0
        return [{'start': 0.0, 'end': duration, 'profanity': 0.0}]

    os.makedirs(PROCESSING_DIR, exist_ok=True)
    audio_path = os.path.join(PROCESSING_DIR, f'audio_{os.getpid()}_{int(time.time())}.wav')
    try:
        if not _extract_audio(video_path, audio_path):
            return []

        logger.info("Transcribing audio for profanity detection: %s", video_path)
        try:
            result = _model.transcribe(audio_path, word_timestamps=True, verbose=False)
        except Exception as ex:  # noqa: BLE001
            if _model_device == 'cuda':
                logger.warning("Whisper GPU transcription failed (%s); retrying on CPU", ex)
                if not _load_model(force_device='cpu'):
                    raise
                result = _model.transcribe(audio_path, word_timestamps=True, verbose=False)
            else:
                raise

        segments = []
        for seg in result.get('segments', []):
            score = _score_text(seg.get('text', ''))
            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'profanity': score,
                'text': seg.get('text', '').strip()
            })
        logger.info("Transcription produced %d segments", len(segments))
        return segments
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


# ---------------------------------------------------------------------------
# Flask endpoints
# ---------------------------------------------------------------------------

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'profanity-detector'}), 200


@app.route('/ready')
def ready():
    ready_flag = _model_available
    status = 'ready' if ready_flag else 'degraded'
    code = 200 if ready_flag else 503
    return jsonify({
        'status': status,
        'model': MODEL_SIZE,
        'device': _model_device,
        'model_available': ready_flag,
        'load_error': _model_load_error,
    }), code


@app.route('/status')
def status():
    return jsonify({
        'service': 'profanity-detector',
        'model_size': MODEL_SIZE,
        'device': _model_device,
        'model_available': _model_available,
        'load_error': _model_load_error,
        'uptime_seconds': int(time.time() - _service_start_time),
    })


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4'}


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a video file for profanity.

    Request body (JSON)::

        {"video_path": "/mnt/media/movie.mp4"}

    Response::

        {
            "success": true,
            "video_path": "/mnt/media/movie.mp4",
            "model_available": true,
            "segments": [
                {"start": 0.0, "end": 4.2, "profanity": 0.0, "text": "Hey let's go"},
                {"start": 4.2, "end": 5.1, "profanity": 0.85, "text": "What the fuck?"},
                ...
            ]
        }
    """
    REQUEST_COUNT.inc()
    start = time.time()
    try:
        data = request.get_json(force=True) or {}
        video_path = data.get('video_path', '')
        if not video_path:
            return jsonify({'error': 'video_path is required'}), 400
        if not os.path.exists(video_path):
            return jsonify({'error': f'Video file not found: {video_path}'}), 404

        segments = _analyze_video(video_path)

        REQUEST_DURATION.observe(time.time() - start)
        return jsonify({
            'success': True,
            'video_path': video_path,
            'model_available': _model_available,
            'segments': segments,
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:  # noqa: BLE001
        ERROR_COUNT.inc()
        logger.error("Error in /analyze: %s", e)
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _preload():
    """Pre-load the Whisper model in a background thread at startup.

    Retries once after a short delay to work around ROCm runtime initialization
    races where torch.cuda.is_available() may return False on the first call
    even when a GPU is present (seen in WSL2/ROCm environments).
    """
    import torch

    # Brief wait to allow the ROCm/HIP runtime to fully initialize.
    if USE_GPU:
        time.sleep(3)

    logger.info("Pre-loading Whisper model in background ...")
    _load_model()

    # If we loaded on CPU despite requesting GPU, retry once after a longer
    # delay in case the GPU runtime needed more time to become available.
    if USE_GPU and _model_device == 'cpu' and torch.cuda.is_available():
        logger.warning("GPU became available after initial load; reloading Whisper on cuda ...")
        _load_model(force_device='cuda')


if __name__ == '__main__':
    threading.Thread(target=_preload, daemon=True).start()
    os.makedirs(PROCESSING_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=3000, debug=False)
