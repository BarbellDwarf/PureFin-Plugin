# Path Configuration Summary

## Overview

The PureFin Content Filter system requires proper path configuration so that:
1. **Jellyfin Plugin** can find media files and segments
2. **AI Services** can access the same media files for analysis
3. **Both systems** can share segment data

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Host                           │
│                                                              │
│  ┌────────────────┐              ┌────────────────┐        │
│  │ Jellyfin       │              │ AI Services    │        │
│  │ Container      │─────HTTP────►│ Container      │        │
│  │                │   (3002)     │                │        │
│  └────────┬───────┘              └────────┬───────┘        │
│           │                               │                 │
│           │ mount                         │ mount           │
│           ▼                               ▼                 │
│  ┌──────────────────────────────────────────────────┐      │
│  │           Host Filesystem                        │      │
│  │                                                  │      │
│  │  /host/media/movies/  ◄─── Media Files          │      │
│  │  /host/segments/      ◄─── Segment JSONs        │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Required Paths

### 1. Media Library Path

**What**: Location of your video files (movies, TV shows)  
**Used by**: Both Jellyfin and AI Services  
**Access**: Read-only for AI services

**Configuration:**

**Jellyfin Container:**
```bash
docker run -v /host/path/to/media:/mnt/media:ro jellyfin/jellyfin
```

**AI Services (docker-compose.yml):**
```yaml
scene-analyzer:
  volumes:
    - /host/path/to/media:/mnt/media:ro
```

**Important**: Both paths must point to the SAME host directory!

### 2. Segments Directory Path

**What**: Location of generated filter segments (JSON files)  
**Used by**: Jellyfin Plugin (reads) and optionally AI Services (writes)  
**Access**: Read-write

**Configuration:**

**Jellyfin Plugin Settings:**
```
Segment Directory: /segments
```

**Jellyfin Container Mount:**
```bash
docker run -v /host/path/to/segments:/segments:rw jellyfin/jellyfin
```

**AI Services (optional, docker-compose.yml):**
```yaml
scene-analyzer:
  volumes:
    - /host/path/to/segments:/segments:rw
```

## Platform-Specific Examples

### Windows (Docker Desktop)

**Your Setup:**
```
Host Media: D:\Movies\
Host Segments: D:\jellytestconfig\segments\
```

**Jellyfin Container:**
```bash
docker run -v D:/Movies:/mnt/media:ro \
           -v D:/jellytestconfig/segments:/segments:rw \
           jellyfin/jellyfin
```

**AI Services (.env):**
```bash
JELLYFIN_MEDIA_PATH=D:/Movies
SEGMENTS_PATH=D:/jellytestconfig/segments
```

**Jellyfin Plugin Config:**
```
AI Service Base URL: http://host.docker.internal:3002
Segment Directory: /segments
```

### Linux

**Example Setup:**
```
Host Media: /mnt/media/movies/
Host Segments: /var/lib/jellyfin/segments/
```

**Jellyfin Container:**
```bash
docker run -v /mnt/media/movies:/mnt/media:ro \
           -v /var/lib/jellyfin/segments:/segments:rw \
           jellyfin/jellyfin
```

**AI Services (.env):**
```bash
JELLYFIN_MEDIA_PATH=/mnt/media/movies
SEGMENTS_PATH=/var/lib/jellyfin/segments
```

**Jellyfin Plugin Config:**
```
AI Service Base URL: http://172.17.0.1:3002
Segment Directory: /segments
```

### Unraid

**Example Setup:**
```
Host Media: /mnt/user/media/movies/
Host Segments: /mnt/user/appdata/jellyfin/segments/
```

**Jellyfin Template:**
```xml
<Config Name="Media" Target="/mnt/media" Mode="ro" Type="Path">/mnt/user/media/movies/</Config>
<Config Name="Segments" Target="/segments" Mode="rw" Type="Path">/mnt/user/appdata/jellyfin/segments/</Config>
```

**AI Services (.env):**
```bash
JELLYFIN_MEDIA_PATH=/mnt/user/media/movies
SEGMENTS_PATH=/mnt/user/appdata/jellyfin/segments
```

**Jellyfin Plugin Config:**
```
AI Service Base URL: http://172.17.0.1:3002
Segment Directory: /segments
```

### Synology NAS

**Example Setup:**
```
Host Media: /volume1/video/
Host Segments: /volume1/docker/jellyfin/segments/
```

**Jellyfin Container:**
```bash
docker run -v /volume1/video:/mnt/media:ro \
           -v /volume1/docker/jellyfin/segments:/segments:rw \
           jellyfin/jellyfin
```

**AI Services (.env):**
```bash
JELLYFIN_MEDIA_PATH=/volume1/video
SEGMENTS_PATH=/volume1/docker/jellyfin/segments
```

## Path Verification Checklist

Use this checklist to verify your paths are configured correctly:

### Media Path
- [ ] Jellyfin can see and play videos
- [ ] AI container can access the same files
- [ ] Paths match between containers (e.g., both use `/mnt/media`)

**Test:**
```bash
# In Jellyfin container:
docker exec jellyfin ls /mnt/media/

# In AI container:
docker exec scene-analyzer ls /mnt/media/

# Should show the same files!
```

### Segments Path
- [ ] Jellyfin plugin can write segments
- [ ] Jellyfin plugin can read segments on restart
- [ ] AI services can access the directory (if configured)

**Test:**
```bash
# In Jellyfin container:
docker exec jellyfin ls /segments/

# Should show .json files like:
# 6e4e254d-8c46-9f6c-dc3c-25f2fc3e4f69.json
```

### Network Connectivity
- [ ] Jellyfin can reach AI services
- [ ] AI services return healthy status

**Test:**
```bash
# From Jellyfin container:
docker exec jellyfin curl http://host.docker.internal:3002/health

# Should return: {"status": "healthy", ...}
```

## Common Path Problems

### Problem: "File not found" when AI analyzes video

**Symptom:** Jellyfin logs show paths like `/mnt/Media/Movie.mkv` but AI service can't find it

**Cause:** Path mismatch between containers

**Solution:**
1. Check Jellyfin's media mount: `docker inspect jellyfin | grep -A 5 Mounts`
2. Verify the source path on host: `ls /host/path/to/media/`
3. Update AI services to use the SAME host source path
4. Ensure container mount points match (e.g., both use `/mnt/media`)

### Problem: Segments not loading after restart

**Symptom:** Plugin says "Loaded 0 segment files"

**Cause:** Segments directory not mounted or wrong path

**Solution:**
1. Verify plugin config: `Segment Directory: /segments`
2. Check container mount: `docker exec jellyfin ls /segments/`
3. Verify host directory exists: `ls /host/path/to/segments/`
4. Check file permissions: `ls -la /host/path/to/segments/`

### Problem: AI service can't write segments

**Symptom:** Analysis completes but no segment files created

**Cause:** Segments volume not mounted in AI container, or read-only

**Solution:**
1. Add volume to docker-compose.yml:
   ```yaml
   volumes:
     - /host/segments:/segments:rw  # note: rw not ro
   ```
2. Restart AI services: `docker-compose restart`
3. Check permissions: AI container user must have write access

## Path Best Practices

### 1. Use Absolute Paths
❌ Bad: `../media` or `~/Videos`  
✅ Good: `/mnt/media` or `D:/Movies`

### 2. Use Forward Slashes on Windows
❌ Bad: `D:\Movies`  
✅ Good: `D:/Movies`

### 3. Match Container Paths
If Jellyfin uses `/mnt/Media`, AI services should too.

### 4. Use Read-Only Where Possible
Media files: `:ro` (read-only)  
Segments: `:rw` (read-write)

### 5. Test Before Full Analysis
Analyze one movie first to verify paths work before processing your entire library.

## Quick Reference

### Path Template

```
┌────────────────┬─────────────────┬───────────────────┐
│ Host Path      │ Container Path  │ Access            │
├────────────────┼─────────────────┼───────────────────┤
│ /host/media    │ /mnt/media      │ ro (read-only)    │
│ /host/segments │ /segments       │ rw (read-write)   │
└────────────────┴─────────────────┴───────────────────┘
```

### Docker Compose Template

```yaml
services:
  scene-analyzer:
    volumes:
      # Media files (required, read-only)
      - ${JELLYFIN_MEDIA_PATH}:/mnt/media:ro
      
      # Segments (optional, read-write)
      - ${SEGMENTS_PATH}:/segments:rw
```

### Environment Variables

```bash
# .env file
JELLYFIN_MEDIA_PATH=/path/to/your/media
SEGMENTS_PATH=/path/to/your/segments
```

## Next Steps

1. ✅ Verify your Jellyfin media path
2. ✅ Configure AI services with the same path
3. ✅ Test with one video before full library analysis
4. ✅ Check logs if issues occur: `docker-compose logs -f`

For detailed setup instructions, see:
- [AI Services SETUP.md](SETUP.md)
- [Plugin Installation Guide](../docs/install.md)
