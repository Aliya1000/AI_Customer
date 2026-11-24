"""Tier 3: Pairwise & Cross-Feature Integration E2E Tests.

Validates multi-step workflows, cross-entity integrity, state transitions,
knowledge ingestion and retrieval interactions, multi-session isolation, and
coaching evaluation idempotence across 16 integration tests.
"""

import pytest
from tests.e2e.helpers import (
    assert_valid_session,
    assert_valid_message,
    assert_valid_agent_outputs,
    assert_valid_coaching_report,
    assert_valid_knowledge_document,
    create_test_session,
    send_test_message,
    upload_test_document,
)

pytestmark = pytest.mark.tier3


# ============================================================================
# 1. Session Mode Lifecycles (4 tests)
# ============================================================================

class TestLifecycleInteractions:
    """End-to-end multi-step lifecycles across simulator, manual, and replay modes."""

    def test_full_simulator_session_lifecycle(self, client):
        """Validates end-to-end simulator workflow: create -> employee turn -> simulated turn -> agent outputs -> report."""
        # 1. Create simulator session
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="ANC high-pitched buzzing in right ear cup.",
            persona="Angry",
        )
        sid = session["session_id"]
        assert_valid_session(session, expected_mode="simulator")

        # 2. Check initial customer message seeded
        res_msgs = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs.status_code == 200
        msgs = res_msgs.json()
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "customer"
        assert "buzzing" in msgs[0]["message_text"]

        # 3. Employee sends response
        send_res = send_test_message(
            client,
            sid,
            "I am sorry for the issue. Let me help you reset the headphones by holding the power button for 10 seconds.",
            sender="employee",
        )
        assert "saved_message" in send_res
        assert "simulated_customer_reply" in send_res
        assert send_res["simulated_customer_reply"] is not None
        assert send_res["simulated_customer_reply"]["sender"] == "customer"
        assert_valid_agent_outputs(send_res["agent_outputs"])

        # 4. Message history has 3 turns in chronological order
        res_msgs_2 = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs_2.status_code == 200
        history = res_msgs_2.json()
        assert len(history) == 3
        assert history[0]["sender"] == "customer"
        assert history[1]["sender"] == "employee"
        assert history[2]["sender"] == "customer"

        # 5. Session details returns populated agent_outputs
        res_detail = client.get(f"/api/sessions/{sid}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert_valid_agent_outputs(detail["agent_outputs"])

        # 6. Retrieve coaching report
        res_rep = client.get(f"/api/sessions/{sid}/coaching-report")
        assert res_rep.status_code == 200
        report = res_rep.json()
        assert_valid_coaching_report(report, expected_session_id=sid)
        assert report["evaluation_score"] >= 0

    def test_full_manual_mode_session_lifecycle(self, client):
        """Validates manual mode: employee & customer messages recorded without automated simulator replies."""
        # 1. Create manual session
        session = create_test_session(
            client,
            interaction_mode="manual",
            product_name="PulseWatch S4 Smartwatch",
            customer_scenario="Watch screen froze during outdoor run.",
            persona="Standard",
        )
        sid = session["session_id"]
        assert_valid_session(session, expected_mode="manual")

        # 2. Employee sends message -> no simulated customer reply
        emp_res = send_test_message(
            client,
            sid,
            "Hello, could you please tell me if the watch vibrates when pressing the crown?",
            sender="employee",
        )
        assert emp_res["simulated_customer_reply"] is None
        assert emp_res["saved_message"]["sender"] == "employee"

        # 3. Customer sends manual message -> no simulated reply
        cust_res = send_test_message(
            client,
            sid,
            "No, there is no vibration at all. The screen is black.",
            sender="customer",
        )
        assert cust_res["simulated_customer_reply"] is None
        assert cust_res["saved_message"]["sender"] == "customer"

        # 4. Employee sends follow-up
        send_test_message(
            client,
            sid,
            "Understood. Let's start an RMA process for a hardware warranty replacement.",
            sender="employee",
        )

        # 5. Verify conversation history has 4 messages
        res_msgs = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs.status_code == 200
        history = res_msgs.json()
        assert len(history) == 4
        senders = [m["sender"] for m in history]
        assert senders == ["customer", "employee", "customer", "employee"]

    def test_full_replay_mode_session_lifecycle(self, client):
        """Validates replay mode initialized with historical transcript data."""
        payload = {
            "interaction_mode": "replay",
            "product_name": "CloudDesk CRM Pro Subscription",
            "customer_scenario": "Duplicate charge on annual subscription invoice #INV-9021.",
            "persona": "Impatient",
            "replay_transcript": (
                "Customer: You billed us twice for our 25-seat license!\n"
                "Agent: I apologize for the error. I have processed an immediate refund."
            ),
        }
        res = client.post("/api/sessions", json=payload)
        assert res.status_code in (200, 201)
        session = res.json()
        assert_valid_session(session, expected_mode="replay")
        sid = session["session_id"]

        # Verify messages endpoint returns session conversation history
        res_msgs = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs.status_code == 200
        msgs = res_msgs.json()
        assert len(msgs) >= 1

    def test_session_status_transition(self, client):
        """Validates that a session maintains active status throughout a completed dialogue."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="ANC crackling sound.",
        )
        sid = session["session_id"]
        assert session["status"] == "active"

        # Send dialogue turns
        send_test_message(client, sid, "Let us reset the headset.", sender="employee")
        send_test_message(client, sid, "Issue resolved, closing session inquiry.", sender="employee")

        # Session remains retrievable and coherent
        detail_res = client.get(f"/api/sessions/{sid}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["status"] in ("active", "completed")


# ============================================================================
# 2. Knowledge Ingestion & Retrieval Interactions (4 tests)
# ============================================================================

class TestKnowledgeIngestionLifecycle:
    """Interactions between document upload, RAG ingestion, session queries, and deletion."""

    def test_knowledge_upload_ingest_retrieval_flow(self, client):
        """Uploads a troubleshooting document and validates it is listed and retrievable."""
        kb_text = (
            b"QuantumFirmware Error 99: When Bluetooth LED flashes magenta, "
            b"press the mute button 3 times rapidly to recalibrate the audio driver."
        )
        doc = upload_test_document(
            client,
            filename="quantum_firmware_err99.txt",
            content=kb_text,
            content_type="text/plain",
        )
        doc_id = doc["document_id"]
        assert_valid_knowledge_document(doc)

        # Confirm document appears in knowledge documents list
        list_res = client.get("/api/knowledge/documents")
        assert list_res.status_code == 200
        docs = list_res.json()
        doc_ids = [d["document_id"] for d in docs]
        assert doc_id in doc_ids

        # Create session and trigger message query
        session = create_test_session(
            client,
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="My headphones are showing QuantumFirmware Error 99.",
        )
        sid = session["session_id"]
        msg_res = send_test_message(
            client,
            sid,
            "Checking knowledge base for QuantumFirmware Error 99 resolution.",
            sender="employee",
        )
        assert_valid_agent_outputs(msg_res["agent_outputs"])
        assert "knowledge_retrieval" in msg_res["agent_outputs"]

    def test_knowledge_document_deletion_lifecycle(self, client):
        """Uploads document, verifies presence, deletes document, and verifies subsequent 404."""
        doc = upload_test_document(
            client,
            filename="temporary_delete_guide.txt",
            content=b"Temporary guide to be deleted.",
            content_type="text/plain",
        )
        doc_id = doc["document_id"]

        # Verify listed
        list_res = client.get("/api/knowledge/documents")
        assert any(d["document_id"] == doc_id for d in list_res.json())

        # Delete document
        del_res = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data.get("deleted") is True
        assert del_data.get("document_id") == doc_id

        # Verify absent from list
        list_res_after = client.get("/api/knowledge/documents")
        assert not any(d["document_id"] == doc_id for d in list_res_after.json())

        # Idempotent second delete returns 404
        second_del = client.delete(f"/api/knowledge/documents/{doc_id}")
        assert second_del.status_code == 404

    def test_multiple_knowledge_uploads_combined_retrieval(self, client):
        """Uploads multiple documents (TXT and PDF) and verifies both are cataloged."""
        doc1 = upload_test_document(
            client,
            filename="aerosound_anc_guide.txt",
            content=b"ANC Tuning: Recalibrate acoustic feedback loop in quiet room.",
            content_type="text/plain",
        )
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\nxref\n0 4\n"
            b"0000000000 65535 f \ntrailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n140\n%%EOF"
        )
        doc2 = upload_test_document(
            client,
            filename="aerosound_spec_sheet.pdf",
            content=pdf_bytes,
            content_type="application/pdf",
        )
        list_res = client.get("/api/knowledge/documents")
        assert list_res.status_code == 200
        doc_ids = [d["document_id"] for d in list_res.json()]
        assert doc1["document_id"] in doc_ids
        assert doc2["document_id"] in doc_ids

    def test_knowledge_upload_with_identical_filenames(self, client):
        """Uploading two documents with the same filename generates unique document IDs."""
        content = b"Knowledge article revision content."
        doc_a = upload_test_document(client, filename="faq_sheet.txt", content=content)
        doc_b = upload_test_document(client, filename="faq_sheet.txt", content=content)
        assert doc_a["document_id"] != doc_b["document_id"]

        list_res = client.get("/api/knowledge/documents")
        assert list_res.status_code == 200
        matching = [d for d in list_res.json() if d["filename"] == "faq_sheet.txt"]
        assert len(matching) >= 2


# ============================================================================
# 3. Multi-Session Isolation & Entity Consistency (2 tests)
# ============================================================================

class TestMultiSessionAndConcurrency:
    """Verifies isolation between multiple active sessions and entity integrity."""

    def test_multi_session_data_isolation(self, client):
        """Verifies messages and agent outputs from Session A do not leak into Session B."""
        session_a = create_test_session(
            client,
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="AeroSound ear cup broken.",
        )
        session_b = create_test_session(
            client,
            product_name="PulseWatch S4 Smartwatch",
            customer_scenario="PulseWatch battery drains fast.",
        )
        sid_a = session_a["session_id"]
        sid_b = session_b["session_id"]

        # Send 3 messages into Session A
        send_test_message(client, sid_a, "Turn 1 in AeroSound session", sender="employee")
        send_test_message(client, sid_a, "Turn 2 in AeroSound session", sender="employee")

        # Session B messages should remain clean (only its 1 initial customer turn)
        msgs_b = client.get(f"/api/sessions/{sid_b}/messages").json()
        assert len(msgs_b) == 1
        assert msgs_b[0]["session_id"] == sid_b
        assert "PulseWatch" in msgs_b[0]["message_text"]

        # Session A has its 5 messages (1 init + 2 employee + 2 simulated)
        msgs_a = client.get(f"/api/sessions/{sid_a}/messages").json()
        assert len(msgs_a) == 5
        for m in msgs_a:
            assert m["session_id"] == sid_a

    def test_session_product_lookup_consistency(self, client):
        """Verifies session detail binds to correct product information from catalog."""
        session = create_test_session(
            client,
            product_name="PulseWatch S4 Smartwatch",
            customer_scenario="PulseWatch screen problem.",
        )
        sid = session["session_id"]
        detail = client.get(f"/api/sessions/{sid}").json()
        assert detail["product_name"] == "PulseWatch S4 Smartwatch"
        assert "agent_outputs" in detail and detail["agent_outputs"] is not None
        pi = detail["agent_outputs"]["product_information"]
        assert pi["product_name"] == "PulseWatch S4 Smartwatch"


# ============================================================================
# 4. Turn Ordering & Simulation Invariants (3 tests)
# ============================================================================

class TestTurnOrderingAndSimulation:
    """Validates chronological ordering and simulator response behavior."""

    def test_consecutive_employee_messages_simulator(self, client):
        """Consecutive employee messages in simulator mode each trigger simulated customer turns."""
        session = create_test_session(client, interaction_mode="simulator")
        sid = session["session_id"]

        res1 = send_test_message(client, sid, "First employee reply", sender="employee")
        assert res1["simulated_customer_reply"] is not None

        res2 = send_test_message(client, sid, "Second employee follow-up reply", sender="employee")
        assert res2["simulated_customer_reply"] is not None

        # Conversation history has 5 messages: initial + emp1 + sim1 + emp2 + sim2
        history = client.get(f"/api/sessions/{sid}/messages").json()
        assert len(history) == 5
        expected_senders = ["customer", "employee", "customer", "employee", "customer"]
        actual_senders = [m["sender"] for m in history]
        assert actual_senders == expected_senders

    def test_consecutive_customer_messages_manual(self, client):
        """Consecutive customer messages in manual mode generate no simulated replies."""
        session = create_test_session(client, interaction_mode="manual")
        sid = session["session_id"]

        res1 = send_test_message(client, sid, "First customer message", sender="customer")
        assert res1["simulated_customer_reply"] is None

        res2 = send_test_message(client, sid, "Second customer message", sender="customer")
        assert res2["simulated_customer_reply"] is None

        history = client.get(f"/api/sessions/{sid}/messages").json()
        assert len(history) == 3
        actual_senders = [m["sender"] for m in history]
        assert actual_senders == ["customer", "customer", "customer"]

    def test_simulated_reply_timestamp_ordering(self, client):
        """Simulated customer reply timestamp is greater than or equal to employee message timestamp."""
        session = create_test_session(client, interaction_mode="simulator")
        sid = session["session_id"]
        res = send_test_message(client, sid, "Checking timestamp sequencing", sender="employee")
        emp_ts = res["saved_message"]["timestamp"]
        sim_ts = res["simulated_customer_reply"]["timestamp"]
        assert sim_ts >= emp_ts


# ============================================================================
# 5. Coaching Report & Sentiment Evolution (3 tests)
# ============================================================================

class TestCoachingAndSentimentProgression:
    """Validates coaching report generation, regeneration idempotence, and recommendations."""

    def test_coaching_report_regeneration_idempotence(self, client):
        """Requesting coaching report multiple times returns valid, coherent reports for the session."""
        session = create_test_session(client)
        sid = session["session_id"]
        send_test_message(client, sid, "Empathetic employee response", sender="employee")

        report1 = client.get(f"/api/sessions/{sid}/coaching-report").json()
        report2 = client.get(f"/api/sessions/{sid}/coaching-report").json()
        assert_valid_coaching_report(report1, expected_session_id=sid)
        assert_valid_coaching_report(report2, expected_session_id=sid)
        assert report1["session_id"] == report2["session_id"]
        assert 0 <= report1["evaluation_score"] <= 100

    def test_agent_outputs_sentiment_adaptation(self, client):
        """Agent outputs include valid query analysis and coaching tips adapted to session turns."""
        session = create_test_session(client, persona="Angry")
        sid = session["session_id"]
        res = send_test_message(
            client,
            sid,
            "I apologize sincerely for the frustration this buzzing noise caused.",
            sender="employee",
        )
        qa = res["agent_outputs"]["query_analysis"]
        assert "sentiment" in qa and len(qa["sentiment"]) > 0
        ec = res["agent_outputs"]["evaluation_and_coaching"]
        assert "tips" in ec and isinstance(ec["tips"], list)

    def test_coaching_report_recommendations_array_not_empty(self, client):
        """Coaching report contains non-empty lists for strengths, improvements, recommendations, and replies."""
        session = create_test_session(client)
        sid = session["session_id"]
        send_test_message(client, sid, "Standard resolution message.", sender="employee")
        report = client.get(f"/api/sessions/{sid}/coaching-report").json()
        assert_valid_coaching_report(report, expected_session_id=sid)
        assert len(report["strengths"]) > 0
        assert len(report["areas_for_improvement"]) > 0
        assert len(report["recommendations"]) > 0
        assert len(report["recommended_replies"]) > 0
