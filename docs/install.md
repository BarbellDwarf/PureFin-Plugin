# Installation Guide

## Prerequisites

- **Jellyfin Server**: 10.9 or higher
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
   https://barbellDwarf.github.io/PureFin-Plugin/repository.json
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

### Wait for Readiness

Check each service is ready before running library analysis:

```bash
curl http://localhost:3001/ready   # nsfw-detector
curl http://localhost:3004/ready   # content-classifier
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
| content-classifier | 3004 | Violence/content classification |

---

## Plugin Configuration

After installation, configure the plugin:

1. Go to **Dashboard → Plugins → PureFin → Settings**.
2. Set `AiServiceBaseUrl` to `http://localhost:3002` (this is the default).
3. Adjust sensitivity and category toggles as needed.
4. Go to **Dashboard → Scheduled Tasks** and run **Analyze Content Library** for initial analysis.

---

## See Also

- [Configuration Reference](./configuration.md)
- [Troubleshooting](./troubleshooting.md)
- [Versioning Policy](./versioning.md)
