"""
Unit tests for JWT Authentication and Leads endpoints:
- POST /auth/login with valid and invalid credentials
- GET /auth/me with Bearer token
- GET /leads and classification filtering
- GET /leads/{lead_id} profile inspection
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_admin_jwt_login_success():
    """Assert valid credentials return signed JWT bearer token."""
    client = TestClient(app)
    res = client.post("/auth/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"


def test_admin_jwt_login_invalid():
    """Assert invalid credentials return HTTP 401 unauthorized."""
    client = TestClient(app)
    res = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_auth_me_profile():
    """Assert /auth/me returns admin profile when authenticated."""
    client = TestClient(app)
    login_res = client.post("/auth/login", json={"username": "admin", "password": "password123"})
    token = login_res.json()["access_token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["sub"] == "admin"


def test_list_leads_and_filtering():
    """Assert /leads returns pipeline leads with BANT scores and classification badges."""
    client = TestClient(app)
    res = client.get("/leads")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 3

    first_lead = data["data"][0]
    assert "lead_score" in first_lead
    assert first_lead["classification"] in {"HOT", "WARM", "COLD"}
    assert "phone_number" in first_lead

    # Test filtering by HOT classification
    hot_res = client.get("/leads?classification=HOT")
    assert hot_res.status_code == 200
    hot_leads = hot_res.json()["data"]
    assert all(l["classification"] == "HOT" for l in hot_leads)


def test_get_lead_detail():
    """Assert /leads/{lead_id} returns full profile and call history."""
    client = TestClient(app)
    lead_id = "11111111-1111-1111-1111-111111111111"
    res = client.get(f"/leads/{lead_id}")
    assert res.status_code == 200
    lead = res.json()["data"]
    assert lead["name"] == "Aman Sharma"
    assert "bant" in lead
    assert lead["bant"]["budget"] == "5 lakh"
    assert len(lead["calls"]) > 0
