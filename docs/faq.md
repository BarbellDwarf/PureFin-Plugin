# Frequently Asked Questions

## General

### What is PureFin?

PureFin is a Jellyfin plugin that automatically detects and skips objectionable content (NSFW, violence, profanity) using self-hosted AI services. All processing runs locally via Docker — no data is sent externally.

### How does it work?

A scheduled task analyzes your media library by sending video frames to local AI services. Detected segments are stored as JSON files. During playback, the plugin monitors position and seeks over flagged segments.

---

## Compatibility

### Does PureFin work with all Jellyfin clients?

Only clients that support chapter/segment skip via the Jellyfin API. Web and most mobile clients support this. Direct DLNA playback does **not** support server-side skip actions.

### Which Jellyfin versions are supported?

Jellyfin **10.11.x**. The plugin targets `targetAbi 10.11.0.0` and is built against Jellyfin package version 10.11.8.

### Does it work with Emby or Plex?

No. PureFin uses Jellyfin-specific APIs and will only work with Jellyfin.

---

## Features

### Can I mute audio instead of skipping?

The mute action is **not yet supported** via the Jellyfin plugin API. When the action is set to `mute`, the plugin falls back to `skip` and logs a warning. True mute support would require client-side cooperation.

### Does per-user filtering work?

Per-user profiles are **planned for a future release**. Currently, all users share the global plugin configuration.

### Will PureFin work offline?

Yes. All AI services run locally via Docker — no external network calls are made for analysis or filtering.

### Can I filter profanity?

Profanity filtering requires the audio pipeline (Whisper transcription), which is **not yet implemented**. The `EnableProfanity` toggle is present but currently has no effect.

---

## Setup and Operations

### Do I need a GPU?

No. A GPU is optional but will speed up initial library analysis significantly.

### How long does initial analysis take?

Depends on library size and hardware:
- ~2–5 minutes per hour of video (GPU)
- ~5–15 minutes per hour of video (CPU)

### Why are my AI services returning HTTP 503?

Placeholder/random model generation has been removed. The services return 503 until real model files are placed at the paths defined in `ai-services/models/model-manifest.json`. See [Troubleshooting](./troubleshooting.md) for details.

### Where is segment data stored?

JSON files, one per media item, in the configured `SegmentDirectory` (default: `/segments`).

---

## Contributing

### Where can I get help?

- [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
- Review the [Troubleshooting Guide](./troubleshooting.md)

### Is there a roadmap?

See the feature status table in the [README](../README.md) for the current state of each feature.
