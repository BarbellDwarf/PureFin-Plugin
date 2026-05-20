# User Guide

## Overview

PureFin detects and filters objectionable content in your Jellyfin library using local AI services.

Current categories:
- Nudity
- Immodesty (revealing clothing)
- Violence

## How It Works

1. **Analyze**: The scheduled task sends video scene windows to AI services.
2. **Store**: Segment JSON is saved per media item with raw AI scores.
3. **Filter**: During playback, PureFin evaluates each segment against current thresholds and skips matching content.

## Getting Started

1. Install and configure PureFin (see [Installation Guide](./install.md)).
2. Run **Analyze Library for PureFin** from **Dashboard → Scheduled Tasks**.
3. Tune sensitivity and category toggles in **Dashboard → Plugins → PureFin**.
4. Play media normally; filtering is applied automatically.

## Configuring Filters

Open **Dashboard → Plugins → PureFin**.

- **Enable/Disable Categories**: Toggle nudity, immodesty, violence.
- **Sensitivity / Thresholds**: Control how aggressively segments are flagged.
- **Scene Detection Method**: Use `transnetv2` for accurate variable-length scene detection (recommended).

## Reviewing Segments (Admin)

Use the built-in admin page:

1. Open **Dashboard → Plugins → PureFin Segments**.
2. Search for a movie or episode.
3. Click **View Segments** to inspect start/end/duration, action, categories, and raw scores.

## Known Limitations

- `mute` action currently falls back to `skip`.
- Per-user profiles are not implemented yet (global configuration applies to all users).
- Profanity audio pipeline is planned, not currently active.

## Troubleshooting and FAQ

- [Troubleshooting Guide](./troubleshooting.md)
- [FAQ](./faq.md)
