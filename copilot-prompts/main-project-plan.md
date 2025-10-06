# Jellyfin Content Filter Project - Master Plan

## Project Overview

This project implements a comprehensive content filtering system for Jellyfin that can automatically detect and filter objectionable content including nudity, immodesty, violence, and profanity using self-hosted AI models and community-curated data.

## Architecture Components

### 1. Core Components
- **Jellyfin Content Filter Plugin** - Custom .NET plugin for playback control
- **AI Analysis Engine** - Containerized Python services for content detection
- **Segment Data Management** - JSON-based storage system for filter timestamps
- **External Data Integration** - MovieContentFilter API compatibility

### 2. Technology Stack
- **Backend**: .NET 6.0+ for Jellyfin plugin development
- **AI/ML**: Python 3.9+, TensorFlow/PyTorch, OpenCV
- **Containerization**: Docker & Docker Compose
- **Database**: SQLite for segment storage
- **Media Processing**: FFmpeg for scene detection and frame extraction

## Development Phases

### Phase 1: Foundation Setup
**Duration**: 2-3 weeks
**Deliverables**:
- Development environment setup
- Basic plugin structure
- AI service containerization
- Initial Docker configuration

**Sub-plans**:
- [Phase 1A: Plugin Development Environment](./phase1a-plugin-dev-setup.md)
- [Phase 1B: AI Service Infrastructure](./phase1b-ai-service-setup.md)

### Phase 2: AI Content Analysis Implementation
**Duration**: 4-5 weeks
**Deliverables**:
- Multi-model detection pipeline
- Scene analysis workflow
- Content classification system
- Performance optimization

**Sub-plans**:
- [Phase 2A: AI Model Integration](./phase2a-ai-model-integration.md)
- [Phase 2B: Content Detection Pipeline](./phase2b-content-detection-pipeline.md)
- [Phase 2C: Scene Analysis Workflow](./phase2c-scene-analysis-workflow.md)

### Phase 3: Jellyfin Plugin Integration
**Duration**: 3-4 weeks
**Deliverables**:
- Plugin core functionality
- Database integration
- Playback hooks
- Configuration interface

**Sub-plans**:
- [Phase 3A: Plugin Core Development](./phase3a-plugin-core-development.md)
- [Phase 3B: Database Integration](./phase3b-database-integration.md)
- [Phase 3C: Playback Integration](./phase3c-playback-integration.md)

### Phase 4: External Data Integration
**Duration**: 2-3 weeks
**Deliverables**:
- MovieContentFilter API client
- Data merging logic
- Quality control system
- User feedback mechanism

**Sub-plans**:
- [Phase 4A: External Data Sources](./phase4a-external-data-sources.md)
- [Phase 4B: Data Validation System](./phase4b-data-validation-system.md)

### Phase 5: Testing & Deployment
**Duration**: 2-3 weeks
**Deliverables**:
- Comprehensive testing suite
- Performance benchmarks
- Documentation
- Production deployment guide

**Sub-plans**:
- [Phase 5A: Testing Strategy](./phase5a-testing-strategy.md)
- [Phase 5B: Deployment & Documentation](./phase5b-deployment-documentation.md)

## Success Criteria

### Technical Requirements
- [ ] Plugin successfully integrates with Jellyfin server
- [ ] AI models achieve >85% accuracy for content detection
- [ ] System processes 1080p video at minimum 2x real-time speed
- [ ] Memory usage stays under 2GB during analysis
- [ ] Support for major video formats (MP4, MKV, AVI)

### Functional Requirements
- [ ] Real-time filtering during playback
- [ ] User-configurable filter categories and sensitivity
- [ ] Integration with existing Jellyfin user management
- [ ] Support for both AI-generated and community segments
- [ ] Manual override capabilities for specific content

### Performance Requirements
- [ ] Startup time under 30 seconds
- [ ] Filter application latency under 500ms
- [ ] Support for concurrent multi-user filtering
- [ ] Graceful degradation when AI services unavailable

## Risk Assessment

### High Risk
- **AI Model Accuracy**: False positives/negatives affecting user experience
  - *Mitigation*: Multi-model validation, user feedback loops
- **Performance Impact**: Resource-intensive AI processing
  - *Mitigation*: Optimized models, smart caching, progressive analysis

### Medium Risk
- **Jellyfin API Changes**: Breaking changes in future versions
  - *Mitigation*: Regular compatibility testing, modular architecture
- **Legal/Copyright Concerns**: Content modification implications
  - *Mitigation*: Clear user consent, documentation of ownership requirements

### Low Risk
- **Community Data Availability**: MovieContentFilter API reliability
  - *Mitigation*: Local caching, fallback to AI-only mode

## Resource Requirements

### Development Environment
- **Hardware**: Minimum 16GB RAM, GPU recommended for AI training/testing
- **Software**: Visual Studio/VS Code, Docker Desktop, Python 3.9+
- **Services**: GitHub repository, Docker Hub account

### Production Deployment
- **Server**: 8GB+ RAM, 100GB+ storage, optional GPU
- **Network**: Stable internet for model downloads and updates
- **Jellyfin**: Version 10.8.0 or higher

## Timeline Estimate

**Total Duration**: 14-18 weeks (3.5-4.5 months)

```
Weeks 1-3:   Phase 1 - Foundation Setup
Weeks 4-8:   Phase 2 - AI Implementation
Weeks 9-12:  Phase 3 - Plugin Integration
Weeks 13-15: Phase 4 - External Data
Weeks 16-18: Phase 5 - Testing & Deployment
```

## Next Steps

1. Review and approve this master plan
2. Set up development environment following Phase 1A guidelines
3. Begin work on plugin template setup
4. Research and select optimal AI models for content detection
5. Establish regular progress review schedule (weekly standups recommended)

## References

- [Jellyfin Plugin Documentation](https://jellyfin.org/docs/general/server/plugins/)
- [MovieContentFilter GitHub](https://github.com/delight-im/MovieContentFilter)
- [NSFW.js Documentation](https://github.com/infinitered/nsfwjs)
- [FFmpeg Scene Detection](https://ffmpeg.org/ffmpeg-filters.html#scene)