# Phase 3A: Plugin Core Development

## Overview
Build the core Jellyfin plugin responsible for managing configuration, triggering analysis, consuming segment files, and applying filtering actions during playback.

## Objectives
- Provide admin UI for configuring categories, sensitivity, and sources
- Implement scheduled tasks to analyze and refresh segment data
- Apply skip/mute actions based on segments during playback

## Tasks

### Task 1: Plugin Skeleton & Configuration
**Duration**: 1-2 days
**Priority**: Critical

#### Subtasks:
1. **Base Plugin Class**
   ```csharp
   public class ContentFilterPlugin : BasePlugin<PluginConfiguration>, IHasWebPages
   {
       public override string Name => "Content Filter";
       public override Guid Id => new Guid("REPLACE-WITH-YOUR-GUID");
       public IEnumerable<PluginPageInfo> GetPages() => new[]
       {
           new PluginPageInfo
           {
               Name = "contentfilter-config",
               EmbeddedResourcePath = GetType().Namespace + ".Web.config.html"
           }
       };
   }
   ```

2. **Configuration Model**
   ```csharp
   public class PluginConfiguration : BasePluginConfiguration
   {
       public bool EnableNudity { get; set; } = true;
       public bool EnableImmodesty { get; set; } = true;
       public bool EnableViolence { get; set; } = true;
       public bool EnableProfanity { get; set; } = true;
       public string Sensitivity { get; set; } = "moderate";
       public string SegmentDirectory { get; set; } = "/segments";
       public bool PreferCommunityData { get; set; } = true;
   }
   ```

3. **Admin UI**
   - Build configuration page with toggles and thresholds
   - Configure path to segment files and external API endpoints

#### Acceptance Criteria:
- [ ] Plugin loads and exposes configuration UI
- [ ] Settings persist across restarts
- [ ] Segment directory configurable

### Task 2: Library Scan & Analysis Triggers
**Duration**: 2-3 days
**Priority**: High

#### Subtasks:
1. **Post-Scan Hook**
   ```csharp
   public class PostScanTask : ILibraryPostScanTask
   {
       public async Task Run(IProgress<double> progress, CancellationToken cancellationToken)
       {
           // Enumerate media items and enqueue analysis jobs
       }
   }
   ```

2. **Scheduled Analysis Task**
   ```csharp
   public class AnalysisScheduledTask : IScheduledTask
   {
       public async Task Execute(CancellationToken cancellationToken, IProgress<double> progress)
       {
           // Trigger AI service API for new/changed media items
       }
       public IEnumerable<TaskTriggerInfo> GetDefaultTriggers() => new[]
       {
           new TaskTriggerInfo { Type = TaskTriggerInfo.TriggerHourly, TimeOfDayTicks = TimeSpan.FromHours(6).Ticks }
       };
   }
   ```

3. **Change Detection**
   - Hash media file; compare with last processed hash
   - Recompute segments on change

#### Acceptance Criteria:
- [ ] New media automatically queued for analysis
- [ ] Re-analysis on media changes
- [ ] Progress visible in Jellyfin tasks

### Task 3: Segment Ingestion & Indexing
**Duration**: 1-2 days
**Priority**: Critical

#### Subtasks:
1. **Segment Loader**
   ```csharp
   public class SegmentStore
   {
       private readonly ConcurrentDictionary<string, SegmentData> _segments = new();
       public SegmentData? Get(string mediaId) => _segments.TryGetValue(mediaId, out var s) ? s : null;
       public void Put(string mediaId, SegmentData data) => _segments[mediaId] = data;
   }
   ```

2. **Schema Models**
   ```csharp
   public record Segment(double Start, double End, string[] Categories, string Action, double Confidence);
   public record SegmentData(string MediaId, int Version, IReadOnlyList<Segment> Segments);
   ```

3. **File Watcher**
   - Watch segment directory for changes
   - Hot-reload updated segment files

#### Acceptance Criteria:
- [ ] Segment files loaded and indexed on startup
- [ ] Hot-reload works on file changes
- [ ] Efficient lookup by media ID

### Task 4: Playback Filtering Hooks
**Duration**: 3-4 days
**Priority**: Critical

#### Subtasks:
1. **Session Monitor**
   - Subscribe to playback events (start/seek/pause/stop)
   - Track current timestamp per session

2. **Action Dispatcher**
   - On timestamp entering a segment: execute action (skip/mute)
   - On leaving segment: restore state

3. **Client Signaling**
   - Use Jellyfin session API to send skip commands
   - For mute: adjust audio stream volume when supported

4. **Fallback Strategy**
   - If direct mute not supported: prebuffer seek to segment end (skip)

#### Acceptance Criteria:
- [ ] Skip actions trigger reliably at segment boundaries
- [ ] Mute actions apply for profanity micro-segments
- [ ] Works across web and supported clients

### Task 5: User Profiles & Overrides
**Duration**: 1-2 days
**Priority**: Medium

#### Subtasks:
1. **Per-User Settings**
   - Map Jellyfin users to sensitivity profiles
   - Allow opt-in/out per category

2. **Media Overrides**
   - Per-item overrides to adjust or disable filters

3. **Audit & Logs**
   - Log actions per session for debugging

#### Acceptance Criteria:
- [ ] Per-user filtering behavior
- [ ] Per-media overrides saved and applied
- [ ] Action logs accessible for troubleshooting

## Deliverables
- Plugin project with configuration UI
- Tasks for analysis triggers and indexing
- Playback action dispatcher and session hooks
- User settings and override mechanisms

## Dependencies
- Phase 2B: Segment file generation
- Jellyfin API access for sessions and playback control

## Testing
- Unit tests for segment ingestion and action dispatch
- Integration tests in local Jellyfin instance
- Manual playback tests for skip/mute timing precision