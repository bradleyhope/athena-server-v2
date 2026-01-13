"""
Test API endpoints for Athena Server v2
"""

import pytest


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "database" in data["components"]


def test_observations_endpoint(client):
    """Test the observations list endpoint."""
    response = client.get("/api/observations?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert "observations" in data
    assert isinstance(data["observations"], list)


def test_patterns_endpoint(client):
    """Test the patterns list endpoint."""
    response = client.get("/api/patterns?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert "patterns" in data
    assert isinstance(data["patterns"], list)


def test_synthesis_endpoint(client):
    """Test the synthesis endpoint."""
    response = client.get("/api/synthesis")
    assert response.status_code == 200
    
    data = response.json()
    # Synthesis might be empty if none have been generated yet
    assert isinstance(data, dict)


def test_brain_status_endpoint(client):
    """Test the brain status endpoint."""
    response = client.get("/api/brain/status")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, dict)


def test_sentry_test_endpoint(client):
    """Test the Sentry test endpoint (should raise an error)."""
    response = client.get("/api/sentry-test")
    # This endpoint intentionally raises an exception
    assert response.status_code == 500


@pytest.mark.parametrize("limit", [1, 5, 10])
def test_observations_with_different_limits(client, limit):
    """Test observations endpoint with different limit values."""
    response = client.get(f"/api/observations?limit={limit}")
    assert response.status_code == 200
    
    data = response.json()
    observations = data["observations"]
    assert len(observations) <= limit


def test_invalid_observation_limit(client):
    """Test observations endpoint with invalid limit."""
    response = client.get("/api/observations?limit=-1")
    # Should either handle gracefully or return an error
    assert response.status_code in [200, 400, 422]
