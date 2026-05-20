# PureFin Plugin Rollout and Operations Guide

## Release Channels

| Channel | Repository URL | Description |
|---------|---------------|-------------|
| Stable | `https://BarbellDwarf.github.io/PureFin-Plugin/repository.json` | Production-ready |

Pre-release builds are marked as GitHub pre-releases and are not included in the stable manifest.

---

## Staged Rollout

### Alpha
- Manual install from GitHub Releases ZIP
- For developers and early testers

### Beta (Current State)
- Available via Jellyfin plugin repository (pre-release channel)
- Tested on Jellyfin 10.11.8 with Docker AI services
- Feature-complete core pipeline with ongoing scale validation

### Stable
- Available via stable repository manifest
- Requires: all CI checks pass, install smoke test passes, changelog published

---

## Upgrade Path

1. Jellyfin will notify you of plugin updates if you've added the repository.
2. Go to **Dashboard → Plugins → Updates**.
3. Click **Update** next to PureFin.
4. Restart Jellyfin when prompted.
5. After restart, verify AI services are still reachable:
   ```bash
   curl http://localhost:3002/ready
   ```

---

## Downgrade / Rollback

1. Download the previous version ZIP from [GitHub Releases](https://github.com/BarbellDwarf/PureFin-Plugin/releases).
2. Stop Jellyfin.
3. Remove current plugin files from `<data>/plugins/Jellyfin.Plugin.ContentFilter*/`.
4. Extract old version ZIP to `<data>/plugins/`.
5. Restart Jellyfin.

---

## Monitoring

**Key log sources:**
- Jellyfin server log (Dashboard → Logs) for plugin errors
- Docker logs: `docker compose logs -f` in `ai-services/`

**Key indicators:**
- Plugin loaded: look for `PureFin` or `Jellyfin.Plugin.ContentFilter` entries in Jellyfin startup logs
- AI services ready: `curl http://localhost:3002/ready` returns `{"status": "ready", ...}`
- Analysis running: Scheduled Tasks log in Jellyfin dashboard

---

## Model File Requirements

AI services refuse to run with placeholder/random model files. Real model files must be provided:

1. Obtain trained model files for:
   - NSFW model files (`models/nsfw/mobilenet_v2_140_224/*`)
   - Violence model profile files (`models/violence/speed|balanced|quality/*`) or enable lazy download
   - CLIP model (for content-classifier, legacy/optional)

2. Place them in the paths defined in `ai-services/models/model-manifest.json`.

3. Restart services:
   ```bash
   docker compose restart
   ```

4. Verify:
   ```bash
   curl http://localhost:3001/ready
   # Expected: {"status": "ready", "models_loaded": true}
   ```

---

## ABI Compatibility

| Plugin Version | targetAbi | Supported Jellyfin |
|---------------|-----------|-------------------|
| 1.0.x | 10.11.0.0 | 10.11.x |

When Jellyfin releases a breaking ABI change, a new plugin version with an updated `targetAbi` will be required.

---

## Deprecation Policy

- Plugin versions are supported for one major Jellyfin release cycle.
- ABI bumps will be announced in the CHANGELOG with at least one minor release notice.
- Model schema versions: old schema versions are supported for two plugin minor releases after a new schema ships.
