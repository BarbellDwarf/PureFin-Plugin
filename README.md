# PureFin Plugin for Jellyfin

AI-powered content filtering for Jellyfin. PureFin analyzes media with self-hosted AI services and skips flagged segments during playback.

> **Compatibility**: `net9.0` plugin · Jellyfin `10.11.x` · `targetAbi 10.11.0.0`

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Scene detection (TransNetV2) | ✅ | Default method; variable-length scene windows |
| NSFW + immodesty scoring | ✅ | Threshold-based with dynamic filtering at playback |
| Violence scoring | ✅ | Category mapped from AI response scores |
| Queue pause/resume controls | ✅ | Admin can pause/resume scene-analyzer queue from plugin UI |
| Idle model auto-unload | ✅ | AI services unload inactive models and lazy-load on next request |
| Skip action | ✅ | Seeks to end of segment |
| Mute action | ⚠️ | Falls back to skip with a warning |
| Admin segment inspection UI | ✅ | `PureFin Segments` page and API |
| Per-user profiles | 🔲 | Planned |
| Profanity pipeline | 🔲 | Planned (audio/transcription pipeline required) |
| Community data merge | 🔲 | Planned |

---

## Quick Start

1. Add the plugin repository URL in Jellyfin (see [Plugin Repository](#plugin-repository)).
2. Install **PureFin** from the catalog and restart Jellyfin.
3. Start AI services and verify readiness.
4. Run **Analyze Library for PureFin** from **Dashboard → Scheduled Tasks**.

### Start AI Services

```bash
cd ai-services
docker compose up -d

curl http://localhost:3001/ready
curl http://localhost:3002/ready
curl http://localhost:3003/ready
```

Set `AiServiceBaseUrl` to `http://localhost:3002` if needed.  
For multi-host AI, add extra scene-analyzer URLs in `AiServiceBaseUrls` and choose `AiServiceLoadBalancingMode`.

Violence profile selection (container-side):

- `speed` → `nghiabntl/vit-base-violence-detection`
- `balanced` → `jaranohaal/vit-base-violence-detection` (default)
- `quality` → `framasoft/vit-base-violence-detection` (+TTA)

Set `VIOLENCE_MODEL_PROFILE` in `ai-services/.env` and restart containers to switch instantly.

---

## Plugin Repository

```
https://BarbellDwarf.github.io/PureFin-Plugin/repository.json
```

1. **Dashboard → Plugins → Repositories → +**
2. Add the URL above and save.
3. Go to **Catalog**, find **PureFin**, click **Install**.
4. Restart Jellyfin.

---

## Requirements

- **Jellyfin** `10.11.x`
- **Docker** `24+` for AI services
- **Python** `3.10+` for AI tooling/scripts
- Optional GPU acceleration for faster analysis

---

## Documentation

- [Installation Guide](docs/install.md)
- [Configuration Reference](docs/configuration.md)
- [Versioning Policy](docs/versioning.md)
- [Rollout and Operations](docs/rollout.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Architecture

```
Jellyfin Server
└── PureFin Plugin (.NET 9)
    ├── PluginServiceRegistrator
    ├── SegmentStore
    ├── PlaybackMonitor
    ├── AnalyzeLibraryTask
    └── PureFinSegmentsController

AI Services (Docker)
├── scene-analyzer      (port 3002)
├── nsfw-detector       (port 3001)
└── violence-detector   (port 3003)
```

Segments are persisted as JSON with raw AI scores. Active categories are derived dynamically from current threshold settings.

---

## Project Structure

```
PureFin-Plugin/
├── Jellyfin.Plugin.ContentFilter/
├── Jellyfin.Plugin.ContentFilter.Tests/
├── ai-services/
├── docs/
└── build.yaml
```

---

## License

See [LICENSE](LICENSE) for details.

