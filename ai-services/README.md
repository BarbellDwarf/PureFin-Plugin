# PureFin Content Filter - AI Services

This directory contains the AI services that power content analysis for the PureFin Content Filter Jellyfin plugin.

## ⚠️ Real Models and Auto-Download Behavior

All detector services now support lazy model initialization. If local model assets are
missing, the service advertises `lazy_download` on `/ready` and downloads/loads the
model on first inference request.

Recommended pre-warm step after first startup:

```bash
python scripts/download-models.py --models all --violence-profile balanced
```

```
ai-services/
└── models/
    ├── nsfw/                                       ← required for NSFW detection
    ├── violence/speed/                             ← optional violence profile cache
    ├── violence/balanced/                          ← default violence profile cache
    ├── violence/quality/                           ← optional violence profile cache
    └── clip/clip-vit-base-patch32/ ← required for CLIP-based classification
```

See `models/model-manifest.json` for the canonical list of required models.

## Quick Start

1. **Configure your paths** - See [SETUP.md](SETUP.md) for detailed instructions
2. **Copy environment template**: `cp .env.example .env`
3. **Edit `.env`** with your media library path
4. **Start services**:
   - **CPU only**: `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build -d`
   - **NVIDIA (CUDA)**: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d`
   - **AMD on WSL2**: `docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build -d`
   - **AMD native Linux**: `docker compose -f docker-compose.yml -f docker-compose.amd-linux.yml up --build -d`
   - **Intel iGPU (VAAPI decode)**: `docker compose -f docker-compose.yml -f docker-compose.intel.yml up --build -d`

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
                         │Violence Detector │
                         │ (HF ViT / Torch) │
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

### Violence Detector (Port 3003)
- **Purpose**: Classifies violent vs non-violent frames
- **Technology**: HuggingFace Transformers + PyTorch
- **Function**: Provides calibrated violence probability (`violence_score`)
- **Model profiles**:
  - `speed` → `nghiabntl/vit-base-violence-detection` (fastest)
  - `balanced` → `jaranohaal/vit-base-violence-detection` (default)
  - `quality` → `framasoft/vit-base-violence-detection` (+TTA for higher stability)

## Configuration Files

- **`docker-compose.yml`** - Active configuration (customize this)
- **`docker-compose.template.yml`** - Template with environment variables
- **`docker-compose.gpu.yml`** - NVIDIA GPU overlay (optional)
- **`docker-compose.cpu.yml`** - Explicit CPU-only overlay (optional)
- **`docker-compose.amd.yml`** - AMD ROCm overlay (optional)
- **`docker-compose.amd-linux.yml`** - AMD ROCm native Linux overlay (optional)
- **`docker-compose.intel.yml`** - Intel iGPU overlay (optional)
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

### Hardware performance expectations

Actual throughput depends heavily on codec, resolution, sample count, and storage speed.
Use this as an operational baseline for full-library analysis:

| Hardware class | Typical effective throughput |
|---|---|
| CPU-only (older 4 cores) | ~0.15x - 0.4x real-time |
| CPU-only (newer 8+ cores) | ~0.4x - 1.0x real-time |
| Older GPU (GTX 10xx / RX 5xxx / Arc A3xx) | ~1.0x - 2.5x real-time |
| Newer mid/high GPU (RTX 30/40, RX 6/7/9xxx, Arc A7xx+) | ~2.5x - 8x real-time |

Interpretation example: a 100-minute movie at 2x takes ~50 minutes to complete.

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
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

**Performance improvement:** 5-10x faster analysis with GPU vs CPU!

### Custom Models

Place custom AI models in the `models/` directory:

```
ai-services/
├── models/
│   ├── nsfw/
│   ├── violence/balanced/
│   └── clip/
```

They'll be available at `/app/models/` inside containers.

### Violence model profile switching

Set these in `.env` (or compose environment) and restart containers:

```bash
VIOLENCE_MODEL_PROFILE=balanced   # speed | balanced | quality
VIOLENCE_MODEL_ID=                # optional custom override
VIOLENCE_MODEL_SUBDIR=            # optional custom cache subdir
```

The scene-analyzer `/health` and `/runtime` endpoints expose the active downstream violence model/profile/device for plugin-side introspection.

### Resource Management (Idle Model Unload)

By default, models are unloaded after inactivity and reloaded on-demand:

- `MODEL_IDLE_UNLOAD_SECONDS` (default: `900`)
- `MODEL_IDLE_CHECK_SECONDS` (default: `30`)

Scene-analyzer queue behavior:

- `ANALYSIS_QUEUE_MAX_SIZE` (default: `8`)
- `ANALYSIS_QUEUE_WAIT_TIMEOUT_SECONDS` (default: `10800`)

## API Testing

Test each service independently:

```bash
# Health checks
curl http://localhost:3002/health  # Scene Analyzer
curl http://localhost:3001/health  # NSFW Detector
curl http://localhost:3003/health  # Violence Detector

# Readiness checks — returns 200 when models are loaded, 503 when not
curl http://localhost:3001/ready   # NSFW Detector
curl http://localhost:3003/ready   # Violence Detector
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

Control Flask access-log verbosity (`INFO:werkzeug ...` lines):

```bash
# quiet (default)
HTTP_ACCESS_LOGS=0

# verbose per-request access logs (debugging)
HTTP_ACCESS_LOGS=1
```

View specific service logs:
```bash
docker-compose logs -f scene-analyzer
docker-compose logs -f nsfw-detector
docker-compose logs -f violence-detector
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

**Processing Speed (quick reference):**
- CPU (older): ~0.15x-0.4x real-time
- CPU (newer): ~0.4x-1.0x real-time
- Older GPU: ~1.0x-2.5x real-time
- Newer GPU: ~2.5x-8x real-time

## Support

For detailed setup instructions, see [SETUP.md](SETUP.md)

For plugin configuration, see [../docs/install.md](../docs/install.md)

For issues or questions, check the main project README.
