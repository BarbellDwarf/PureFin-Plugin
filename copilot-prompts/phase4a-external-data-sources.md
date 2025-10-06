# Phase 4A: External Data Sources Integration

## Overview
Integrate community-curated segment data (e.g., MovieContentFilter) and other potential sources into the system, normalize formats, and merge with AI-generated segments.

## Objectives
- Fetch and cache community segment data
- Normalize formats to local schema
- Merge community and AI segments with deterministic rules

## Tasks

### Task 1: Source Connectors
**Duration**: 1-2 days
**Priority**: Critical

#### Subtasks:
1. **MovieContentFilter Client**
   ```python
   class MovieContentFilterClient:
       def __init__(self, base_url):
           self.base_url = base_url

       def fetch_segments(self, title, year=None, imdb_id=None, hash=None):
           # Implement title/year lookup and metadata matching
           pass
   ```

2. **Local File Importer**
   - Support importing JSON/YAML from local directories
   - Validate format and schema

3. **Caching Layer**
   - Cache fetched results with TTL
   - Invalidate on plugin upgrade or manual purge

#### Acceptance Criteria:
- [ ] Community data fetched for known titles
- [ ] Local imports supported
- [ ] Cache reduces repeated lookups

### Task 2: Normalization Pipeline
**Duration**: 1 day
**Priority**: High

#### Subtasks:
1. **Schema Mapping**
   - Map external fields to internal: start/end, categories, actions, source

2. **Category Translation**
   - Translate external category names to internal taxonomy
   - Handle unknown categories gracefully

3. **Validation**
   - Ensure non-overlapping, ordered segments
   - Fix or flag invalid timestamps

#### Acceptance Criteria:
- [ ] All external formats mapped correctly
- [ ] Invalid records rejected with logs
- [ ] Normalized output conforms to schema

### Task 3: Merge Engine
**Duration**: 1-2 days
**Priority**: Critical

#### Subtasks:
1. **Priority Rules**
   - Prefer community segments when overlap with AI
   - Fill gaps with AI segments

2. **Conflict Resolution**
   - Overlap with differing actions: choose stricter action (skip over mute)
   - Merge adjacent segments with same categories and small gap (<300ms)

3. **Provenance & Versioning**
   - Preserve `source` and external IDs
   - Track version and timestamps

#### Acceptance Criteria:
- [ ] Deterministic merge outputs
- [ ] Conflicts resolved by rules
- [ ] Provenance retained

## Deliverables
- Source connectors and caching layer
- Normalization and validation utilities
- Merge engine with unit tests

## Testing
- Integration tests with sample community datasets
- Edge-case tests (overlaps, gaps, invalid data)
- Performance tests for batch imports