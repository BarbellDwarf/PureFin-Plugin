# PureFin Content Filter Plugin

AI-powered content filtering for Jellyfin media server. Detects and skips objectionable content using self-hosted AI analysis. No data leaves your server — all processing runs locally via Docker.

> **ABI / Compatibility**: net8.0 · Jellyfin 10.9+ · targetAbi 10.9.0.0

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| NSFW filtering | ✅ | Real model path; service returns 503 if models not loaded |
| Violence filtering | ✅ | Threshold-based; wired to sensitivity presets |
| Profanity filtering | 🔲 | Planned — requires Whisper audio pipeline |
| Skip action | ✅ | Seeks to end of flagged segment |
| Mute action | ⚠️ | Falls back to skip with a log warning (no native mute API) |
| Sensitivity presets | ✅ | Low/Medium/High map to score thresholds (0.85 / 0.65 / 0.45) |
| Per-user profiles | 🔲 | Planned — all users currently share global settings |
| Community data | ⚠️ | Config option present; logs warning; no source implemented yet |
| Manual overrides | 🔲 | Planned — segment edit UI not started |

---

## Quick Start

### Host Install (plugin only, AI services running separately)

1. Add the plugin repository in Jellyfin (see [Plugin Repository](#plugin-repository) section below).
2. Install **PureFin** from the catalog and restart Jellyfin.
3. Go to **Dashboard → Plugins → PureFin → Settings** and set `AiServiceBaseUrl` if needed.

### Docker (Jellyfin + AI services)

```bash
# Start all AI services (nsfw-detector:3001, scene-analyzer:3002, content-classifier:3004)
cd ai-services
docker compose up -d

# Verify readiness
curl http://localhost:3001/ready
curl http://localhost:3002/ready
curl http://localhost:3004/ready
```

Then install the plugin via the Jellyfin catalog and point `AiServiceBaseUrl` at `http://localhost:3002`.

### Windows

Follow the Docker steps above (Docker Desktop required), then install via the plugin repository.

---

## Plugin Repository

Repository URL:
```
https://barbellDwarf.github.io/PureFin-Plugin/repository.json
```

Steps:
1. **Dashboard → Plugins → Repositories → +**
2. Paste the URL above and save.
3. Go to **Catalog**, find **PureFin**, and click **Install**.
4. Restart Jellyfin when prompted.

---

## Requirements

- **Jellyfin** 10.9+
- **.NET 8 runtime** on the Jellyfin server
- **Python 3.10+** and **Docker** (for AI services)

---

## Documentation

- [Installation Guide](docs/install.md)
- [Configuration Reference](docs/configuration.md)
- [Versioning Policy](docs/versioning.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Architecture

```
Jellyfin Server
└── Content Filter Plugin (.NET 8)
    ├── PluginServiceRegistrator  ← registers services via IPluginServiceRegistrator
    ├── SegmentStore              ← in-memory + JSON file cache
    ├── PlaybackMonitor           ← 500 ms polling; executes skip actions
    └── AnalyzeLibraryTask        ← calls AI scene-analyzer, persists segments

AI Services (Docker)
├── scene-analyzer      (port 3002)  ← orchestrator called by plugin
├── nsfw-detector       (port 3001)  ← NSFW/nudity detection
└── content-classifier  (port 3004)  ← violence/content classification
```

Segments are stored as JSON files (one per media item). Raw AI scores are persisted; thresholds are applied dynamically at playback time based on the current sensitivity setting.

---

## Project Structure

```
PureFin-Plugin/
├── Jellyfin.Plugin.ContentFilter/       # C# plugin
│   ├── Configuration/                   # PluginConfiguration + SensitivityThresholds
│   ├── Models/                          # Segment, SegmentData
│   ├── Services/                        # SegmentStore, PlaybackMonitor
│   ├── Tasks/                           # AnalyzeLibraryTask
│   ├── Web/                             # config.html
│   ├── Plugin.cs
│   └── PluginServiceRegistrator.cs
├── Jellyfin.Plugin.ContentFilter.Tests/ # xUnit test project
├── ai-services/                         # Python AI services + Docker Compose
├── docs/                                # Extended documentation
└── build.yaml                           # Plugin manifest
```

---

## License

See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Jellyfin](https://jellyfin.org/) — Free Software Media System
- [FFmpeg](https://ffmpeg.org/) — Video processing

