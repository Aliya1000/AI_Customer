"""Tier 1: Feature Coverage E2E Tests.

Covers all 10 REST endpoints with 51 comprehensive tests:
- Products (GET /api/products): 5 tests
- Sessions (POST /api/sessions): 5 tests
- Sessions list (GET /api/sessions): 5 tests
- Session detail (GET /api/sessions/{id}): 5 tests
- Messages send (POST /api/sessions/{id}/messages): 6 tests
- Messages list (GET /api/sessions/{id}/messages): 5 tests
- Knowledge upload (POST /api/knowledge/upload): 5 tests
- Knowledge list (GET /api/knowledge/documents): 5 tests
- Knowledge delete (DELETE /api/knowledge/documents/{id}): 5 tests
- Coaching report (GET /api/sessions/{id}/coaching-report): 5 tests
"""

import pytest
from tests.e2e.helpers import (
    assert_valid_product,
    assert_valid_session,
    assert_valid_message,
    assert_valid_agent_outputs,
    assert_valid_coaching_report,
    assert_valid_knowledge_document,
)

pytestmark = pytest.mark.tier1


# ============================================================================
# 1. Product Catalog (GET /api/products) — 5 tests
# ============================================================================

class TestProductCatalog:
    """Tests for GET /api/products."""

    def test_get_products_status_ok(self, client):
        """GET /api/products returns HTTP 200 OK."""
        response = client.get("/api/products")
        assert response.status_code == 200

    def test_get_products_list_count(self, client):
        """GET /api/products returns a list of products with length >= 3."""
        response = client.get("/api/products")
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) >= 3

    def test_get_products_seeded_items(self, client):
        """GET /api/products contains canonical seeded products (PRD-01, PRD-02, PRD-03)."""
        response = client.get("/api/products")
        assert response.status_code == 200
        products = response.json()
        product_ids = {p.get("product_id") for p in products}
        for expected_id in ["PRD-01", "PRD-02", "PRD-03"]:
            assert expected_id in product_ids, f"Seeded product {expected_id} missing from catalog"

    def test_get_products_schema_fields(self, client):
        """GET /api/products returns items conforming to ProductResponse schema."""
        response = client.get("/api/products")
        assert response.status_code == 200
        products = response.json()
        for prod in products:
            assert_valid_product(prod)

    def test_get_products_content_type(self, client):
        """GET /api/products returns application/json Content-Type."""
        response = client.get("/api/products")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type


# ============================================================================
# 2. Session Creation (POST /api/sessions) — 5 tests
# ============================================================================

class TestSessionCreation:
    """Tests for POST /api/sessions."""

    def test_post_session_simulator_mode(self, client, sample_session_payload):
        """POST /api/sessions creates a simulator mode session with active status."""
        response = client.post("/api/sessions", json=sample_session_payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data, expected_mode="simulator")
        assert data["status"] == "active"
        assert data["product_name"] == sample_session_payload["product_name"]

    def test_post_session_manual_mode(self, client, sample_manual_session_payload):
        """POST /api/sessions creates a manual mode session."""
        response = client.post("/api/sessions", json=sample_manual_session_payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data, expected_mode="manual")
        assert data["status"] == "active"

    def test_post_session_replay_mode(self, client):
        """POST /api/sessions creates a replay mode session with transcript."""
        payload = {
            "interaction_mode": "replay",
            "product_name": "CloudDesk CRM Pro Subscription",
            "product_context": "Annual Tier 2 Account",
            "customer_scenario": "Inquiry regarding SAML SSO configuration options.",
            "persona": "Standard",
            "emotional_progression": None,
            "replay_transcript": '[{"sender": "customer", "message_text": "How do I configure SAML?"}]',
        }
        response = client.post("/api/sessions", json=payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_session(data, expected_mode="replay")

    def test_post_session_seeds_initial_msg(self, client, sample_session_payload):
        """POST /api/sessions automatically seeds an initial customer message."""
        res_session = client.post("/api/sessions", json=sample_session_payload)
        assert res_session.status_code in (200, 201)
        session_id = res_session.json()["session_id"]

        # Fetch messages for session
        res_msgs = client.get(f"/api/sessions/{session_id}/messages")
        assert res_msgs.status_code == 200
        msgs = res_msgs.json()
        assert len(msgs) >= 1
        first_msg = msgs[0]
        assert first_msg["sender"] == "customer"
        assert first_msg["message_text"] == sample_session_payload["customer_scenario"]
        assert first_msg["session_id"] == session_id

    def test_post_session_returns_input_data(self, client, sample_session_payload):
        """POST /api/sessions accurately reflects input fields in response payload."""
        response = client.post("/api/sessions", json=sample_session_payload)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["product_name"] == sample_session_payload["product_name"]
        assert data["customer_scenario"] == sample_session_payload["customer_scenario"]
        assert data["product_context"] == sample_session_payload["product_context"]
        assert data["persona"] == sample_session_payload["persona"]


# ============================================================================
# 3. Sessions List (GET /api/sessions) — 5 tests
# ============================================================================

class TestSessionsList:
    """Tests for GET /api/sessions."""

    def test_get_sessions_status_ok(self, client):
        """GET /api/sessions returns HTTP 200 OK."""
        response = client.get("/api/sessions")
        assert response.status_code == 200

    def test_get_sessions_returns_list(self, client):
        """GET /api/sessions returns a JSON list."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_sessions_ordered_desc(self, client, sample_session_payload, sample_manual_session_payload):
        """GET /api/sessions returns sessions ordered by created_at descending."""
        res1 = client.post("/api/sessions", json=sample_session_payload)
        assert res1.status_code in (200, 201)
        res2 = client.post("/api/sessions", json=sample_manual_session_payload)
        assert res2.status_code in (200, 201)

        response = client.get("/api/sessions")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 2
        # Verify created_at timestamps are descending
        for i in range(len(sessions) - 1):
            assert sessions[i]["created_at"] >= sessions[i + 1]["created_at"]

    def test_get_sessions_contains_created(self, client, sample_session_payload):
        """GET /api/sessions contains the newly created session."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        assert res_create.status_code in (200, 201)
        session_id = res_create.json()["session_id"]

        response = client.get("/api/sessions")
        assert response.status_code == 200
        session_ids = [s["session_id"] for s in response.json()]
        assert session_id in session_ids

    def test_get_sessions_schema_fields(self, client, sample_session_payload):
        """GET /api/sessions returns records satisfying SessionResponse schema."""
        client.post("/api/sessions", json=sample_session_payload)
        response = client.get("/api/sessions")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) > 0
        for s in sessions:
            assert_valid_session(s)


# ============================================================================
# 4. Session Detail (GET /api/sessions/{id}) — 5 tests
# ============================================================================

class TestSessionDetail:
    """Tests for GET /api/sessions/{id}."""

    def test_get_session_by_id_status_ok(self, client, sample_session_payload):
        """GET /api/sessions/{id} returns HTTP 200 OK for an existing session."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        assert res_create.status_code in (200, 201)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200

    def test_get_session_by_id_metadata(self, client, sample_session_payload):
        """GET /api/sessions/{id} returns correct session metadata."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["product_name"] == sample_session_payload["product_name"]
        assert data["status"] == "active"
        assert_valid_session(data)

    def test_get_session_by_id_agent_outputs(self, client, sample_session_payload):
        """GET /api/sessions/{id} includes agent_outputs structure."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "agent_outputs" in data
        assert data["agent_outputs"] is not None

    def test_get_session_by_id_6_sections(self, client, sample_session_payload):
        """GET /api/sessions/{id} agent_outputs includes all 6 sections."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        outputs = response.json().get("agent_outputs")
        assert outputs is not None
        assert_valid_agent_outputs(outputs)

    def test_get_session_by_id_warranty(self, client, sample_session_payload):
        """GET /api/sessions/{id} agent_outputs contains product warranty status."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        outputs = response.json().get("agent_outputs", {})
        prod_info = outputs.get("product_information", {})
        assert "warranty_status" in prod_info
        assert isinstance(prod_info["warranty_status"], str)
        assert len(prod_info["warranty_status"]) > 0


# ============================================================================
# 5. Messages Send (POST /api/sessions/{id}/messages) — 6 tests
# ============================================================================

class TestMessagesSend:
    """Tests for POST /api/sessions/{id}/messages."""

    def test_post_message_employee_simulator(self, client, sample_session_payload):
        """POST /api/sessions/{id}/messages in simulator mode generates simulated customer reply."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        msg_payload = {"sender": "employee", "message_text": "I can help resolve the buzzing noise."}
        response = client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert response.status_code in (200, 201)
        data = response.json()

        assert "saved_message" in data
        assert_valid_message(data["saved_message"], expected_session_id=session_id, expected_sender="employee")
        assert data["saved_message"]["message_text"] == msg_payload["message_text"]

        assert "simulated_customer_reply" in data
        assert data["simulated_customer_reply"] is not None
        assert_valid_message(data["simulated_customer_reply"], expected_session_id=session_id, expected_sender="customer")

        assert "agent_outputs" in data
        assert_valid_agent_outputs(data["agent_outputs"])

    def test_post_message_employee_manual(self, client, sample_manual_session_payload):
        """POST /api/sessions/{id}/messages in manual mode does not generate simulated reply."""
        res_create = client.post("/api/sessions", json=sample_manual_session_payload)
        session_id = res_create.json()["session_id"]

        msg_payload = {"sender": "employee", "message_text": "Hello, thank you for contacting support."}
        response = client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert response.status_code in (200, 201)
        data = response.json()

        assert data["saved_message"]["sender"] == "employee"
        assert data["simulated_customer_reply"] is None
        assert_valid_agent_outputs(data["agent_outputs"])

    def test_post_message_customer_manual(self, client, sample_manual_session_payload):
        """POST /api/sessions/{id}/messages with sender='customer' saves message without simulation."""
        res_create = client.post("/api/sessions", json=sample_manual_session_payload)
        session_id = res_create.json()["session_id"]

        msg_payload = {"sender": "customer", "message_text": "The watch screen is completely black."}
        response = client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert response.status_code in (200, 201)
        data = response.json()

        assert data["saved_message"]["sender"] == "customer"
        assert data["simulated_customer_reply"] is None

    def test_post_message_persists_text(self, client, sample_session_payload):
        """POST /api/sessions/{id}/messages faithfully saves exact message text."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        unique_text = "Please try holding the power button for exactly 10 seconds to factory reset."
        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": unique_text},
        )
        assert response.status_code in (200, 201)
        assert response.json()["saved_message"]["message_text"] == unique_text

    def test_post_message_updates_agent_out(self, client, sample_session_payload):
        """POST /api/sessions/{id}/messages returns updated agent_outputs."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "Let me check the knowledge base."},
        )
        assert response.status_code in (200, 201)
        outputs = response.json().get("agent_outputs")
        assert outputs is not None
        assert_valid_agent_outputs(outputs)

    def test_post_message_chronology(self, client, sample_session_payload):
        """Subsequent messages maintain chronological timestamp ordering."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        res1 = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "Turn 1 employee reply."},
        )
        res2 = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "Turn 2 employee follow up."},
        )
        assert res1.status_code in (200, 201)
        assert res2.status_code in (200, 201)
        t1 = res1.json()["saved_message"]["timestamp"]
        t2 = res2.json()["saved_message"]["timestamp"]
        assert t2 >= t1


# ============================================================================
# 6. Messages List (GET /api/sessions/{id}/messages) — 5 tests
# ============================================================================

class TestMessagesList:
    """Tests for GET /api/sessions/{id}/messages."""

    def test_get_messages_status_ok(self, client, sample_session_payload):
        """GET /api/sessions/{id}/messages returns HTTP 200 OK."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200

    def test_get_messages_chronological(self, client, sample_session_payload):
        """Messages are returned in ascending chronological order."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "First response."},
        )
        client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "Second response."},
        )

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        msgs = response.json()
        assert len(msgs) >= 3  # initial + 2 turns (plus simulated turns)
        for i in range(len(msgs) - 1):
            assert msgs[i]["timestamp"] <= msgs[i + 1]["timestamp"]

    def test_get_messages_includes_simulated(self, client, sample_session_payload):
        """Message list in simulator mode includes initial scenario, employee turn, and simulated reply."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        client.post(
            f"/api/sessions/{session_id}/messages",
            json={"sender": "employee", "message_text": "Reset the device."},
        )

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        msgs = response.json()
        assert len(msgs) == 3
        assert msgs[0]["sender"] == "customer"
        assert msgs[1]["sender"] == "employee"
        assert msgs[2]["sender"] == "customer"

    def test_get_messages_schema_fields(self, client, sample_session_payload):
        """All returned messages conform to MessageResponse schema."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        msgs = response.json()
        assert len(msgs) > 0
        for m in msgs:
            assert_valid_message(m, expected_session_id=session_id)

    def test_get_messages_empty_session_id(self, client, sample_session_payload):
        """Messages returned strictly match the requested session_id."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        for m in response.json():
            assert m["session_id"] == session_id


# ============================================================================
# 7. Knowledge Upload (POST /api/knowledge/upload) — 5 tests
# ============================================================================

class TestKnowledgeUpload:
    """Tests for POST /api/knowledge/upload."""

    def test_upload_txt_document(self, client, sample_txt_file):
        """POST /api/knowledge/upload accepts a .txt file upload."""
        fname, content, ctype = sample_txt_file
        response = client.post("/api/knowledge/upload", files={"file": (fname, content, ctype)})
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_knowledge_document(data)
        assert data["file_type"].upper() == "TXT"
        assert data["filename"] == fname

    def test_upload_pdf_document(self, client, sample_pdf_file):
        """POST /api/knowledge/upload accepts a .pdf file upload."""
        fname, content, ctype = sample_pdf_file
        response = client.post("/api/knowledge/upload", files={"file": (fname, content, ctype)})
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_knowledge_document(data)
        assert data["file_type"].upper() == "PDF"

    def test_upload_json_document(self, client, sample_json_file):
        """POST /api/knowledge/upload accepts a .json file upload."""
        fname, content, ctype = sample_json_file
        response = client.post("/api/knowledge/upload", files={"file": (fname, content, ctype)})
        assert response.status_code in (200, 201)
        data = response.json()
        assert_valid_knowledge_document(data)
        assert data["file_type"].upper() == "JSON"

    def test_upload_returns_doc_id(self, client, sample_txt_file):
        """POST /api/knowledge/upload returns document_id starting with 'DOC-'."""
        fname, content, ctype = sample_txt_file
        response = client.post("/api/knowledge/upload", files={"file": (fname, content, ctype)})
        assert response.status_code in (200, 201)
        doc_id = response.json().get("document_id")
        assert doc_id is not None
        assert doc_id.startswith("DOC-")

    def test_upload_triggers_storage_persist(self, client, sample_txt_file):
        """Uploaded document is persisted and listed in GET /api/knowledge/documents."""
        fname, content, ctype = sample_txt_file
        res_upload = client.post("/api/knowledge/upload", files={"file": (fname, content, ctype)})
        assert res_upload.status_code in (200, 201)
        doc_id = res_upload.json()["document_id"]

        res_list = client.get("/api/knowledge/documents")
        assert res_list.status_code == 200
        doc_ids = [d["document_id"] for d in res_list.json()]
        assert doc_id in doc_ids


# ============================================================================
# 8. Knowledge List (GET /api/knowledge/documents) — 5 tests
# ============================================================================

class TestKnowledgeList:
    """Tests for GET /api/knowledge/documents."""

    def test_get_documents_status_ok(self, client):
        """GET /api/knowledge/documents returns HTTP 200 OK."""
        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200

    def test_get_documents_returns_list(self, client):
        """GET /api/knowledge/documents returns a list."""
        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_documents_ordered_desc(self, client, sample_txt_file, sample_json_file):
        """GET /api/knowledge/documents orders uploaded documents."""
        client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        client.post("/api/knowledge/upload", files={"file": sample_json_file})

        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) >= 2
        for i in range(len(docs) - 1):
            assert docs[i]["upload_time"] >= docs[i + 1]["upload_time"]

    def test_get_documents_contains_uploaded(self, client, sample_txt_file):
        """GET /api/knowledge/documents contains uploaded document ID."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200
        doc_ids = [d["document_id"] for d in response.json()]
        assert doc_id in doc_ids

    def test_get_documents_schema_fields(self, client, sample_txt_file):
        """All items in GET /api/knowledge/documents conform to KnowledgeDocumentResponse."""
        client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        response = client.get("/api/knowledge/documents")
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) > 0
        for d in docs:
            assert_valid_knowledge_document(d)


# ============================================================================
# 9. Knowledge Delete (DELETE /api/knowledge/documents/{id}) — 5 tests
# ============================================================================

class TestKnowledgeDelete:
    """Tests for DELETE /api/knowledge/documents/{id}."""

    def test_delete_document_status_ok(self, client, sample_txt_file):
        """DELETE /api/knowledge/documents/{id} returns HTTP 200 OK for an existing doc."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        res_del = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert res_del.status_code == 200

    def test_delete_document_response_shape(self, client, sample_txt_file):
        """DELETE /api/knowledge/documents/{id} returns {'deleted': True, 'document_id': doc_id}."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        res_del = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert res_del.status_code == 200
        data = res_del.json()
        assert data.get("deleted") is True
        assert data.get("document_id") == doc_id

    def test_delete_document_removes_from_list(self, client, sample_txt_file):
        """Deleted document no longer appears in GET /api/knowledge/documents."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        client.delete(f"/api/knowledge/documents/{doc_id}")
        res_list = client.get("/api/knowledge/documents")
        assert res_list.status_code == 200
        doc_ids = [d["document_id"] for d in res_list.json()]
        assert doc_id not in doc_ids

    def test_delete_document_storage_cleanup(self, client, sample_txt_file):
        """DELETE /api/knowledge/documents/{id} cleans up associated storage asset."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        res_del = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert res_del.status_code == 200

        # Attempt to clean up or verify store
        try:
            from app.supabase_client.client import get_mock_store
            store = get_mock_store()
            bucket = store.storage.get("knowledge-docs", {})
            matching_keys = [k for k in bucket.keys() if doc_id in k]
            assert len(matching_keys) == 0, f"Storage asset not removed: {matching_keys}"
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass

    def test_delete_document_idempotency(self, client, sample_txt_file):
        """Deleting an already-deleted document ID returns HTTP 404 Not Found."""
        res_upload = client.post("/api/knowledge/upload", files={"file": sample_txt_file})
        doc_id = res_upload.json()["document_id"]

        # First delete succeeds
        res_del1 = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert res_del1.status_code == 200

        # Second delete fails with 404
        res_del2 = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert res_del2.status_code == 404


# ============================================================================
# 10. Coaching Report (GET /api/sessions/{id}/coaching-report) — 5 tests
# ============================================================================

class TestCoachingReport:
    """Tests for GET /api/sessions/{id}/coaching-report."""

    def test_get_coaching_report_status_ok(self, client, sample_session_payload):
        """GET /api/sessions/{id}/coaching-report returns HTTP 200 OK for a valid session."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert response.status_code == 200

    def test_get_coaching_report_fields(self, client, sample_session_payload):
        """GET /api/sessions/{id}/coaching-report returns all schema fields."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert response.status_code == 200
        data = response.json()
        assert_valid_coaching_report(data, expected_session_id=session_id)

    def test_get_coaching_report_score_range(self, client, sample_session_payload):
        """Evaluation score is between 0 and 100 inclusive."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert response.status_code == 200
        score = response.json().get("evaluation_score")
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_get_coaching_report_4_lists(self, client, sample_session_payload):
        """Report contains 4 required list fields: strengths, areas_for_improvement, recommendations, recommended_replies."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        response = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert response.status_code == 200
        data = response.json()
        for field in ["strengths", "areas_for_improvement", "recommendations", "recommended_replies"]:
            assert field in data, f"Missing list field: {field}"
            assert isinstance(data[field], list), f"Field {field} must be a list"

    def test_get_coaching_report_idempotency(self, client, sample_session_payload):
        """Successive calls to coaching-report return consistent report data."""
        res_create = client.post("/api/sessions", json=sample_session_payload)
        session_id = res_create.json()["session_id"]

        res1 = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert res1.status_code == 200
        res2 = client.get(f"/api/sessions/{session_id}/coaching-report")
        assert res2.status_code == 200
        assert res1.json()["report_id"] == res2.json()["report_id"]
        assert res1.json()["evaluation_score"] == res2.json()["evaluation_score"]
