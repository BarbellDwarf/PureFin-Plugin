# Phase 4B: Data Validation & Quality Control

## Overview
Design systems and processes to ensure the accuracy, reliability, and safety of segment data from both AI and community sources, with human-in-the-loop review where needed.

## Objectives
- Validate timestamps and category assignments
- Quantify confidence and detect anomalies
- Provide review workflows and feedback loops

## Tasks

### Task 1: Schema & Timestamp Validation
**Duration**: 1 day
**Priority**: Critical

#### Subtasks:
1. **Schema Validator**
   - JSON schema for segments
   - Enforce numeric start/end, ordering, and non-negative durations

2. **Timestamp Sanity Checks**
   - Ensure `0 <= start < end <= media.duration`
   - Clamp values near boundaries

3. **Overlap Resolution**
   - Merge overlapping segments of same category/action
   - Flag excessive overlap across categories

#### Acceptance Criteria:
- [ ] Invalid records rejected with explicit errors
- [ ] Overlaps and boundary issues auto-corrected or flagged
- [ ] Validator unit-tested across edge cases

### Task 2: Confidence & Anomaly Detection
**Duration**: 1-2 days
**Priority**: High

#### Subtasks:
1. **Confidence Calibration**
   - Map model scores to calibrated confidence via Platt scaling or isotonic regression

2. **Anomaly Rules**
   - Extremely long segments
   - Excessive number of segments per hour
   - Rapid alternation between categories

3. **Drift Monitoring**
   - Track model score distributions over time
   - Alert on distribution shifts

#### Acceptance Criteria:
- [ ] Calibrated confidence scores persisted
- [ ] Anomalies detected and logged
- [ ] Drift metrics exported

### Task 3: Human Review Tools
**Duration**: 2 days
**Priority**: Medium

#### Subtasks:
1. **Web Review UI**
   - List segments with thumbnails and context
   - Approve/reject/edit actions and timestamps

2. **Reviewer Shortcuts**
   - Keyboard and seek shortcuts for efficient review
   - Batch operations for similar segments

3. **Feedback Integration**
   - Persist reviewer decisions
   - Optional: use accepted/rejected labels to fine-tune thresholds

#### Acceptance Criteria:
- [ ] Review UI supports efficient workflows
- [ ] Reviewer edits persist and propagate
- [ ] Feedback loop improves precision over time

## Deliverables
- JSON schema and validator
- Confidence calibration and anomaly detectors
- Human review UI and feedback system

## Testing
- Unit tests for validation logic
- Synthetic anomaly scenarios to verify detection
- Usability tests for review interface