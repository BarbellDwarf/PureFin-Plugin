# Implementation Tracker - PureFin

This tracker reflects the current implementation state of the repository.

**Last Updated**: 2026-05

---

## Legend

- ✅ **Complete**
- 🟡 **Partial / limited**
- ❌ **Not started**

---

## Phase 1: Core Plugin + Platform

| Area | Status | Notes |
|------|--------|-------|
| Plugin load / DI wiring | ✅ | Uses `IPluginServiceRegistrator` |
| Framework + Jellyfin alignment | ✅ | `net9.0`, Jellyfin packages `10.11.8`, `targetAbi 10.11.0.0` |
| Config UI | ✅ | Main settings page + scene detection controls |
| Plugin repository metadata | ✅ | `build.yaml` and release manifest workflow in place |

---

## Phase 2: AI Pipeline

| Area | Status | Notes |
|------|--------|-------|
| Scene detection orchestration | ✅ | TransNetV2 default with FFmpeg fallback |
| Sampling mode | 🟡 | Kept for diagnostics only; not recommended for production |
| NSFW/immodesty scoring | ✅ | Real model-backed path used in running setup |
| Violence scoring | ✅ | Content classifier integrated |
| Profanity audio pipeline | ❌ | Planned |

---

## Phase 3: Playback + Segment Data

| Area | Status | Notes |
|------|--------|-------|
| Segment persistence | ✅ | Per-item JSON with raw AI scores |
| Dynamic threshold filtering | ✅ | Applied at playback time from current config |
| Skip action | ✅ | Primary action in active flow |
| Mute action | 🟡 | Falls back to skip |
| Admin segment inspection | ✅ | `PureFinSegmentsController` + `segments.html` |
| Manual segment editing | ❌ | Planned |

---

## Phase 4: Multi-User / External Data

| Area | Status | Notes |
|------|--------|-------|
| Per-user filtering profiles | ❌ | Planned |
| Community data merge | ❌ | Planned |
| Segment import/export workflow | ❌ | Planned |

---

## Phase 5: Quality, CI/CD, and Operations

| Area | Status | Notes |
|------|--------|-------|
| Plugin unit tests | ✅ | Passing in current branch |
| AI service tests | ✅ | Workflow exists for `ai-services/tests` |
| Build workflow | ✅ | Builds/tests plugin in CI |
| Release workflow | ✅ | Publishes artifacts + updates `gh-pages` manifest |
| Install / versioning / rollout docs | ✅ | Updated for PureFin + Jellyfin 10.11.x |

---

## Current Gaps (Next Work)

1. Implement profanity detection pipeline (audio/transcription).
2. Add true mute behavior (requires client-capable flow).
3. Add per-user profile support.
4. Add manual segment editing and override workflow.
5. Add distributed worker queue for multi-node AI processing at scale.
