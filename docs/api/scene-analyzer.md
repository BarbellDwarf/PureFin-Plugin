# Scene Analyzer API

## Overview

The Scene Analyzer service extracts scene boundaries from videos and coordinates content analysis with other services.

**Base URL**: `http://localhost:3002`

## Endpoints

### Health Check

Check service health.

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "scene-analyzer"
}
```

### Analyze Video

Analyze a video file for scenes and content.

```http
POST /analyze
Content-Type: application/json
```

**Request Body**:
```json
{
  "video_path": "/path/to/video.mp4",
  "threshold": 0.3,
  "sample_count": 3
}
```

**Parameters**:
- `video_path` (string, required): Full path to video file
- `threshold` (number, optional): Scene detection threshold (0.0-1.0, default: 0.3)
- `sample_count` (number, optional): Number of frames to sample per scene (default: 3)

**Response**:
```json
{
  "success": true,
  "video_path": "/path/to/video.mp4",
  "scene_count": 45,
  "scenes": [
    {
      "start": 0.0,
      "end": 15.5,
      "duration": 15.5,
      "analysis": {
        "nudity": 0.02,
        "immodesty": 0.05,
        "violence": 0.01,
        "confidence": 0.85
      }
    },
    {
      "start": 15.5,
      "end": 30.2,
      "duration": 14.7,
      "analysis": {
        "nudity": 0.85,
        "immodesty": 0.75,
        "violence": 0.05,
        "confidence": 0.92
      }
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Error Response**:
```json
{
  "error": "Video file not found",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Prometheus Metrics

Expose Prometheus metrics for monitoring.

```http
GET /metrics
```

## Usage Examples

### cURL

```bash
# Analyze video
curl -X POST http://localhost:3002/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/media/movies/example.mp4", "threshold": 0.3}'
```

### Python

```python
import requests

response = requests.post(
    'http://localhost:3002/analyze',
    json={
        'video_path': '/media/movies/example.mp4',
        'threshold': 0.3,
        'sample_count': 3
    }
)

result = response.json()
print(f"Found {result['scene_count']} scenes")
for scene in result['scenes']:
    print(f"Scene {scene['start']:.1f}s-{scene['end']:.1f}s: "
          f"nudity={scene['analysis']['nudity']:.2f}")
```

### C#

```csharp
using var client = new HttpClient();

var request = new
{
    video_path = "/media/movies/example.mp4",
    threshold = 0.3,
    sample_count = 3
};

var content = new StringContent(
    JsonSerializer.Serialize(request),
    Encoding.UTF8,
    "application/json"
);

var response = await client.PostAsync("http://localhost:3002/analyze", content);
var result = await response.Content.ReadAsStringAsync();
```

## Scene Detection Algorithm

The service uses FFmpeg's scene detection filter with configurable threshold:

1. Extract scene change timestamps using `select='gt(scene,threshold)'`
2. Merge scenes shorter than 2 seconds
3. Cap maximum scene length at 180 seconds
4. Add buffer zones (±0.3s) for smoother playback

## Configuration

Environment variables:

- `PROCESSING_DIR`: Temporary processing directory (default: `/tmp/processing`)
- `NSFW_DETECTOR_URL`: NSFW detector service URL
- `CONTENT_CLASSIFIER_URL`: Content classifier service URL
- `PORT`: Service port (default: `3000`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Performance

- Processing speed: 2-5x real-time (GPU), 0.5-1x real-time (CPU)
- Memory usage: 2-4GB depending on video resolution
- Disk space: Temporary frame storage requires ~1GB per video

## Error Codes

- `400`: Bad request (missing or invalid parameters)
- `404`: Video file not found
- `500`: Internal server error
- `503`: Service unavailable
