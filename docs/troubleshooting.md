# Troubleshooting Guide

## Plugin Not Loading

**Symptoms:** Plugin doesn't appear in Jellyfin dashboard or plugin settings after installation.

**Steps:**

1. Check Jellyfin log for `PureFin` or `Jellyfin.Plugin.ContentFilter` entries at startup:
   - Dashboard → Logs, or grep the log file: `grep -i "PureFin\|Jellyfin.Plugin.ContentFilter\|PluginServiceRegistrator" /var/log/jellyfin/*.log`

2. Verify Jellyfin version is **10.11.x** — earlier versions have a different plugin ABI.

3. Ensure the plugin ZIP was extracted to `<jellyfin-data>/plugins/` and Jellyfin was fully restarted (not just config reloaded).

4. Confirm the installed plugin version matches the Jellyfin ABI requirement (`targetAbi 10.11.0.0`).

---

## AI Services Not Reachable

**Symptoms:** Library analysis fails; plugin log shows connection errors to AI services.

**Steps:**

1. Run `docker compose ps` in `ai-services/` — all services should show `Up`:
   ```bash
   cd ai-services
   docker compose ps
   ```

2. Check readiness of each service:
   ```bash
   curl http://localhost:3001/ready   # nsfw-detector
   curl http://localhost:3002/ready   # scene-analyzer
   curl http://localhost:3003/ready   # violence-detector
   ```

3. **Expected response when ready:**
   ```json
   {"status": "ready", "models_loaded": true}
   ```

   Services may also return ready with lazy loading when models are currently unloaded to save memory:
   ```json
   {"status": "ready", "models_loaded": false, "lazy_load": true}
   ```

4. **Expected response when degraded (models not loaded):**
   ```json
   {"status": "degraded", "models_loaded": false, "reason": "Model file not found at ..."}
   ```

5. Check Docker logs for errors:
   ```bash
   docker compose logs --tail=50
   ```

---

## Services Degraded (Models Not Loaded)

**Symptoms:** `/ready` returns `{"status": "degraded"}` and services return HTTP 503 for analysis requests.

**Cause:** Placeholder/random model generation has been disabled. Real model files must be provided.

**Steps:**

1. Check `ai-services/models/model-manifest.json` to see which model files are expected and at which paths.

2. Obtain real model files:
   - NSFW model files (`models/nsfw/mobilenet_v2_140_224/*`)
   - Violence profile model files (`models/violence/speed|balanced|quality/*`) or allow lazy download
   - CLIP model weights — for content-classifier (legacy/optional)

3. Place model files in the paths specified in the manifest.

4. Restart services:
   ```bash
   docker compose restart
   ```

5. Verify: `curl http://localhost:3001/ready` should now return `{"status": "ready", "models_loaded": true}`.

---

## Analysis Not Running

**Symptoms:** No segments are being created; playback filtering never triggers.

**Steps:**

1. Go to **Dashboard → Scheduled Tasks → Analyze Library for PureFin** and run it manually.

2. Check the plugin log for errors from `AnalyzeLibraryTask`:
   ```bash
   grep -i "AnalyzeLibraryTask\|PureFin\|Jellyfin.Plugin.ContentFilter" /var/log/jellyfin/*.log
   ```

3. Verify AI services are reachable (see section above).

---

## Queue Is Paused

**Symptoms:** Analysis jobs remain pending and do not progress.

**Steps:**

1. Open **Dashboard → Plugins → PureFin**.
2. In **Analysis Queue Controls (Admin)**, check status.
3. Click **Resume Queue**.
4. Recheck status and confirm active/processed counters are moving.

You can also query directly:
```bash
curl http://localhost:3002/queue/status
```

---

## Models Keep Unloading

**Symptoms:** First analysis call after inactivity is slower.

**Cause:** Idle model auto-unload is enabled by design to free resources.

**Options:**

1. Increase timeout in `ai-services/docker-compose.yml`:
   - `MODEL_IDLE_UNLOAD_SECONDS=1800` (example)
2. Disable unload entirely:
   - `MODEL_IDLE_UNLOAD_SECONDS=0`
3. Restart services after changes:
   ```bash
   docker compose up -d
   ```

---

## Filtering Not Happening During Playback

**Symptoms:** Analysis has completed but content is not being skipped during playback.

**Steps:**

1. Confirm that analysis has been run and segment files exist in the segment directory (default: `/segments/`).

2. Check the configured sensitivity level — if set to `permissive`, only very high-confidence detections are triggered (threshold 0.85).

3. Verify the relevant content categories are enabled in plugin settings (EnableNudity, EnableViolence, etc.).

4. Check the plugin log for `PlaybackMonitor` entries during playback.

---

## Getting Help

1. Check the [FAQ](./faq.md)
2. Review [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
3. Enable debug logging in Jellyfin and share the relevant log section when filing an issue

---

## Debug Logging

To enable verbose logging, add to `logging.json` in your Jellyfin config directory:
```json
{
  "Serilog": {
    "MinimumLevel": {
      "Override": {
        "Jellyfin.Plugin.ContentFilter": "Debug"
      }
    }
  }
}
```

Check AI service logs:
```bash
docker compose logs -f
```
