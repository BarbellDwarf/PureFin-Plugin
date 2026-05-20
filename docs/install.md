# Installation Guide

## Prerequisites

- **Jellyfin Server**: 10.11.x
- **Docker Engine**: 24.0 or higher (for AI services)
- **Python**: 3.10+ (on the host running AI services)
- **System Requirements**:
  - 8 GB+ RAM (16 GB recommended)
  - Optional: NVIDIA GPU with drivers + NVIDIA Container Toolkit for GPU acceleration

---

## Method 1: Via Jellyfin Plugin Repository (Preferred)

This is the recommended approach for production use.

1. In Jellyfin, go to **Dashboard → Plugins → Repositories**.
2. Click **+** to add a new repository.
3. Enter the URL:
   ```
   https://BarbellDwarf.github.io/PureFin-Plugin/repository.json
   ```
4. Click **Save**.
5. Go to **Catalog**, find **PureFin**, and click **Install**.
6. Restart Jellyfin when prompted.

---

## Method 2: Manual Install (Development)

Use this method when working from source or testing a pre-release build.

1. Download the plugin ZIP from [GitHub Releases](https://github.com/BarbellDwarf/PureFin-Plugin/releases).
2. Extract the ZIP to your Jellyfin `plugins/` folder:
   - **Linux**: `/var/lib/jellyfin/plugins/`
   - **Windows**: `C:\ProgramData\Jellyfin\Server\plugins\`
   - **Docker**: the path mapped to `/config/plugins/`
3. Restart Jellyfin.

---

## AI Services Setup

The plugin calls a local scene-analyzer service. All AI services run in Docker.

### Start Services

```bash
cd ai-services
docker compose up -d
```

### Choose a Violence Model Profile (speed / balanced / quality)

Set `VIOLENCE_MODEL_PROFILE` in `ai-services/.env` before starting containers:

| Profile | Model ID | Tradeoff |
|---------|----------|----------|
| `speed` | `nghiabntl/vit-base-violence-detection` | Fastest startup/inference |
| `balanced` | `jaranohaal/vit-base-violence-detection` | Default balance of speed/quality |
| `quality` | `framasoft/vit-base-violence-detection` | Slower but uses additional TTA pass for more stable scores |

Switching profiles is a drop-in change: update `VIOLENCE_MODEL_PROFILE`, then restart the AI containers.

By default, AI services auto-unload models after idle time and lazy-load them on the next request. You can override this with environment variables in `ai-services/docker-compose.yml`:

- `MODEL_IDLE_UNLOAD_SECONDS` (default `900`)
- `MODEL_IDLE_CHECK_SECONDS` (default `30`)
- `ANALYSIS_QUEUE_MAX_SIZE` (scene-analyzer queue, default `8`)
- `ANALYSIS_QUEUE_WAIT_TIMEOUT_SECONDS` (default `3600`)

### Wait for Readiness

Check each service is ready before running library analysis:

```bash
curl http://localhost:3001/ready   # nsfw-detector
curl http://localhost:3003/ready   # violence-detector
curl http://localhost:3002/ready   # scene-analyzer (orchestrator)
```

Expected response when ready:
```json
{"status": "ready", "models_loaded": true}
```

> **Note:** Placeholder/random model generation has been disabled. Services return HTTP 503 until real model files are provided in the paths defined in `ai-services/models/model-manifest.json`. See [Troubleshooting](./troubleshooting.md) for details.

### Port Reference

| Service | Host Port | Purpose |
|---------|-----------|---------|
| scene-analyzer | 3002 | Orchestrator — called directly by the plugin |
| nsfw-detector | 3001 | NSFW/nudity detection |
| violence-detector | 3003 | Violence classification |

---

## Plugin Configuration

After installation, configure the plugin:

1. Go to **Dashboard → Plugins → PureFin → Settings**.
2. Set `AiServiceBaseUrl` to `http://localhost:3002` (this is the default).
3. Optional: set `AiServiceBaseUrls` with additional scene-analyzer hosts and choose `AiServiceLoadBalancingMode` (`round_robin` or `failover`).
4. Adjust sensitivity and category toggles as needed.
5. Go to **Dashboard → Scheduled Tasks** and run **Analyze Library for PureFin** for initial analysis.
6. Optional: use **Analysis Queue Controls (Admin)** in the plugin page to pause/resume queue processing across all configured hosts.

---

## See Also

- [Configuration Reference](./configuration.md)
- [Troubleshooting](./troubleshooting.md)
- [Versioning Policy](./versioning.md)
