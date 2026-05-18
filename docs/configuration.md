# Configuration Reference

Access plugin configuration: **Dashboard → Plugins → PureFin → Settings**

---

## All Configuration Options

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `AiServiceBaseUrl` | string | `http://localhost:3002` | Base URL for the scene-analyzer service (the plugin's primary AI endpoint) |
| `Sensitivity` | string | `moderate` | Sensitivity preset: `strict`, `moderate`, or `permissive` |
| `EnableNudity` | bool | `true` | Enable NSFW/nudity filtering |
| `EnableImmodesty` | bool | `true` | Enable immodesty filtering |
| `EnableViolence` | bool | `true` | Enable violence filtering |
| `EnableProfanity` | bool | `true` | Enable profanity filtering (requires audio pipeline — not yet active) |
| `NudityThreshold` | double | `0.35` | Overridden by sensitivity preset |
| `ImmodestyThreshold` | double | `0.20` | Overridden by sensitivity preset |
| `ViolenceThreshold` | double | `0.45` | Overridden by sensitivity preset |
| `ProfanityThreshold` | double | `0.30` | Not currently overridden by preset |
| `SegmentDirectory` | string | `/segments` | Directory for JSON segment files |
| `PreferCommunityData` | bool | `true` | **Planned** — logs a warning when set; no community source is active |
| `EnableOsdFeedback` | bool | `false` | Show on-screen toast when content is skipped |
| `SceneDetectionMethod` | string | `transnetv2` | `transnetv2`, `ffmpeg`, or `sampling` |
| `FfmpegSceneThreshold` | double | `0.3` | Scene cut threshold for `ffmpeg` method |
| `SamplingIntervalSeconds` | int | `30` | Frame sampling interval for `sampling` method |

---

## Sensitivity Presets

The `Sensitivity` setting overrides the individual NSFW and violence threshold sliders. Lower thresholds = more aggressive filtering.

| Preset | NSFW Threshold | Violence Threshold | Effect |
|--------|---------------|-------------------|--------|
| `strict` | 0.45 | 0.45 | Catches most flagged content; may have more false positives |
| `moderate` | 0.65 | 0.65 | Balanced (default) |
| `permissive` | 0.85 | 0.85 | Only very high-confidence detections |

---

## Content Categories

- **Nudity / Immodesty**: Detected by the nsfw-detector service (port 3001).
- **Violence**: Detected by the content-classifier service (port 3004).
- **Profanity**: Planned — requires Whisper audio pipeline, not yet active.

---

## Planned / Not Yet Active Settings

- **`PreferCommunityData`**: Config option is present and will log a one-time warning when enabled. No community data source is integrated yet.
- **Per-user profiles**: The configuration UI notes this as "Coming in a future release." All users currently share the global plugin settings.

---

## Analysis Queue Controls (Admin)

The PureFin settings page includes queue controls backed by the scene-analyzer service:

- **Refresh Queue Status**
- **Pause Queue**
- **Resume Queue**

Queue status includes pending jobs, active jobs, processed count, failed count, and idle-unload timeout.

When paused, new analysis requests are still accepted and queued, but processing is halted until resumed.

---

## AI Service Runtime Controls (Docker)

`ai-services/docker-compose.yml` exposes environment variables for queue/resource behavior:

| Name | Default | Description |
|------|---------|-------------|
| `MODEL_IDLE_UNLOAD_SECONDS` | `900` | Unload in-memory AI models after this many idle seconds |
| `MODEL_IDLE_CHECK_SECONDS` | `30` | Idle-unload check interval |
| `ANALYSIS_QUEUE_MAX_SIZE` | `8` | Maximum queued jobs in scene-analyzer |
| `ANALYSIS_QUEUE_WAIT_TIMEOUT_SECONDS` | `3600` | Max API wait time for queued request completion |

---

## Backup and Restore

```bash
# Backup plugin configuration
cp /var/lib/jellyfin/config/plugins/ContentFilter.xml ~/backup/

# Backup segment data
tar -czf segments_backup.tar.gz /segments/

# Restore
cp ~/backup/ContentFilter.xml /var/lib/jellyfin/config/plugins/
tar -xzf segments_backup.tar.gz -C /
```

---

## See Also

- [Installation Guide](./install.md)
- [Troubleshooting](./troubleshooting.md)
