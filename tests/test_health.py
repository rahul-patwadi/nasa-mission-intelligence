"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_200() -> None:
    """Health endpoint should return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_returns_healthy_status() -> None:
    """Health endpoint should report healthy status and service name."""
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "NASA Mission Intelligence"