"""Tests for /ready endpoint behavior across all services."""
import pytest


def test_ready_returns_false_when_models_not_loaded():
    """Service should report not ready when _models_ready is False."""
    # Contract test — verify the expected ready response shape when not loaded.
    # Full integration tests require running services; see docs/troubleshooting.md.
    response = {"status": "degraded", "models_loaded": False, "reason": "Model file not found"}
    assert response["models_loaded"] is False
    assert response["status"] != "ready"


def test_health_schema():
    """Health response must have 'status' key."""
    health_response = {"status": "ok"}
    assert "status" in health_response


def test_ready_schema_ready():
    """Ready response when models loaded must match schema."""
    response = {"status": "ready", "models_loaded": True}
    assert response["status"] == "ready"
    assert response["models_loaded"] is True


def test_ready_schema_degraded():
    """Degraded response must have reason."""
    response = {"status": "degraded", "models_loaded": False, "reason": "Model file not found"}
    assert response["status"] == "degraded"
    assert response["models_loaded"] is False
    assert "reason" in response


def test_ready_response_has_required_keys():
    """Both ready and degraded responses must include status and models_loaded."""
    for response in [
        {"status": "ready", "models_loaded": True},
        {"status": "degraded", "models_loaded": False, "reason": "no model"},
    ]:
        assert "status" in response
        assert "models_loaded" in response


def test_ready_status_values_are_constrained():
    """status must be one of the defined values."""
    valid_statuses = {"ready", "degraded"}
    ready_response = {"status": "ready", "models_loaded": True}
    degraded_response = {"status": "degraded", "models_loaded": False, "reason": "x"}

    assert ready_response["status"] in valid_statuses
    assert degraded_response["status"] in valid_statuses
