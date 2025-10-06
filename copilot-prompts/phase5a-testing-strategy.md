# Phase 5A: Testing Strategy

## Overview
Establish a comprehensive testing strategy covering unit, integration, system, and performance testing for AI services, the content pipeline, and the Jellyfin plugin.

## Objectives
- Validate correctness, robustness, and performance
- Prevent regressions through automated CI
- Ensure accurate and low-latency filtering during playback

## Test Suites

### 1. Unit Tests
- Model loaders and preprocessors
- Scene detection parsing and timestamp math
- Segment merge rules and conflict resolution
- Repository queries and caching behavior
- Sensitivity thresholds and action mapping

### 2. Integration Tests
- AI service APIs (analyze image/video/audio)
- End-to-end pipeline: media file -> segments JSON
- Plugin ingestion of segment files
- Playback event handling and boundary detection

### 3. System Tests
- Multi-user playback with concurrent filtering
- Failure scenarios (service down, timeouts, missing files)
- Data drift and anomaly triggers

### 4. Performance Tests
- Throughput on 1080p/4K samples (CPU vs GPU)
- Latency of boundary detection and action dispatch
- Memory/CPU usage under load

## Tooling
- xUnit/NUnit for .NET plugin
- PyTest for Python AI services
- Locust or k6 for load testing APIs
- Prometheus + Grafana for metrics

## Example Tests

### C#: Segment Lookup
```csharp
[Fact]
public async Task GetActiveSegments_Returns_Correct_Segment()
{
    var repo = new SegmentRepository(...);
    await repo.UpsertSegments("media1", new[]
    {
        new Segment(10.0, 20.0, new[]{"immodesty"}, "skip", 0.9)
    });

    var active = await repo.GetActiveSegments("media1", 15.0);
    Assert.Single(active);
    Assert.Equal("skip", active.First().Action);
}
```

### Python: Scene Detection
```python
def test_ffmpeg_scene_parse():
    log = open('tests/data/scenes.log').read()
    timestamps = parse_showinfo(log)
    assert timestamps[0] == pytest.approx(12.345, abs=0.05)
```

## CI/CD
- GitHub Actions workflows:
  - Build and test .NET plugin
  - Build and test Python services
  - Linting and static analysis
  - Docker image build and push on tags

## Acceptance Criteria
- [ ] >90% unit test coverage for critical paths
- [ ] All integration tests green
- [ ] Performance targets met in benchmarks
- [ ] CI passing on main branch

## Reporting
- Generate HTML coverage reports
- Publish performance dashboards
- Weekly test summary in CI artifacts