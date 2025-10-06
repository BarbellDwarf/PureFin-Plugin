# PureFin Content Filter Plugin

AI-powered content filtering for Jellyfin media server. Automatically detect and filter objectionable content including nudity, immodesty, violence, and profanity.

## Features

- 🤖 **AI-Powered Detection**: Uses machine learning models to analyze video content
- 🎯 **Multi-Category Filtering**: Filter nudity, immodesty, violence, and profanity
- ⚙️ **Configurable Sensitivity**: Choose strict, moderate, or permissive filtering levels
- 👥 **Per-User Profiles**: Different filtering preferences for each user
- 🌐 **Community Data**: Leverage manually-curated segment data from the community
- ⚡ **Real-Time Filtering**: Automatic skip/mute during playback
- 🔧 **Manual Overrides**: Edit or disable filtering for specific media items

## Quick Start

### Prerequisites

- Jellyfin 10.8.0+
- Docker Engine 24+
- 8GB+ RAM (16GB recommended)

### Installation

1. **Deploy AI Services**:
```bash
cd ai-services
docker compose up -d
```

2. **Install Plugin**:
```bash
cd Jellyfin.Plugin.ContentFilter
dotnet build --configuration Release
# Copy DLL to Jellyfin plugins directory
```

3. **Configure & Run**:
- Access Jellyfin Dashboard → Plugins → Content Filter
- Configure your preferences
- Run "Analyze Library" task

## Documentation

- [Installation Guide](docs/install.md)
- [Configuration Guide](docs/configuration.md)
- [User Guide](docs/user-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [API Documentation](docs/api/)

## Architecture

### Components

- **Jellyfin Plugin**: .NET plugin for Jellyfin integration
- **AI Services**: Containerized Python services for content analysis
  - NSFW Detector: Nudity and adult content detection
  - Scene Analyzer: Video scene detection and segmentation
  - Content Classifier: Multi-category content classification
- **Segment Storage**: JSON-based storage for filter timestamps

### Technology Stack

- **Plugin**: .NET 8.0, C#
- **AI Services**: Python 3.11, TensorFlow, OpenCV, FFmpeg
- **Deployment**: Docker Compose
- **Storage**: SQLite, JSON files

## Development

See [copilot-prompts/main-project-plan.md](copilot-prompts/main-project-plan.md) for detailed development phases and plans.

### Project Structure

```
PureFin-Plugin/
├── Jellyfin.Plugin.ContentFilter/  # Main plugin code
│   ├── Configuration/              # Plugin configuration
│   ├── Web/                        # Web UI
│   └── Plugin.cs                   # Main plugin class
├── ai-services/                    # AI service containers
│   ├── services/
│   │   ├── nsfw-detector/         # NSFW detection service
│   │   ├── scene-analyzer/        # Scene analysis service
│   │   └── content-classifier/    # Content classification service
│   └── docker-compose.yml
├── docs/                           # Documentation
└── copilot-prompts/               # Development planning documents
```

## Contributing

Contributions are welcome! Please read the contributing guidelines and development documentation.

## License

See LICENSE file for details.

## Acknowledgments

- [Jellyfin](https://jellyfin.org/) - Free Software Media System
- [MovieContentFilter](https://github.com/delight-im/MovieContentFilter) - Community segment data
- [NSFW.js](https://github.com/infinitered/nsfwjs) - NSFW detection models
- [FFmpeg](https://ffmpeg.org/) - Video processing

## Support

- [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
- [Documentation](docs/)
- Community forums

## Disclaimer

This plugin is provided as-is for content filtering purposes. Users are responsible for compliance with applicable laws and terms of service. The accuracy of AI-powered content detection may vary.
