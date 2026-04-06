"""Smoke tests — verify the app factory and model imports are healthy."""
from app.models import User, Claim, Document, DocumentVersion


def test_model_imports():
    """All four core models must be importable from app.models."""
    assert User is not None
    assert Claim is not None
    assert Document is not None
    assert DocumentVersion is not None


def test_app_creates(app):
    """App factory produces a working Flask app."""
    assert app is not None
    assert app.testing is True


def test_health_endpoint(client):
    """Health check endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
