# Troubleshooting Guide

## Common Issues

### Plugin Not Loading

**Symptoms**: Plugin doesn't appear in Jellyfin dashboard after installation.

**Solutions**:
1. Check Jellyfin logs for assembly errors:
   ```bash
   journalctl -u jellyfin -n 100 | grep -i error
   ```

2. Verify plugin DLL is in correct location:
   ```bash
   ls -la /var/lib/jellyfin/plugins/ContentFilter/
   ```

3. Ensure correct .NET version (8.0) is installed

4. Restart Jellyfin server completely

### AI Services Failing

**Symptoms**: Services won't start or health checks fail.

**Solutions**:
1. Check Docker container status:
   ```bash
   docker compose ps
   docker compose logs
   ```

2. Verify model paths exist:
   ```bash
   ls -la ai-services/models/
   ```

3. Check GPU drivers (if using GPU):
   ```bash
   nvidia-smi
   ```

4. Rebuild containers:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

### High Latency

**Symptoms**: Content analysis is very slow.

**Solutions**:
1. Enable GPU acceleration in docker-compose.yml
2. Reduce model size or sampling rate
3. Adjust scene detection threshold (higher = fewer scenes)
4. Limit concurrent analysis jobs

### Incorrect Segments

**Symptoms**: Content is filtered incorrectly or not filtered when it should be.

**Solutions**:
1. Adjust sensitivity level in plugin configuration
2. Review and correct segments manually
3. Provide feedback for AI model improvement
4. Check confidence thresholds

### Database Locked

**Symptoms**: Database locked errors in logs.

**Solutions**:
1. Ensure WAL mode is enabled:
   ```bash
   sqlite3 content_filter.db "PRAGMA journal_mode=WAL;"
   ```

2. Check file permissions:
   ```bash
   ls -la /var/lib/jellyfin/data/
   ```

3. Reduce concurrent database access

### Permission Denied

**Symptoms**: Can't write to segment directory or plugin directory.

**Solutions**:
1. Check directory ownership:
   ```bash
   sudo chown -R jellyfin:jellyfin /segments
   ```

2. Verify directory permissions:
   ```bash
   sudo chmod 755 /segments
   ```

3. Check SELinux/AppArmor policies if applicable

## Getting Help

1. Check [FAQ](./faq.md)
2. Review [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
3. Join community discussions
4. Enable debug logging for more details

## Debug Logging

Enable debug logging in plugin configuration:
```json
{
  "LogLevel": "Debug"
}
```

Check logs:
```bash
# Jellyfin logs
journalctl -u jellyfin -f

# AI service logs
docker compose logs -f

# Plugin-specific logs
grep "ContentFilter" /var/log/jellyfin/*.log
```
