import pytest
from fastapi.testclient import TestClient
from rag_service.api.app import app
from rag_service.config import settings

client = TestClient(app)


def test_missing_session_id_header_rejected():
    """Requesting RAG retrieval without X-Session-ID returns HTTP 401."""
    res = client.post(
        "/api/v1/documents/retrieve",
        json={"query": "test warranty", "top_k": 2},
    )
    assert res.status_code == 401
    assert "Missing 'X-Session-ID' header" in res.json().get("detail", "")


def test_malformed_session_id_rejected():
    """Session IDs not conforming to backend SES- pattern are rejected with 422."""
    res = client.post(
        "/api/v1/documents/retrieve",
        headers={"X-Session-ID": "INVALID-FORMAT-123"},
        json={"query": "test warranty", "top_k": 2},
    )
    assert res.status_code == 422
    assert "Malformed session ID" in res.json().get("detail", "")


def test_system_session_without_secret_rejected():
    """SYSTEM session without secret returns HTTP 403."""
    res = client.post(
        "/api/v1/documents/retrieve",
        headers={"X-Session-ID": "SYSTEM"},
        json={"query": "test warranty", "top_k": 2},
    )
    assert res.status_code == 403


def test_system_session_with_valid_secret_accepted():
    """SYSTEM session with valid X-Internal-Secret returns HTTP 200."""
    res = client.post(
        "/api/v1/documents/retrieve",
        headers={
            "X-Session-ID": "SYSTEM",
            "X-Internal-Secret": settings.rag_internal_secret,
        },
        json={"query": "warranty policy", "top_k": 2},
    )
    assert res.status_code == 200
    assert res.json().get("session_id") == "SYSTEM"


def test_valid_backend_session_accepted():
    """Valid backend-generated session ID format succeeds."""
    res = client.post(
        "/api/v1/documents/retrieve",
        headers={
            "X-Session-ID": "SES-2026-TEST01",
            "X-Internal-Secret": settings.rag_internal_secret,
        },
        json={"query": "headphone audio crack", "top_k": 2},
    )
    assert res.status_code == 200
    assert res.json().get("session_id") == "SES-2026-TEST01"
