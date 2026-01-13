"""
Test fixtures for Athena Server v2
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Provide authentication headers for API requests."""
    from config import settings
    return {"Authorization": f"Bearer {settings.ATHENA_API_KEY}"}
