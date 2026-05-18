"""Unit tests for scene analyzer pipeline helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

pytest.importorskip("flask")
pytest.importorskip("requests")
pytest.importorskip("prometheus_client")


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "scene-analyzer"
    / "app.py"
)
SPEC = spec_from_file_location("scene_analyzer_app", MODULE_PATH)
scene_analyzer = module_from_spec(SPEC)
SPEC.loader.exec_module(scene_analyzer)


def test_normalize_scene_probabilities_handles_shapes():
    preds = [[], [[0.0], [0.9], [0.2], [1.2]]]
    probs = scene_analyzer._normalize_scene_probabilities(preds)
    assert probs.ndim == 1
    assert len(probs) == 4
    assert probs[1] == 0.9
    assert probs[3] == 1.0


def test_select_transition_frames_collapses_runs_and_enforces_gap():
    probs = [0.1, 0.8, 0.9, 0.1, 0.85, 0.86, 0.1]
    peaks = scene_analyzer._select_transition_frames(probs, threshold=0.8, min_gap_frames=3)
    assert peaks == [2, 5]


def test_build_scene_windows_covers_full_duration():
    scenes = scene_analyzer._build_scene_windows(
        duration=12.0,
        timestamps=[3.0, 6.0, 9.0],
        min_scene_duration=1.0,
    )
    assert scenes[0]["start"] == 0.0
    assert scenes[-1]["end"] == 12.0
    assert abs(sum(scene["duration"] for scene in scenes) - 12.0) < 0.001


def test_build_sample_timestamps_stays_inside_scene():
    scene = {"start": 10.0, "end": 20.0}
    timestamps = scene_analyzer._build_sample_timestamps(scene, requested_samples=5, total_scene_count=50)
    assert len(timestamps) == 5
    assert min(timestamps) > 10.0
    assert max(timestamps) < 20.0


def test_extract_violence_score_accepts_multiple_response_formats():
    assert scene_analyzer._extract_violence_score({"violence": 0.4}) == 0.4
    assert scene_analyzer._extract_violence_score({"violence": {"general_violence": 0.6}}) == 0.6
    assert scene_analyzer._extract_violence_score(
        {"violence": {"category_scores": {"fighting": 0.7, "blood": 0.5}}}
    ) == 0.7
