# Content Classifier API

## Overview

The Content Classifier service provides multi-category content classification for images including violence, nudity, and immodesty detection.

**Base URL**: `http://localhost:3003`

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
  "models_loaded": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "content-classifier"
}
```

### Classify Image

Perform comprehensive content classification on an image.

```http
POST /classify
Content-Type: multipart/form-data
```

**Parameters**:
- `image` (file, required): Image file to classify

**Response**:
```json
{
  "success": true,
  "results": {
    "violence": {
      "overall_violence_score": 0.05,
      "category_scores": {
        "blood": 0.02,
        "weapons": 0.01,
        "fighting": 0.03,
        "explosions": 0.01,
        "death": 0.00,
        "torture": 0.00,
        "general_violence": 0.05
      },
      "primary_violence_type": "general_violence"
    },
    "nudity": {
      "none": 0.85,
      "partial_nudity": 0.10,
      "full_nudity": 0.03,
      "suggestive": 0.02
    },
    "immodesty": {
      "modesty_score": 0.85,
      "exposed_areas": {
        "chest_area": 0.05,
        "upper_leg_area": 0.10,
        "midriff_area": 0.02,
        "back_area": 0.03
      },
      "clothing_type": "casual"
    },
    "content_rating": "PG",
    "overall_concern_score": 0.15
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Content Ratings**:
- `PG`: General audience (concern score < 0.3)
- `PG-13`: Parental guidance (concern score 0.3-0.5)
- `R`: Restricted (concern score 0.5-0.8)
- `X`: Adult only (concern score > 0.8)

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

**Metrics Exported**:
- `classifier_requests_total`: Total classification requests
- `classifier_request_duration_seconds`: Request duration histogram
- `classifier_errors_total`: Total errors

## Usage Examples

### cURL

```bash
# Classify image
curl -X POST -F "image=@/path/to/image.jpg" http://localhost:3003/classify
```

### Python

```python
import requests

with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:3003/classify',
        files={'image': f}
    )
    
result = response.json()
violence = result['results']['violence']['overall_violence_score']
nudity = result['results']['nudity']['full_nudity']
rating = result['results']['content_rating']

print(f"Violence: {violence:.2f}, Nudity: {nudity:.2f}, Rating: {rating}")
```

### C#

```csharp
using var client = new HttpClient();
using var content = new MultipartFormDataContent();

var imageContent = new ByteArrayContent(imageBytes);
imageContent.Headers.ContentType = new MediaTypeHeaderValue("image/jpeg");
content.Add(imageContent, "image", "image.jpg");

var response = await client.PostAsync("http://localhost:3003/classify", content);
var json = await response.Content.ReadAsStringAsync();
var result = JsonSerializer.Deserialize<ClassificationResult>(json);
```

## Classification Categories

### Violence Detection

Detects and classifies types of violence:
- Blood/gore
- Weapons (guns, knives, etc.)
- Fighting/combat
- Explosions/destruction
- Death/injury
- Torture
- General violence

### Nudity Detection

Classifies levels of nudity:
- None: No nudity detected
- Suggestive: Sexually suggestive but no nudity
- Partial: Partial nudity
- Full: Full nudity

### Immodesty Analysis

Analyzes clothing coverage and modesty:
- Exposed area percentages per body region
- Clothing type classification
- Overall modesty score

## Configuration

Environment variables:

- `MODEL_PATH`: Path to model files (default: `/app/models`)
- `PROCESSING_DIR`: Temporary processing directory (default: `/tmp/processing`)
- `PORT`: Service port (default: `3000`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `BATCH_SIZE`: Batch size for inference (default: `32`)

## Performance

- Average response time: 200-800ms per image
- Throughput: 5-20 requests/second (CPU)
- Throughput: 20-100 requests/second (GPU)
- Memory usage: ~2-4GB

## Error Codes

- `400`: Bad request (missing or invalid image)
- `500`: Internal server error
- `503`: Service unavailable (models not loaded)
