# Running a Test Analysis

## Prerequisites

1. Install Python 3.8+ and Docker Desktop for Windows

2. Bootstrap the AI models (one-time setup):
   ```powershell
   cd ai-services\scripts
   pip install torch torchvision requests
   python bootstrap_models.py --models-dir ..\models
   ```

3. Build and start services:
   ```powershell
   cd ai-services
   docker compose up --build -d
   ```

4. Wait for services to be ready (check logs):
   ```powershell
   docker compose logs -f
   ```

5. Verify services are ready:
   ```powershell
   curl http://localhost:3002/ready  # scene-analyzer
   curl http://localhost:3001/ready  # nsfw-detector
   curl http://localhost:3004/ready  # content-classifier
   ```

## Run a test analysis

Send a POST request to scene-analyzer:

```powershell
curl -X POST http://localhost:3002/analyze `
  -H "Content-Type: application/json" `
  -d '{"media_path": "/mnt/d/Media/Movies/YourMovie.mkv", "item_id": "test-001"}'
```

**Note on paths:** Inside Docker containers (WSL2), `D:\Media\Movies` appears as `/mnt/d/Media/Movies`. Docker Desktop automatically mounts drive letters this way.

## AMD GPU acceleration (optional)

See `GPU_SETUP.md` for full AMD ROCm setup. Once AMD ROCm is configured:

```powershell
docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d
```

## Check results

The analyze endpoint returns a JSON object with detected segments and content scores. Example:

```json
{
  "item_id": "test-001",
  "segments": [
    {
      "start": 12.5,
      "end": 28.3,
      "type": "violence",
      "confidence": 0.72,
      "action": "skip"
    }
  ],
  "analysis_duration_ms": 45000
}
```

## Notes on expected behavior

- **First run is slow**: The CLIP model (~600MB) downloads from HuggingFace on first use. Subsequent runs use the cached model.
- **Low violence confidence scores**: Until a real trained model replaces the bootstrap weights, violence detection confidence will be low. This is expected.
- **NSFW detection**: Uses a real trained MobileNetV2 model (GantMan) — scores are meaningful immediately.
- **CPU mode**: All three services run on CPU by default. A 2-hour movie may take 30–60 minutes to analyse fully.
