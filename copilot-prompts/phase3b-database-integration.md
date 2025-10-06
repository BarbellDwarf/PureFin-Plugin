# Phase 3B: Database Integration

## Overview
Design and implement a lightweight, efficient storage layer for segment data, linking Jellyfin media items to their associated filtering segments, and enabling fast lookups during playback.

## Objectives
- Store and retrieve segment data efficiently
- Support provenance, confidence scoring, and versioning
- Provide indexes for fast time-based lookups

## Schema Design

### Tables
1. **media_items**
   - `id` (PK) - Jellyfin media ID
   - `hash` - Media file hash for change detection
   - `duration` - Video duration (seconds)
   - `updated_at` - Last update timestamp

2. **segments**
   - `id` (PK)
   - `media_id` (FK -> media_items.id)
   - `start` (REAL)
   - `end` (REAL)
   - `action` (TEXT) - skip, mute, blur
   - `confidence` (REAL)
   - `source` (TEXT) - ai, community, manual
   - `version` (INTEGER)

3. **segment_categories**
   - `segment_id` (FK -> segments.id)
   - `category` (TEXT) - nudity, immodesty, violence, profanity
   - Composite PK (segment_id, category)

4. **indexes**
   - `idx_segments_media_time` on (media_id, start, end)
   - `idx_segments_source` on source

## Tasks

### Task 1: Storage Engine Setup
**Duration**: 1 day
**Priority**: Critical

#### Subtasks:
1. **SQLite Initialization**
   ```csharp
   using var connection = new SqliteConnection("Data Source=content_filter.db");
   connection.Open();
   new SqliteCommand("PRAGMA journal_mode=WAL;", connection).ExecuteNonQuery();
   ```

2. **Migrations**
   - Implement schema migrations with versioning
   - Create initial schema and seed data

3. **Data Access Layer**
   ```csharp
   public class SegmentRepository
   {
       public Task UpsertMediaItem(MediaItem item);
       public Task UpsertSegments(string mediaId, IEnumerable<Segment> segments);
       public Task<IReadOnlyList<Segment>> GetSegments(string mediaId);
       public Task<IReadOnlyList<Segment>> GetActiveSegments(string mediaId, double timestamp);
   }
   ```

#### Acceptance Criteria:
- [ ] Database file created and schema applied
- [ ] WAL mode enabled for concurrency
- [ ] Repository methods tested

### Task 2: Segment Lookup Optimization
**Duration**: 1 day
**Priority**: High

#### Subtasks:
1. **Time Range Queries**
   ```sql
   SELECT * FROM segments 
   WHERE media_id = @mediaId 
     AND start <= @timestamp AND end >= @timestamp
   ORDER BY start ASC;
   ```

2. **In-Memory Cache**
   - Cache per-media segments on first access
   - Use LRU eviction for memory efficiency

3. **Hot Path Optimization**
   - Precompute next action boundary for active playback sessions

#### Acceptance Criteria:
- [ ] Time-based lookups < 5ms avg
- [ ] Cache hit ratio > 90% during playback
- [ ] Minimal memory footprint (< 200MB)

### Task 3: Import/Export & Versioning
**Duration**: 1 day
**Priority**: Medium

#### Subtasks:
1. **JSON Import**
   - Parse segment files and normalize
   - Validate schema and timestamps

2. **JSON Export**
   - Export per-media segments for backup or sharing

3. **Versioning**
   - Track segment version and media hash
   - Invalidate older versions on media change

#### Acceptance Criteria:
- [ ] Import/export round-trip safe
- [ ] Version conflicts resolved deterministically
- [ ] Backward compatibility maintained

## Deliverables
- SQLite database file and schema migrations
- Repository and caching layer
- Import/export utilities with validation

## Testing
- Unit tests for repository methods
- Integration tests for import/export
- Performance tests for lookup latency