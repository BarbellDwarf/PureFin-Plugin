# PureFin Content Filter Plugin

AI-powered content filtering for Jellyfin media server. Detects and skips objectionable content using self-hosted AI analysis.

> **ABI / Compatibility**: net8.0 · Jellyfin 10.9.x – 10.11.x · targetAbi 10.9.0.0

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Plugin loads in Jellyfin | ✅ Implemented | Requires DI registration fix (v1.0.1+) |
| Library analysis task | ✅ Implemented | Schedules daily, calls scene-analyzer, stores segments |
| Playback monitor – Skip action | ✅ Implemented | Seeks to end of flagged segment |
| NSFW / violence detection pipeline | ✅ Implemented | Real model path; degrades gracefully if service down |
| Configuration UI | ✅ Implemented | Web page renders in Jellyfin dashboard |
| Sensitivity presets (Low/Medium/High) | ⚠️ Partial | Maps to thresholds in code; individual sliders override |
| Mute action | ⚠️ Partial | Logs warning and falls back to Skip (no native mute API) |
| PreferCommunityData setting | ⚠️ Partial | Config/UI only — logs warning; no source arbitration |
| Per-user profiles | 🔲 Planned | Not implemented; all users share global settings |
| Profanity / audio pipeline | 🔲 Planned | Whisper integration not started |
| Manual override UI | 🔲 Planned | Segment edit interface not started |
| Community data merge pipeline | 🔲 Planned | MovieContentFilter integration not started |

---

## Quick Start

### Prerequisites

- Jellyfin 10.9.x – 10.11.x
- Docker Engine 24+ (for AI services)
- 8 GB+ RAM (16 GB recommended)

### Installation

1. **Deploy AI Services** (scene-analyzer at `http://localhost:3002`):
```bash
cd ai-services
docker compose up -d
```

2. **Install Plugin**:
   - Build: `dotnet build --configuration Release` (requires .NET 8 SDK)
   - Copy `Jellyfin.Plugin.ContentFilter.dll` to your Jellyfin plugins directory

3. **Configure**:
   - Jellyfin Dashboard → Plugins → Content Filter
   - Set **AI Service Base URL** to `http://localhost:3002` (or your host)
   - Run the **Analyze Library for Content Filter** scheduled task

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
└── scene-analyzer  (port 3002)  ← TransNetV2 / FFmpeg scene detection + NSFW scoring
```

### Storage

Segments are stored as JSON files (one per media item) in the configured **Segment Directory**. Raw AI scores are stored; thresholds are applied dynamically at playback time based on the current sensitivity setting.

---

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| AI Service Base URL | `http://localhost:3002` | Scene-analyzer endpoint |
| Sensitivity | `moderate` | `strict` (0.45), `moderate` (0.65), `permissive` (0.85) |
| Enable Nudity / Immodesty / Violence / Profanity | `true` | Per-category on/off |
| Prefer Community Data | `true` | Reserved — no community source yet |
| Enable OSD Feedback | `false` | Shows a toast when content is skipped |
| Scene Detection Method | `transnetv2` | `transnetv2`, `ffmpeg`, or `sampling` |

---

## Known Limitations

- **Mute action** is a no-op in the Jellyfin plugin API; it falls back to Skip.
- **Profanity filtering** requires the audio pipeline (Whisper), which is not yet implemented.
- **Per-user profiles** are not implemented; all users share global settings.
- **Community data** (`PreferCommunityData`) has no backing source — setting is reserved.

---

## Project Structure

```
PureFin-Plugin/
├── Jellyfin.Plugin.ContentFilter/   # C# plugin
│   ├── Configuration/               # PluginConfiguration + SensitivityThresholds
│   ├── Models/                      # Segment, SegmentData
│   ├── Services/                    # SegmentStore, PlaybackMonitor
│   ├── Tasks/                       # AnalyzeLibraryTask
│   ├── Web/                         # config.html
│   ├── Plugin.cs
│   └── PluginServiceRegistrator.cs
├── ai-services/                     # Python scene-analyzer + Docker Compose
├── docs/                            # Extended documentation
└── build.yaml                       # Plugin manifest
```

---

## License

See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Jellyfin](https://jellyfin.org/) — Free Software Media System
- [FFmpeg](https://ffmpeg.org/) — Video processing

