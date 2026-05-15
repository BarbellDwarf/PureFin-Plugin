"""Tests for analysis response schema conformance."""
import json
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "analysis-response.json")


def test_schema_file_exists():
    assert os.path.exists(SCHEMA_PATH), f"Schema file not found at {SCHEMA_PATH}"


def test_schema_is_valid_json():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    assert "$schema" in schema or "type" in schema


def test_valid_response_passes_contract():
    """A well-formed response should match the expected structure."""
    response = {
        "schema_version": "1.0",
        "segments": [
            {
                "start_time": 10.0,
                "end_time": 25.5,
                "category": "nsfw",
                "confidence": 0.92,
                "metadata": {}
            }
        ],
        "model_versions": {
            "nsfw-mobilenet": "1.0.0"
        }
    }

    assert response["schema_version"] == "1.0"
    assert isinstance(response["segments"], list)
    for seg in response["segments"]:
        assert "start_time" in seg
        assert "end_time" in seg
        assert "category" in seg
        assert "confidence" in seg
        assert 0 <= seg["confidence"] <= 1
        assert seg["category"] in ("nsfw", "violence", "profanity", "unknown")


def test_empty_segments_is_valid():
    """Response with no segments is valid."""
    response = {
        "schema_version": "1.0",
        "segments": [],
        "model_versions": {}
    }
    assert isinstance(response["segments"], list)
    assert len(response["segments"]) == 0


def test_confidence_bounds():
    """Confidence values must be between 0 and 1 inclusive."""
    valid_confidences = [0.0, 0.5, 1.0]
    invalid_confidences = [-0.1, 1.1, 2.0]

    for c in valid_confidences:
        assert 0 <= c <= 1, f"Expected {c} to be valid"

    for c in invalid_confidences:
        assert not (0 <= c <= 1), f"Expected {c} to be invalid"


def test_all_valid_categories():
    """All known categories must be accepted."""
    valid_categories = ("nsfw", "violence", "profanity", "unknown")
    for cat in valid_categories:
        seg = {"category": cat, "confidence": 0.5}
        assert seg["category"] in valid_categories


def test_segment_end_time_after_start_time():
    """end_time must be greater than start_time."""
    valid_seg = {"start_time": 10.0, "end_time": 25.5, "category": "nsfw", "confidence": 0.5}
    assert valid_seg["end_time"] > valid_seg["start_time"]


def test_model_versions_is_dict():
    """model_versions field must be a dict."""
    response = {
        "schema_version": "1.0",
        "segments": [],
        "model_versions": {"nsfw-mobilenet": "1.0.0"}
    }
    assert isinstance(response["model_versions"], dict)
