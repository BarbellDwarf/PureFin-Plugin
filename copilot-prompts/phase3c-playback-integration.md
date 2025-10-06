# Phase 3C: Playback Integration

## Overview
Implement real-time playback filtering by monitoring Jellyfin sessions, detecting when the current playback position enters a flagged segment, and triggering actions (skip/mute/blur) across supported clients.

## Objectives
- Low-latency detection of segment boundaries during playback
- Cross-client compatibility for skip/mute commands
- Resilient behavior on seeks, pauses, and network jitter

## Tasks

### Task 1: Session Event Subscriptions
**Duration**: 1 day
**Priority**: Critical

#### Subtasks:
1. **Subscribe to Session Manager**
   ```csharp
   _sessionManager.SessionStarted += OnSessionStarted;
   _sessionManager.SessionEnded += OnSessionEnded;
   _sessionManager.PlaybackProgress += OnPlaybackProgress;
   _sessionManager.PlaybackStart += OnPlaybackStart;
   _sessionManager.PlaybackStopped += OnPlaybackStopped;
   ```

2. **Track Per-Session State**
   - Current mediaId
   - Last known position ticks
   - Active segment (if any)

3. **Handle Seeks and Pauses**
   - Reset state on seek
   - Pause timers on pause events

#### Acceptance Criteria:
- [ ] Events fire reliably across clients
- [ ] State tracked per session
- [ ] Seek/pause handled without errors

### Task 2: Boundary Detection Engine
**Duration**: 2 days
**Priority**: High

#### Subtasks:
1. **Polling Loop**
   - Poll current position every 250ms if progress events too sparse
   - Query active segments via repository

2. **Debounce & Hysteresis**
   - Avoid flapping at boundaries with ±150ms hysteresis
   - Single-fire actions per segment entry

3. **Next Boundary Scheduling**
   - Schedule timer for segment end to restore state or auto-seek

#### Acceptance Criteria:
- [ ] Boundary detection within ±200ms
- [ ] No duplicate triggers on jitter
- [ ] Accurate end-of-segment restoration

### Task 3: Action Execution
**Duration**: 2 days
**Priority**: Critical

#### Subtasks:
1. **Skip Action**
   ```csharp
   await _sessionApi.SeekAsync(sessionId, TimeSpan.FromSeconds(segment.End));
   ```

2. **Mute Action**
   - If supported: set volume to 0 via client API
   - Else: fast-seek micro-skip (start->end)

3. **Blur Action (Optional)**
   - Not natively supported; fallback to skip

4. **User Feedback**
   - Optional OSD toast: "Filtered: immodesty (skip)"

#### Acceptance Criteria:
- [ ] Skip/mute work on web client
- [ ] Graceful fallback on unsupported clients
- [ ] OSD feedback togglable

### Task 4: Profile-Aware Actions
**Duration**: 1 day
**Priority**: Medium

#### Subtasks:
1. **Per-User Sensitivity**
   - Load user profile at session start
   - Filter segments by category thresholds

2. **Per-Item Overrides**
   - Apply item-specific adjustments

3. **Audit Logging**
   - Record actions with timestamps and reasons

#### Acceptance Criteria:
- [ ] Different users receive different filtering
- [ ] Overrides respected
- [ ] Logs available for debugging

## Deliverables
- Session event handlers and state tracker
- Boundary detection engine with timers
- Action executors for skip/mute
- Profile-aware filtering logic and logging

## Testing
- Simulate playback positions and verify actions
- Manual tests on web and Android clients
- Stress tests with rapid seeks and pauses