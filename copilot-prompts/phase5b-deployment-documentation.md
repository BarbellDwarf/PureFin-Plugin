# Phase 5B: Deployment & Documentation

## Overview
Define the production deployment process and comprehensive documentation to run, maintain, and extend the Jellyfin content filtering system.

## Objectives
- Reliable deployment on homelab or server
- Clear docs for installation, configuration, and troubleshooting
- Versioning and release process for plugin and services

## Deployment Steps

### Step 1: Pre-Requisites
- Jellyfin 10.8.0+
- Docker Engine 24+
- Optional: NVIDIA GPU + drivers + NVIDIA Container Toolkit

### Step 2: Deploy AI Services
```bash
git clone https://github.com/yourorg/jellyfin-content-filter-ai.git
cd jellyfin-content-filter-ai
docker compose pull
docker compose up -d
```
- Verify health endpoints: `/health`
- Confirm model downloads completed

### Step 3: Install Plugin
- Copy built DLLs to Jellyfin plugins directory:
  - Linux: `/var/lib/jellyfin/plugins/ContentFilter/`
  - Docker: bind-mount `/config/plugins/ContentFilter/`
- Restart Jellyfin

### Step 4: Configure Plugin
- Set segment directory path `/segments`
- Enable categories: nudity, immodesty, violence, profanity
- Choose sensitivity per user profile
- Configure external data sources and caching TTL

### Step 5: First Run
- Trigger “Analyze Library” task from Jellyfin dashboard
- Monitor AI service logs and resource usage
- Review initial segments via Review UI (optional)

## Operations

### Monitoring
- Expose Prometheus metrics from services
- Dashboards: Processing throughput, latency, errors
- Alerts: Service down, model load failure, drift detected

### Backups
- Backup `/segments` directory and SQLite DB nightly
- Export plugin configuration JSON

### Updates
- Semantic versioning: MAJOR.MINOR.PATCH
- Changelog per release
- Zero-downtime service update via `docker compose pull && up -d`

## Documentation Structure
```
docs/
├── install.md
├── configuration.md
├── user-guide.md
├── developer-guide.md
├── troubleshooting.md
├── faq.md
└── api/
    ├── nsfw-detector.md
    ├── scene-analyzer.md
    └── content-classifier.md
```

## Troubleshooting
- Plugin not loading: check Jellyfin logs for assembly errors
- Services failing: verify model paths and GPU drivers
- High latency: reduce model size or sampling rate, enable GPU
- Incorrect segments: adjust sensitivity, review and correct in UI

## Security Considerations
- Run services on internal network only
- Limit file system access to media and segments directories
- Keep dependencies patched and up to date

## Acceptance Criteria
- [ ] End-to-end deployment reproducible from docs
- [ ] Monitoring and alerts configured
- [ ] Backup and update procedures validated
- [ ] User and developer docs complete
