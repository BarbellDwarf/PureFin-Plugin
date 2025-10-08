# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added
- Initial release of PureFin Content Filter Plugin
- AI-powered content detection for nudity, immodesty, violence, and profanity
- Three AI microservices:
  - NSFW Detector: Nudity and adult content detection
  - Scene Analyzer: Video scene detection and segmentation
  - Content Classifier: Multi-category content classification
- Jellyfin plugin with configuration UI
- Real-time playback monitoring and filtering
- Automatic skip/mute actions during playback
- Configurable sensitivity levels (strict, moderate, permissive)
- Per-user filtering preferences
- Scheduled library analysis task
- In-memory segment caching with JSON file persistence
- Comprehensive documentation:
  - Installation guide
  - Configuration guide
  - User guide
  - Developer guide
  - API documentation
  - FAQ
  - Troubleshooting guide
- Docker Compose orchestration for AI services
- Prometheus metrics for monitoring
- Health check endpoints for all services

### Technical Details
- .NET 8.0 plugin for Jellyfin 10.8.0+
- Python 3.11 AI services with Flask
- TensorFlow for model inference
- FFmpeg for video processing
- Docker containerization
- JSON-based segment storage

### Known Limitations
- AI models use mock predictions (pending real model integration)
- No database integration (using JSON files for persistence)
- Limited client support for mute actions
- Manual segment editing not yet implemented
- Community data integration not yet implemented

## [Unreleased]

### Planned Features
- Real AI model integration (NSFW.js, custom models)
- MovieContentFilter API integration
- SQLite database for better performance
- Manual segment editing UI
- Improved accuracy with real models
- Audio profanity detection with Whisper
- Batch processing improvements
- Advanced filtering options
- Statistics and reporting
- Import/export segment data
- Multi-language support

### Planned Improvements
- Enhanced playback monitoring with event subscriptions
- Better client compatibility
- Performance optimizations
- Automated testing suite
- CI/CD pipeline
- Model management and updates
- Confidence calibration
- False positive/negative reporting

## Version History

### Pre-releases

Development versions and planning documents created during project inception.

## Support

For issues, questions, or contributions, please visit:
- [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
- [Documentation](docs/)

## License

See LICENSE file for details.
