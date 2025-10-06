# NSFW Detector API

## Overview

The NSFW Detector service analyzes images for nudity and adult content using machine learning models.

**Base URL**: `http://localhost:3001`

## Endpoints

### Health Check

Check service health and model status.

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "nsfw-detector"
}
```

### Analyze Image

Analyze an image for NSFW content.

```http
POST /analyze
Content-Type: multipart/form-data
```

**Parameters**:
- `image` (file, required): Image file to analyze

**Response**:
```json
{
  "success": true,
  "results": {
    "drawings": 0.05,
    "hentai": 0.02,
    "neutral": 0.85,
    "porn": 0.03,
    "sexy": 0.05
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Categories**:
- `drawings`: Drawn/animated content (0.0-1.0)
- `hentai`: Hentai/anime adult content (0.0-1.0)
- `neutral`: Safe/neutral content (0.0-1.0)
- `porn`: Pornographic content (0.0-1.0)
- `sexy`: Sexually suggestive content (0.0-1.0)

**Error Response**:
```json
{
  "error": "Error message",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Prometheus Metrics

Expose Prometheus metrics for monitoring.

```http
GET /metrics
```

**Response**: Prometheus-formatted metrics

**Metrics Exported**:
- `nsfw_requests_total`: Total number of analysis requests
- `nsfw_request_duration_seconds`: Request duration histogram
- `nsfw_errors_total`: Total number of errors

## Usage Examples

### cURL

```bash
# Health check
curl http://localhost:3001/health

# Analyze image
curl -X POST -F "image=@/path/to/image.jpg" http://localhost:3001/analyze
```

### Python

```python
import requests

# Analyze image
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:3001/analyze',
        files={'image': f}
    )
    
result = response.json()
print(f"Nudity score: {result['results']['porn']}")
```

### C#

```csharp
using var client = new HttpClient();
using var content = new MultipartFormDataContent();

var imageContent = new ByteArrayContent(imageBytes);
imageContent.Headers.ContentType = new MediaTypeHeaderValue("image/jpeg");
content.Add(imageContent, "image", "image.jpg");

var response = await client.PostAsync("http://localhost:3001/analyze", content);
var result = await response.Content.ReadAsStringAsync();
```

## Configuration

Environment variables:

- `MODEL_PATH`: Path to model files (default: `/app/models`)
- `PROCESSING_DIR`: Temporary processing directory (default: `/tmp/processing`)
- `PORT`: Service port (default: `3000`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Performance

- Average response time: 100-500ms per image
- Throughput: 10-50 requests/second (CPU)
- Throughput: 50-200 requests/second (GPU)
- Memory usage: ~1-2GB

## Error Codes

- `400`: Bad request (missing or invalid image)
- `500`: Internal server error
- `503`: Service unavailable (model not loaded)
