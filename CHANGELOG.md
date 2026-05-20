# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Upgraded plugin project and tests to `net9.0` with Jellyfin package version `10.11.8`
- Updated plugin compatibility metadata to `targetAbi 10.11.0.0`
- Renamed user-facing plugin/task/category text to **PureFin**
- Added admin segment inspection page and API (`PureFin Segments`)
- Updated scene detection defaults and UI messaging to prefer TransNetV2 variable scene detection
- Added scene-analyzer queue controls with pause/resume/status endpoints and Jellyfin admin UI controls
- Added idle model auto-unload + lazy-load behavior for AI services to reduce steady-state resource usage

### Fixed
- Corrected documentation references that still pointed to `net8.0`, Jellyfin `10.9`, old task names, and old plugin naming
- Aligned CI/release workflow .NET SDK versions and artifact paths with current `net9.0` build output

## [1.0.1.0] - 2025-01-01
### Fixed
- Plugin DI registration: implemented `IPluginServiceRegistrator` so plugin services now start correctly in Jellyfin
- Upgraded target framework from `net6.0` to `net8.0` to match Jellyfin's requirements
- Added `ExcludeAssets=runtime` to Jellyfin package references to prevent runtime conflicts

### Added
- Sensitivity threshold presets (Low/Medium/High) wired to actual score thresholds
- `/ready` endpoint on all AI services distinguishing model-loaded state from service-alive
- `model-manifest.json` schema for versioned model declarations
- `schemas/analysis-response.json` for stable versioned API responses
- GitHub Actions CI (`build.yml`, `release.yml`) for automated builds and releases
- Plugin repository manifest publishing via gh-pages
- Versioning policy documentation
- Rollout and operations guide

### Changed
- `mute` action now explicitly falls back to `skip` with a log warning (was a silent no-op)
- `PreferCommunityData` now logs a warning when set (was silently ignored)
- AI services now return HTTP 503 instead of random/placeholder predictions when models not loaded
- docker-compose.yml added to repo (was only a template)
- Port reference docs corrected: scene-analyzer=3002, nsfw-detector=3001, content-classifier=3004

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
- Scheduled library analysis task
- In-memory segment caching with JSON file persistence
- Docker Compose orchestration for AI services
- Health check endpoints for all services

### Technical Details
- .NET 8.0 plugin for Jellyfin 10.9.0+
- Python 3.11 AI services with Flask
- TensorFlow for model inference
- FFmpeg for video processing
- Docker containerization
- JSON-based segment storage

### Known Limitations
- AI models require real model files (placeholder/random model generation is disabled)
- No database integration (using JSON files for persistence)
- Limited client support for mute actions
- Manual segment editing not yet implemented
- Community data integration not yet implemented

## Support

For issues, questions, or contributions, please visit:
- [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
- [Documentation](docs/)

## License

See LICENSE file for details.

