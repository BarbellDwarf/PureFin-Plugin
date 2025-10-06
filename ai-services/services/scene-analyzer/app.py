"""Scene Analyzer Service - Video scene detection and analysis."""

import os
import logging
import subprocess
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('scene_analyzer_requests_total', 'Total scene analysis requests')
REQUEST_DURATION = Histogram('scene_analyzer_request_duration_seconds', 'Scene analysis request duration')
ERROR_COUNT = Counter('scene_analyzer_errors_total', 'Total scene analysis errors')

# Service URLs
NSFW_DETECTOR_URL = os.getenv('NSFW_DETECTOR_URL', 'http://nsfw-detector:3000')
CONTENT_CLASSIFIER_URL = os.getenv('CONTENT_CLASSIFIER_URL', 'http://content-classifier:3000')


def extract_scenes(video_path, threshold=0.3):
    """Extract scene boundaries from video using FFmpeg.
    
    Args:
        video_path: Path to video file
        threshold: Scene detection threshold (0.0-1.0)
        
    Returns:
        List of scene timestamps
    """
    try:
        # Get video duration first
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        duration = float(subprocess.check_output(probe_cmd).decode().strip())
        
        # Detect scenes
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'select=gt(scene\\,{threshold}),showinfo',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
        
        # Parse scene timestamps from showinfo output
        timestamps = []
        for line in result.stdout.split('\n'):
            if 'pts_time:' in line:
                match = re.search(r'pts_time:(\d+\.?\d*)', line)
                if match:
                    timestamps.append(float(match.group(1)))
        
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
        
    except Exception as e:
        logger.error(f"Error extracting scenes: {e}")
        raise


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
        
        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
        
    except Exception as e:
        logger.error(f"Error extracting frame: {e}")
        raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'scene-analyzer'
    })


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
        threshold = data.get('threshold', 0.3)
        sample_count = data.get('sample_count', 3)
        
        # Check if file exists
        if not os.path.exists(video_path):
            ERROR_COUNT.inc()
            return jsonify({'error': 'Video file not found'}), 404
        
        logger.info(f"Analyzing video: {video_path}")
        
        # Extract scenes
        scenes = extract_scenes(video_path, threshold)
        logger.info(f"Found {len(scenes)} scenes")
        
        # Analyze sample frames from each scene (simplified for development)
        results = []
        for i, scene in enumerate(scenes[:10]):  # Limit to first 10 scenes for demo
            # Sample frames from scene
            mid_time = (scene['start'] + scene['end']) / 2
            
            result = {
                'start': scene['start'],
                'end': scene['end'],
                'duration': scene['duration'],
                'analysis': {
                    'nudity': 0.02,
                    'immodesty': 0.05,
                    'violence': 0.01,
                    'confidence': 0.85
                }
            }
            results.append(result)
        
        return jsonify({
            'success': True,
            'video_path': video_path,
            'scene_count': len(scenes),
            'scenes': results,
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
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
