# Installation Guide

## Prerequisites

- **Jellyfin Server**: Version 10.8.0 or higher
- **Docker Engine**: Version 24.0 or higher
- **System Requirements**:
  - 8GB+ RAM (16GB recommended)
  - 100GB+ free disk space
  - Optional: NVIDIA GPU with drivers + NVIDIA Container Toolkit for GPU acceleration

## Installation Steps

### Step 1: Deploy AI Services

1. Clone the repository:
```bash
git clone https://github.com/BarbellDwarf/PureFin-Plugin.git
cd PureFin-Plugin/ai-services
```

2. Start the services using Docker Compose:
```bash
docker compose up -d
```

3. Verify services are running:
```bash
docker compose ps
```

4. Check health endpoints:
```bash
curl http://localhost:3001/health  # NSFW Detector
curl http://localhost:3002/health  # Scene Analyzer
curl http://localhost:3003/health  # Content Classifier
```

### Step 2: Install Jellyfin Plugin

1. Build the plugin:
```bash
cd ../Jellyfin.Plugin.ContentFilter
dotnet build --configuration Release
```

2. Copy the plugin DLL to your Jellyfin plugins directory:

**Linux:**
```bash
sudo mkdir -p /var/lib/jellyfin/plugins/ContentFilter
sudo cp bin/Release/net8.0/Jellyfin.Plugin.ContentFilter.dll /var/lib/jellyfin/plugins/ContentFilter/
```

**Docker (modify your docker-compose.yml):**
```yaml
volumes:
  - ./plugins:/config/plugins
```

Then copy:
```bash
mkdir -p ./plugins/ContentFilter
cp bin/Release/net8.0/Jellyfin.Plugin.ContentFilter.dll ./plugins/ContentFilter/
```

**Windows:**
```powershell
Copy-Item bin\Release\net8.0\Jellyfin.Plugin.ContentFilter.dll "C:\ProgramData\Jellyfin\Server\plugins\ContentFilter\"
```

3. Restart Jellyfin

### Step 3: Configure Plugin

1. Access Jellyfin web interface
2. Navigate to **Dashboard** → **Plugins** → **Content Filter**
3. Configure settings and save

### Step 4: First Run

1. From Jellyfin Dashboard, navigate to **Scheduled Tasks**
2. Find "Analyze Library for Content Filter" task
3. Click **Run** to start initial analysis

## See Also

- [Configuration Guide](./configuration.md)
- [User Guide](./user-guide.md)
- [Troubleshooting](./troubleshooting.md)
