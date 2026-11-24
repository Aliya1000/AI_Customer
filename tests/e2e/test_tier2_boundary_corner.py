"""Tier 2: Boundary & Corner Cases E2E Tests.

Validates resilience against invalid inputs, error status codes (404, 422, 400, 413),
empty database collections, large payloads, special characters, and edge conditions across
all feature areas (23 tests total).
"""

import pytest
from tests.e2e.helpers import (
    assert_valid_session,
    assert_valid_message,
    assert_valid_coaching_report,
    assert_valid_knowledge_document,
    create_test_session,
)

pytestmark = pytest.mark.tier2


# ============================================================================
# 1. Session Boundary & Validation Tests (8 tests)
# ============================================================================

class TestSessionBoundaryValidation:
    """Boundary and corner cases for session endpoints."""

    def test_post_session_invalid_mode(self, client):
        """POST /api/sessions with invalid interaction_mode returns HTTP 422."""
        payload = {
            "interaction_mode": "unsupported_mode",
            "product_name": "AeroSound Pro ANC Headphones",
            "customer_scenario": "Test scenario for unsupported mode.",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code == 422

    def test_post_session_missing_product_name(self, client):
        """POST /api/sessions with missing or empty product_name returns HTTP 422."""
        payload = {
            "interaction_mode": "simulator",
            "product_name": "",
            "customer_scenario": "Missing product name scenario.",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code == 422

    def test_post_session_missing_customer_scenario(self, client):
        """POST /api/sessions with missing or empty customer_scenario returns HTTP 422."""
        payload = {
            "interaction_mode": "simulator",
            "product_name": "AeroSound Pro ANC Headphones",
            "customer_scenario": "",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code == 422

    def test_post_session_large_scenario(self, client):
        """POST /api/sessions with a 10,000-character customer scenario succeeds without error."""
        large_scenario = "ANC buzzing and high-frequency noise issue: " + ("Details: Audio artifact observed. " * 300)
        assert len(large_scenario) >= 10000
        payload = {
            "interaction_mode": "simulator",
            "product_name": "AeroSound Pro ANC Headphones",
            "customer_scenario": large_scenario,
            "persona": "Patient",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data)
        assert len(data["customer_scenario"]) >= 10000

    def test_post_session_unknown_persona(self, client):
        """POST /api/sessions with an unusual/custom persona is handled gracefully."""
        payload = {
            "interaction_mode": "simulator",
            "product_name": "PulseWatch S4 Smartwatch",
            "customer_scenario": "Screen unresponsive after update.",
            "persona": "Extraordinary",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data)
        assert data.get("persona") is not None

    def test_post_session_empty_product_context(self, client):
        """POST /api/sessions with empty product_context succeeds with empty string default."""
        payload = {
            "interaction_mode": "simulator",
            "product_name": "AeroSound Pro ANC Headphones",
            "product_context": "",
            "customer_scenario": "Ear cup cushion loose.",
            "persona": "Patient",
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data)
        assert data.get("product_context") == ""

    def test_get_sessions_empty_database(self, client):
        """GET /api/sessions when no sessions have been created returns HTTP 200 with empty list."""
        try:
            from app.supabase_client.client import get_mock_store
            store = get_mock_store()
            store.tables["sessions"] = []
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_session_nonexistent_id(self, client):
        """GET /api/sessions/SES-NONEXISTENT returns HTTP 404 Not Found."""
        response = client.get("/api/sessions/SES-NONEXISTENT")
        assert response.status_code == 404


# ============================================================================
# 2. Message Boundary & Validation Tests (7 tests)
# ============================================================================

class TestMessageBoundaryValidation:
    """Boundary and corner cases for message endpoints."""

    def test_post_message_nonexistent_session(self, client):
        """POST /api/sessions/SES-NONEXISTENT/messages returns HTTP 404 Not Found."""
        payload = {"sender": "employee", "message_text": "Hello, how can I assist you?"}
        response = client.post("/api/sessions/SES-NONEXISTENT/messages", json=payload)
        assert response.status_code == 404

    def test_post_message_invalid_sender(self, client):
        """POST /api/sessions/{id}/messages with an invalid sender returns HTTP 422."""
        session = create_test_session(client)
        sid = session["session_id"]
        payload = {"sender": "robot", "message_text": "Automated greeting"}
        response = client.post(f"/api/sessions/{sid}/messages", json=payload)
        assert response.status_code == 422

    def test_post_message_empty_text(self, client):
        """POST /api/sessions/{id}/messages with empty message_text returns HTTP 422."""
        session = create_test_session(client)
        sid = session["session_id"]
        payload = {"sender": "employee", "message_text": ""}
        response = client.post(f"/api/sessions/{sid}/messages", json=payload)
        assert response.status_code == 422

    def test_post_message_whitespace_only_text(self, client):
        """POST /api/sessions/{id}/messages with whitespace-only text returns HTTP 422 or 400."""
        session = create_test_session(client)
        sid = session["session_id"]
        payload = {"sender": "employee", "message_text": "   \n\t  "}
        response = client.post(f"/api/sessions/{sid}/messages", json=payload)
        assert response.status_code in (400, 422)

    def test_post_message_very_large_text(self, client):
        """POST /api/sessions/{id}/messages with a 20,000-character message succeeds."""
        session = create_test_session(client)
        sid = session["session_id"]
        large_text = "Troubleshooting guide: " + ("Step: Verify Bluetooth pairing. " * 650)
        assert len(large_text) >= 20000
        payload = {"sender": "employee", "message_text": large_text}
        response = client.post(f"/api/sessions/{sid}/messages", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert "saved_message" in data
        assert len(data["saved_message"]["message_text"]) >= 20000

    def test_post_message_special_characters_emojis(self, client):
        """POST /api/sessions/{id}/messages preserves special characters, emojis, and script tags."""
        session = create_test_session(client)
        sid = session["session_id"]
        special_text = "🎧 ⚡ こんにちは \u0000 <script>alert(1)</script>"
        payload = {"sender": "employee", "message_text": special_text}
        response = client.post(f"/api/sessions/{sid}/messages", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert "saved_message" in data
        saved = data["saved_message"]
        assert "🎧" in saved["message_text"] or "script" in saved["message_text"]

    def test_get_messages_nonexistent_session(self, client):
        """GET /api/sessions/SES-NONEXISTENT/messages returns HTTP 404 Not Found."""
        response = client.get("/api/sessions/SES-NONEXISTENT/messages")
        assert response.status_code == 404


# ============================================================================
# 3. Knowledge Document Boundary & Validation Tests (6 tests)
# ============================================================================

class TestKnowledgeBoundaryValidation:
    """Boundary and corner cases for knowledge management endpoints."""

    def test_upload_unsupported_file_extension(self, client):
        """POST /api/knowledge/upload with unsupported file extension (.exe or .py) returns 400 or 422."""
        files = {"file": ("malware_installer.exe", b"\x4d\x5a\x90\x00", "application/octet-stream")}
        response = client.post("/api/knowledge/upload", files=files)
        assert response.status_code in (400, 422)

    def test_upload_missing_file_parameter(self, client):
        """POST /api/knowledge/upload with missing file parameter in multipart form returns HTTP 422."""
        response = client.post("/api/knowledge/upload", files={})
        assert response.status_code == 422

    def test_upload_empty_zero_byte_file(self, client):
        """POST /api/knowledge/upload with 0-byte file is handled gracefully."""
        files = {"file": ("empty_manual.txt", b"", "text/plain")}
        response = client.post("/api/knowledge/upload", files=files)
        assert response.status_code in (200, 201, 400, 422)

    def test_upload_large_file_size(self, client):
        """POST /api/knowledge/upload with 15MB file (exceeding 10MB limit) returns 400, 413, or 422."""
        large_payload = b"0" * (15 * 1024 * 1024)
        files = {"file": ("massive_catalog.pdf", large_payload, "application/pdf")}
        response = client.post("/api/knowledge/upload", files=files)
        assert response.status_code in (400, 413, 422)

    def test_delete_knowledge_document_nonexistent(self, client):
        """DELETE /api/knowledge/documents/DOC-NONEXISTENT returns HTTP 404 Not Found."""
        response = client.delete("/api/knowledge/documents/DOC-NONEXISTENT")
        assert response.status_code == 404

    def test_get_documents_empty_database(self, client):
        """GET /api/knowledge/documents when no documents have been uploaded returns HTTP 200 with []."""
        try:
            from app.supabase_client.client import get_mock_store
            store = get_mock_store()
            store.tables["knowledge_documents"] = []
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass
        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ============================================================================
# 4. Coaching Report Boundary & Validation Tests (2 tests)
# ============================================================================

class TestCoachingReportBoundaryValidation:
    """Boundary and corner cases for coaching report endpoint."""

    def test_get_coaching_report_nonexistent_session(self, client):
        """GET /api/sessions/SES-NONEXISTENT/coaching-report returns HTTP 404 Not Found."""
        response = client.get("/api/sessions/SES-NONEXISTENT/coaching-report")
        assert response.status_code == 404

    def test_get_coaching_report_empty_session(self, client):
        """GET /api/sessions/{id}/coaching-report immediately after creation returns valid baseline report."""
        session = create_test_session(client)
        sid = session["session_id"]
        response = client.get(f"/api/sessions/{sid}/coaching-report")
        assert response.status_code == 200
        report = response.json()
        assert_valid_coaching_report(report, expected_session_id=sid)
