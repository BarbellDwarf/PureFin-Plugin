# AI Services Setup Guide

This guide will help you set up the PureFin Content Filter AI services that analyze your media library and generate filter segments.

## Overview

The AI services consist of three Docker containers:
- **Scene Analyzer** (port 3002): Detects scene boundaries and coordinates analysis
- **NSFW Detector** (port 3001): Identifies nudity and immodest content
- **Content Classifier** (port 3004): Classifies violence, profanity, and other categories

## Prerequisites

- Docker and Docker Compose installed
- Access to your Jellyfin media library files
- At least 4GB RAM available for Docker
- GPU recommended but not required (CPU works, just slower)

## Quick Start

### 1. Configure Paths

Copy the environment template and edit it with your paths:

```bash
cd ai-services
cp .env.example .env
nano .env  # or use your preferred editor
```

Set your media library path:

**Windows:**
```bash
JELLYFIN_MEDIA_PATH=D:/Movies
SEGMENTS_PATH=D:/jellytestconfig/segments
```

**Linux:**
```bash
JELLYFIN_MEDIA_PATH=/mnt/media/movies
SEGMENTS_PATH=/var/lib/jellyfin/segments
```

**Docker/Unraid:**
```bash
JELLYFIN_MEDIA_PATH=/mnt/user/media
SEGMENTS_PATH=/mnt/user/appdata/jellyfin/segments
```

### 2. Copy Docker Compose Template

```bash
cp docker-compose.template.yml docker-compose.yml
```

The template uses environment variables from `.env`, so no manual editing needed!

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Services

Check that all services are healthy:

```bash
docker-compose ps
```

You should see all three containers with status "Up" and "(healthy)".

Test the health endpoints:

```bash
curl http://localhost:3002/health  # Scene Analyzer
curl http://localhost:3001/health  # NSFW Detector
curl http://localhost:3004/health  # Content Classifier
```

## Path Configuration Details

### Media Path Requirements

The `JELLYFIN_MEDIA_PATH` must:
1. **Match your Jellyfin library structure**: The AI services receive paths from Jellyfin in the format `/mnt/media/Movie Name/movie.mkv`
2. **Be read-only**: Services only need to read video files for analysis
3. **Include all media types**: Point to your root media directory if you have movies, TV shows, etc.

### Segments Path (Optional)

The `SEGMENTS_PATH` allows AI services to:
- Write generated segments directly to Jellyfin's segment directory
- Read existing segments to avoid re-analyzing content
- Coordinate with the Jellyfin plugin

**Recommended Setup:**
- Set `SEGMENTS_PATH` to the same directory your Jellyfin plugin uses
- In Jellyfin plugin config, set "Segment Directory" to the same path
- This ensures segments are shared between plugin and AI services

**Example Matching Configuration:**

Docker `.env`:
```bash
SEGMENTS_PATH=/var/lib/jellyfin/segments
```

Jellyfin Plugin Settings:
```
Segment Directory: /segments
```

Then mount the host path to the container:
```yaml
volumes:
  - /var/lib/jellyfin/segments:/segments:rw
```

## Platform-Specific Guides

### Windows

1. **Media Path**: Use forward slashes, e.g., `D:/Movies` (not `D:\Movies`)
2. **WSL2**: If using Docker Desktop with WSL2, paths are accessible
3. **Hyper-V**: Ensure drive sharing is enabled in Docker Desktop settings

Example `.env`:
```bash
JELLYFIN_MEDIA_PATH=D:/Movies
SEGMENTS_PATH=D:/ProgramData/Jellyfin/Server/segments
```

### Linux

1. **Permissions**: Ensure Docker can read the media directory
2. **SELinux**: May need to add `:z` to volume mounts if enforcing

Example `.env`:
```bash
JELLYFIN_MEDIA_PATH=/mnt/media
SEGMENTS_PATH=/var/lib/jellyfin/plugins/segments
```

### Unraid

1. **Paths**: Use Unraid's standard mount points like `/mnt/user/`
2. **AppData**: Segments typically go in `/mnt/user/appdata/jellyfin/`
3. **Community Apps**: Can be added to Unraid's Docker templates

Example `.env`:
```bash
JELLYFIN_MEDIA_PATH=/mnt/user/media/movies
SEGMENTS_PATH=/mnt/user/appdata/jellyfin/segments
```

### Synology NAS

1. **Paths**: Use `/volume1/` or your volume number
2. **Docker Package**: Install from Package Center first
3. **Permissions**: May need to adjust folder permissions

Example `.env`:
```bash
JELLYFIN_MEDIA_PATH=/volume1/video
SEGMENTS_PATH=/volume1/docker/jellyfin/segments
```

## Updating Services

To update the AI services to a new version:

```bash
cd ai-services
git pull  # if using git
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Services won't start
```bash
docker-compose logs scene-analyzer
docker-compose logs nsfw-detector
docker-compose logs content-classifier
```

### "File not found" errors
- Verify your `JELLYFIN_MEDIA_PATH` is correct
- Check that paths in `.env` use forward slashes `/` not backslashes `\`
- Ensure the media directory is readable by Docker

### Connection refused from Jellyfin
- Jellyfin plugin must use `host.docker.internal:3002` (Windows/Mac) or `172.17.0.1:3002` (Linux)
- Or put Jellyfin in the same Docker network: `content-filter-network`

### Slow performance
- GPU acceleration: Install nvidia-docker2 for CUDA support
- Reduce video quality: AI can analyze lower resolutions
- Adjust FFmpeg parameters in scene-analyzer settings

## Advanced Configuration

### Custom Docker Network

To allow Jellyfin container to communicate directly:

```yaml
networks:
  content-filter-network:
    external: true
    name: jellyfin_network
```

Then in Jellyfin plugin config:
```
AI Service Base URL: http://scene-analyzer:3000
```

### GPU Acceleration

For NVIDIA GPUs, modify docker-compose.yml:

```yaml
scene-analyzer:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Custom Models

Place custom AI models in the `models/` directory and they'll be mounted to `/app/models` in containers.

## Port Reference

- **3001**: NSFW Detector API
- **3002**: Scene Analyzer API (main entry point for Jellyfin plugin)
- **3004**: Content Classifier API

Configure Jellyfin plugin to connect to: `http://host.docker.internal:3002`

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review health status: `docker-compose ps`
- See main project README for additional troubleshooting
