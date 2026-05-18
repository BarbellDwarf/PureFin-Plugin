# PureFin Content Filter - AI Services

This directory contains the AI services that power content analysis for the PureFin Content Filter Jellyfin plugin.

## ⚠️ Real Model Files Required

AI services will **not** perform inference without trained model weight files in the `models/` directory.
Services start in a degraded state when models are missing — all `/analyze` and `/classify` endpoints
return **HTTP 503** until real models are present.

```
ai-services/
└── models/
    ├── nsfw/nsfw_model.h5          ← required for NSFW detection
    ├── violence/violence_model.h5  ← required for violence classification
    └── clip/clip-vit-base-patch32/ ← required for CLIP-based classification
```

See `models/model-manifest.json` for the canonical list of required models.

## Quick Start

1. **Configure your paths** - See [SETUP.md](SETUP.md) for detailed instructions
2. **Copy environment template**: `cp .env.example .env`
3. **Edit `.env`** with your media library path
4. **Start services**: 
   - **With GPU**: `docker-compose -f docker-compose.gpu.yml up -d` (see [GPU_SETUP.md](GPU_SETUP.md))
   - **CPU only**: `docker-compose up -d`

## What You Need to Configure

### Required: Media Library Path

The AI services need access to your Jellyfin media files to analyze them. 

**Edit `docker-compose.yml`** and replace `D:/Movies` with your actual media path:

```yaml
volumes:
  - D:/Movies:/mnt/media:ro  # <- Change this to YOUR media path
```

**Examples:**
- Windows: `D:/Movies:/mnt/media:ro`
- Linux: `/mnt/media/movies:/mnt/media:ro`
- NAS: `/volume1/media:/mnt/media:ro`

### Optional: Segments Directory

If you want the AI services to write segments directly to where your Jellyfin plugin reads them, also mount the segments directory:

```yaml
volumes:
  - D:/Movies:/mnt/media:ro
  - D:/jellytestconfig/segments:/segments:rw  # <- Add this line
```

## Architecture

```
┌─────────────────┐
│  Jellyfin       │
│  Plugin         │
└────────┬────────┘
         │ HTTP API (port 3002)
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Scene Analyzer  │─────►│  NSFW Detector   │
│   (FFmpeg)      │      │  (TensorFlow)    │
└─────────────────┘      └──────────────────┘
         │
         └──────────────►┌──────────────────┐
                         │Content Classifier│
                         │  (TensorFlow)    │
                         └──────────────────┘
```

## Services

### Scene Analyzer (Port 3002)
- **Purpose**: Main entry point for video analysis
- **Technology**: Python + FFmpeg
- **Function**: Detects scene boundaries, queues jobs, and coordinates content analysis
- **Requirements**: Access to media files (`/mnt/media`)

### NSFW Detector (Port 3001)
- **Purpose**: Identifies nudity and immodest content
- **Technology**: TensorFlow + OpenCV
- **Function**: Analyzes video frames for NSFW content
- **Models**: Pre-trained classification models

### Content Classifier (Port 3004)
- **Purpose**: Classifies violence, profanity, and other categories
- **Technology**: TensorFlow
- **Function**: Multi-label content classification
- **Models**: Custom trained models

## Configuration Files

- **`docker-compose.yml`** - Active configuration (customize this)
- **`docker-compose.template.yml`** - Template with environment variables
- **`.env.example`** - Environment variable examples
- **`SETUP.md`** - Detailed setup instructions

## Common Issues

### "File not found" when analyzing videos

**Problem**: AI service can't find the video file

**Solution**: 
1. Check that media path is mounted correctly in `docker-compose.yml`
2. Verify the path matches your Jellyfin media library
3. Ensure Jellyfin sends paths that match the mounted directory

**Example**:
- Jellyfin sees: `/mnt/Media/Movie.mkv`
- AI container must have: `- /host/path:/mnt/Media:ro`

### Connection refused from Jellyfin

**Problem**: Jellyfin plugin can't reach AI services

**Solutions**:
- **Windows/Mac Docker Desktop**: Use `host.docker.internal:3002`
- **Linux**: Use `172.17.0.1:3002` or host IP
- **Same Docker network**: Use container name `scene-analyzer:3000`

### Slow analysis performance

**Solutions**:
- Add GPU support (NVIDIA Docker)
- Reduce `sample_count` in API requests
- Process fewer scenes (increase `threshold`)
- Upgrade Docker resources (RAM, CPU)

### Queue paused / analysis not progressing

**Problem**: Jobs are queued but not processing.

**Solution**:
```bash
curl http://localhost:3002/queue/status
curl -X POST http://localhost:3002/queue/resume
```

You can also pause/resume from the PureFin plugin UI.

## Advanced Configuration

### Using .env File (Recommended)

Instead of editing `docker-compose.yml` directly, use environment variables:

1. `cp .env.example .env`
2. Edit `.env` with your paths
3. `cp docker-compose.template.yml docker-compose.yml`
4. `docker-compose up -d`

The template uses environment variables so you never need to edit YAML directly.

### GPU Acceleration

For significantly faster content analysis with NVIDIA GPUs, see **[GPU_SETUP.md](GPU_SETUP.md)** for complete setup instructions.

**Quick GPU Start:**
```bash
# Install NVIDIA Container Toolkit
# See GPU_SETUP.md for detailed instructions

# Start with GPU support
docker-compose -f docker-compose.gpu.yml up -d
```

**Performance improvement:** 5-10x faster analysis with GPU vs CPU!

### Custom Models

Place custom AI models in the `models/` directory:

```
ai-services/
├── models/
│   ├── nsfw_model.h5
│   ├── violence_model.h5
│   └── profanity_model.pkl
```

They'll be available at `/app/models/` inside containers.

### Resource Management (Idle Model Unload)

By default, models are unloaded after inactivity and reloaded on-demand:

- `MODEL_IDLE_UNLOAD_SECONDS` (default: `900`)
- `MODEL_IDLE_CHECK_SECONDS` (default: `30`)

Scene-analyzer queue behavior:

- `ANALYSIS_QUEUE_MAX_SIZE` (default: `8`)
- `ANALYSIS_QUEUE_WAIT_TIMEOUT_SECONDS` (default: `3600`)

## API Testing

Test each service independently:

```bash
# Health checks
curl http://localhost:3002/health  # Scene Analyzer
curl http://localhost:3001/health  # NSFW Detector
curl http://localhost:3004/health  # Content Classifier

# Readiness checks — returns 200 when models are loaded, 503 when not
curl http://localhost:3001/ready   # NSFW Detector
curl http://localhost:3004/ready   # Content Classifier
curl http://localhost:3002/ready   # Scene Analyzer (checks all downstream services)

# Queue controls
curl http://localhost:3002/queue/status
curl -X POST http://localhost:3002/queue/pause -H "Content-Type: application/json" -d '{"reason":"maintenance"}'
curl -X POST http://localhost:3002/queue/resume

# Analyze a video (requires media path mounted)
curl -X POST http://localhost:3002/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/mnt/media/test.mp4",
    "threshold": 0.3,
    "sample_count": 3
  }'
```

## Logs and Debugging

View logs for all services:
```bash
docker-compose logs -f
```

View specific service logs:
```bash
docker-compose logs -f scene-analyzer
docker-compose logs -f nsfw-detector
docker-compose logs -f content-classifier
```

## Updating

Pull latest changes and rebuild:

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Resource Requirements

**Minimum:**
- 4GB RAM
- 2 CPU cores
- 10GB disk space (for models and temp files)

**Recommended:**
- 8GB RAM
- 4 CPU cores
- NVIDIA GPU with 4GB+ VRAM
- 20GB disk space

**Processing Speed:**
- CPU: 0.5-1x real-time (slower than video playback)
- GPU: 2-5x real-time (faster than video playback)

## Support

For detailed setup instructions, see [SETUP.md](SETUP.md)

For plugin configuration, see [../docs/install.md](../docs/install.md)

For issues or questions, check the main project README.
