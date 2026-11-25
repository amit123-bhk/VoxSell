"""
Unit tests for application health check endpoint.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_returns_200_ok():
    """
    Assert that GET /health returns 200 OK with standard payload structure.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "VoxSell"
    assert "version" in data
    assert "timestamp" in data
