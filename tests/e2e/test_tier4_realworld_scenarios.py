"""Tier 4: Real-World Application Scenarios E2E Tests.

Validates complete end-to-end customer support workflows across 3 distinct problem domains:
1. Scenario A: Audio Hardware Support Flow (AeroSound Pro ANC) — 3 tests
2. Scenario B: Smartwatch Hardware Return / Warranty Flow (PulseWatch S4) — 3 tests
3. Scenario C: Enterprise SaaS Subscription & Billing Flow (CloudDesk CRM Pro) — 3 tests
Total: 9 comprehensive scenario tests.
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

pytestmark = pytest.mark.tier4


# ============================================================================
# Scenario A: Audio Hardware Support Flow (AeroSound Pro ANC)
# ============================================================================

class TestScenarioAAudioHardware:
    """Scenario A: Angry customer experiencing ANC buzzing noise after firmware update."""

    def test_scenario_a_session_setup_and_initial_state(self, client):
        """Step 1: Create session with angry customer complaining about ANC buzzing noise."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="AeroSound Pro ANC Headphones",
            product_context="Purchased 2 months ago, firmware v2.1 installed yesterday.",
            customer_scenario="ANC is producing a high-pitched buzzing noise in the right ear cup after firmware update 2.1.",
            persona="Angry",
            emotional_progression="escalating_to_calm",
        )
        sid = session["session_id"]
        assert_valid_session(session, expected_mode="simulator")
        assert session["product_name"] == "AeroSound Pro ANC Headphones"

        # Verify initial customer complaint is seeded in message history
        res_msgs = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs.status_code == 200
        msgs = res_msgs.json()
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "customer"
        assert "buzzing" in msgs[0]["message_text"]

        # Verify session details provide product context
        res_detail = client.get(f"/api/sessions/{sid}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert "agent_outputs" in detail and detail["agent_outputs"] is not None
        pi = detail["agent_outputs"]["product_information"]
        assert "AeroSound" in pi["product_name"]

    def test_scenario_a_multiturn_troubleshooting_conversation(self, client):
        """Step 2: Multi-turn dialogue: empathy + reset instructions -> replacement escalation."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="ANC is producing a high-pitched buzzing noise in the right ear cup after firmware update 2.1.",
            persona="Angry",
        )
        sid = session["session_id"]

        # Turn 1: Employee responds with empathy and factory reset steps
        turn1_res = send_test_message(
            client,
            sid,
            "I sincerely apologize for the unpleasant buzzing noise in your AeroSound Pro headphones. "
            "Let's perform a 10-second factory reset by holding the power and ANC buttons together.",
            sender="employee",
        )
        assert turn1_res["simulated_customer_reply"] is not None
        assert turn1_res["simulated_customer_reply"]["sender"] == "customer"
        assert_valid_agent_outputs(turn1_res["agent_outputs"])

        # Turn 2: Employee offers express warranty replacement
        turn2_res = send_test_message(
            client,
            sid,
            "Since the reset did not resolve the ANC buzzing, your device is covered under our 1-year warranty. "
            "I will initiate an immediate express replacement order for a new unit.",
            sender="employee",
        )
        assert turn2_res["simulated_customer_reply"] is not None
        assert turn2_res["simulated_customer_reply"]["sender"] == "customer"

        # Verify conversation history has 5 turns in sequential order
        res_msgs = client.get(f"/api/sessions/{sid}/messages")
        assert res_msgs.status_code == 200
        history = res_msgs.json()
        assert len(history) == 5
        senders = [m["sender"] for m in history]
        assert senders == ["customer", "employee", "customer", "employee", "customer"]

    def test_scenario_a_coaching_report_evaluation(self, client):
        """Step 3: Evaluate employee performance and coaching recommendations for Scenario A."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="AeroSound Pro ANC Headphones",
            customer_scenario="ANC buzzing defect post update.",
            persona="Angry",
        )
        sid = session["session_id"]

        # Run troubleshooting dialogue
        send_test_message(
            client,
            sid,
            "I understand how frustrating that buzzing noise is. Let me initiate a warranty replacement.",
            sender="employee",
        )

        res_rep = client.get(f"/api/sessions/{sid}/coaching-report")
        assert res_rep.status_code == 200
        report = res_rep.json()
        assert_valid_coaching_report(report, expected_session_id=sid)
        assert report["evaluation_score"] >= 70
        assert len(report["strengths"]) > 0
        assert len(report["recommended_replies"]) > 0


# ============================================================================
# Scenario B: Smartwatch Hardware Return / Warranty Flow (PulseWatch S4)
# ============================================================================

class TestScenarioBSmartwatchWearable:
    """Scenario B: Impatient customer reporting smartwatch screen failure after swimming in pool."""

    def test_scenario_b_session_setup_and_kb_context(self, client):
        """Step 1: Ingest 5ATM water resistance documentation and create PulseWatch S4 session."""
        specs_doc = (
            b"PulseWatch S4 Water Resistance Specifications:\n"
            b"- Rated 5ATM (50 meters static water pressure ISO 22810:2010).\n"
            b"- Suitable for shallow-water swimming in pools or ocean.\n"
            b"- Warranty covers liquid ingress under standard swimming conditions within 1 year.\n"
            b"- Diagnostic procedure: Check water indicator seal inside SIM/charging port."
        )
        doc = upload_test_document(
            client,
            filename="pulsewatch_s4_water_resistance.txt",
            content=specs_doc,
            content_type="text/plain",
        )
        assert_valid_knowledge_document(doc)

        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="PulseWatch S4 Smartwatch",
            product_context="Purchased 3 weeks ago for triathlon training.",
            customer_scenario="Watch screen went completely dark and stopped charging after swimming in a 2-meter pool.",
            persona="Impatient",
        )
        sid = session["session_id"]
        assert_valid_session(session, expected_mode="simulator")
        assert session["product_name"] == "PulseWatch S4 Smartwatch"

    def test_scenario_b_warranty_and_water_resistance_dialogue(self, client):
        """Step 2: Impatient dialogue: swimming depth inquiry -> 5ATM explanation & warranty diagnostic."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="PulseWatch S4 Smartwatch",
            customer_scenario="Watch screen went completely dark and stopped charging after swimming in a 2-meter pool.",
            persona="Impatient",
        )
        sid = session["session_id"]

        # Employee Turn 1: Clarify conditions with empathy
        turn1 = send_test_message(
            client,
            sid,
            "I am sorry your PulseWatch S4 screen failed. The watch is rated 5ATM for pool swimming. "
            "Did the watch experience high-velocity water sports or hot steam?",
            sender="employee",
        )
        assert turn1["simulated_customer_reply"] is not None
        assert turn1["simulated_customer_reply"]["sender"] == "customer"

        # Employee Turn 2: Authorize warranty replacement
        turn2 = send_test_message(
            client,
            sid,
            "Normal 2-meter swimming is 100% covered by your 5ATM warranty. "
            "I have generated your prepaid RMA label #RMA-7742 to inspect and replace the device.",
            sender="employee",
        )
        assert turn2["simulated_customer_reply"] is not None

        # Verify chronological messages
        history = client.get(f"/api/sessions/{sid}/messages").json()
        assert len(history) == 5

    def test_scenario_b_coaching_report_accuracy(self, client):
        """Step 3: Coaching report reflects technical knowledge of 5ATM rating and warranty process."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="PulseWatch S4 Smartwatch",
            customer_scenario="Water damage after pool swim.",
            persona="Impatient",
        )
        sid = session["session_id"]
        send_test_message(
            client,
            sid,
            "I apologize for the failure. Since 5ATM covers pool swimming, we will replace the watch under warranty.",
            sender="employee",
        )

        res_rep = client.get(f"/api/sessions/{sid}/coaching-report")
        assert res_rep.status_code == 200
        report = res_rep.json()
        assert_valid_coaching_report(report, expected_session_id=sid)
        assert report["evaluation_score"] >= 70
        assert isinstance(report["strengths"], list)


# ============================================================================
# Scenario C: SaaS CRM Subscription & Billing Flow (CloudDesk CRM Pro)
# ============================================================================

class TestScenarioCSaaSEnterpriseCRM:
    """Scenario C: IT administrator requesting SAML 2.0 SSO guide and invoice for adding 25 team seats."""

    def test_scenario_c_session_setup_and_sso_doc_upload(self, client):
        """Step 1: Upload SAML SSO configuration JSON guide and initialize enterprise session."""
        sso_json = (
            b'{\n'
            b'  "feature": "SAML 2.0 SSO",\n'
            b'  "supported_idps": ["Okta", "Azure AD", "Google Workspace", "PingIdentity"],\n'
            b'  "acs_url": "https://auth.clouddesk.io/saml/consume",\n'
            b'  "entity_id": "https://auth.clouddesk.io/saml/metadata",\n'
            b'  "seat_pricing": {"tier": "Enterprise Pro", "price_per_seat_monthly": 45.00}\n'
            b'}'
        )
        doc = upload_test_document(
            client,
            filename="clouddesk_sso_guide.json",
            content=sso_json,
            content_type="application/json",
        )
        assert_valid_knowledge_document(doc)

        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="CloudDesk CRM Pro Subscription",
            product_context="Annual Enterprise Plan, currently 50 seats.",
            customer_scenario="Enterprise IT admin requesting SAML 2.0 SSO configuration guide and invoice for adding 25 team seats.",
            persona="Standard",
        )
        sid = session["session_id"]
        assert_valid_session(session, expected_mode="simulator")
        assert session["product_name"] == "CloudDesk CRM Pro Subscription"

    def test_scenario_c_enterprise_inquiry_multiturn(self, client):
        """Step 2: Multi-turn enterprise inquiry covering SSO setup instructions and 25-seat invoice."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="CloudDesk CRM Pro Subscription",
            customer_scenario="Enterprise IT admin requesting SAML 2.0 SSO configuration guide and invoice for adding 25 team seats.",
            persona="Standard",
        )
        sid = session["session_id"]

        # Employee Turn 1: Share SSO configuration guide details
        turn1 = send_test_message(
            client,
            sid,
            "Hello! You can configure SAML 2.0 SSO under Admin Settings > Security with ACS URL: "
            "https://auth.clouddesk.io/saml/consume. We support Okta, Azure AD, and Google Workspace.",
            sender="employee",
        )
        assert turn1["simulated_customer_reply"] is not None
        assert turn1["simulated_customer_reply"]["sender"] == "customer"
        assert_valid_agent_outputs(turn1["agent_outputs"])

        # Employee Turn 2: Address the 25-seat expansion invoice
        turn2 = send_test_message(
            client,
            sid,
            "For your 25 additional seats at $45/seat/month pro-rated, I have generated invoice #INV-25-ENTERPRISE "
            "and sent it to your billing email.",
            sender="employee",
        )
        assert turn2["simulated_customer_reply"] is not None

        # Verify 5 turns in messages history
        history = client.get(f"/api/sessions/{sid}/messages").json()
        assert len(history) == 5

    def test_scenario_c_coaching_report_enterprise_professionalism(self, client):
        """Step 3: Coaching report evaluates enterprise professionalism, accuracy, and tone."""
        session = create_test_session(
            client,
            interaction_mode="simulator",
            product_name="CloudDesk CRM Pro Subscription",
            customer_scenario="Enterprise IT admin SSO configuration and seat invoice inquiry.",
            persona="Standard",
        )
        sid = session["session_id"]
        send_test_message(
            client,
            sid,
            "Thank you for contacting CloudDesk Enterprise Support. Here is your SSO setup guide and seat invoice.",
            sender="employee",
        )

        res_rep = client.get(f"/api/sessions/{sid}/coaching-report")
        assert res_rep.status_code == 200
        report = res_rep.json()
        assert_valid_coaching_report(report, expected_session_id=sid)
        assert report["evaluation_score"] >= 75
        assert len(report["strengths"]) > 0
        assert len(report["recommendations"]) > 0
