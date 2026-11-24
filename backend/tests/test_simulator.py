import pytest

from backend.app.llm.coaching import CoachingService
from backend.app.llm.fallback_service import FallbackLLMService
from backend.app.llm.simulator import CustomerSimulator
from backend.app.schemas.message import MessageResponse
from backend.app.schemas.report import CoachingReportResponse
from backend.app.schemas.session import SessionResponse


def create_session(
    persona: str = "Standard",
    progression: str = "stable",
    scenario: str = "Hardware defect upon arrival",
) -> SessionResponse:
    return SessionResponse(
        session_id=f"sess-{persona.lower()}-001",
        interaction_mode="simulator",
        product_name="AeroSound Pro Headphones",
        product_context="Wireless ANC headphones",
        customer_scenario=scenario,
        persona=persona,
        emotional_progression=progression,
        status="active",
        created_at="2026-11-23T12:00:00Z",
    )


def test_all_five_personas_produce_distinct_replies():
    """Verifies that all 5 personas generate distinct, persona-specific customer replies."""
    sim = CustomerSimulator()
    personas = ["Angry", "Confused", "Impatient", "Patient", "Standard"]
    replies = {}

    for persona in personas:
        sess = create_session(persona=persona, progression="stable")
        reply = sim.generate_reply(session=sess, messages=[])
        replies[persona] = reply
        assert isinstance(reply, str)
        assert len(reply) > 20

    # Ensure all 5 persona replies are distinct strings
    unique_replies = set(replies.values())
    assert len(unique_replies) == 5

    # Check characteristic persona vocabulary
    assert any(w in replies["Angry"].lower() for w in ["unacceptable", "broken", "upset", "order"])
    assert any(w in replies["Confused"].lower() for w in ["confused", "instructions", "button", "press"])
    assert any(w in replies["Impatient"].lower() for w in ["rush", "hurry", "skip", "fast", "replacement"])
    assert any(w in replies["Patient"].lower() for w in ["thank you", "assisting", "troubleshooting", "please"])
    assert any(w in replies["Standard"].lower() for w in ["assistance", "help", "order"])


def test_emotional_progression_escalating_to_calm():
    """
    Verifies that escalating_to_calm begins with strong frustration/indignation
    and gradually de-escalates to cooperative appreciation across conversation turns.
    """
    sim = CustomerSimulator()
    sess = create_session(persona="Angry", progression="escalating_to_calm")

    # Turn 1: Initial employee response
    messages_turn_1 = [
        MessageResponse(
            message_id="m1",
            session_id=sess.session_id,
            sender="customer",
            message_text="My headphones arrived broken!",
            timestamp="2026-11-23T12:00:00Z",
        ),
        MessageResponse(
            message_id="m2",
            session_id=sess.session_id,
            sender="employee",
            message_text="I am so sorry to hear that. I can process a replacement right away.",
            timestamp="2026-11-23T12:00:15Z",
        ),
    ]
    reply_1 = sim.generate_reply(session=sess, messages=messages_turn_1)
    assert any(w in reply_1.lower() for w in ["extremely upset", "defective", "full price", "unacceptable"])

    # Turn 2: Second employee response (softening)
    messages_turn_2 = messages_turn_1 + [
        MessageResponse(
            message_id="m3",
            session_id=sess.session_id,
            sender="customer",
            message_text=reply_1,
            timestamp="2026-11-23T12:00:30Z",
        ),
        MessageResponse(
            message_id="m4",
            session_id=sess.session_id,
            sender="employee",
            message_text="No need to worry, you do not have to return it first. We will dispatch the new unit today.",
            timestamp="2026-11-23T12:00:45Z",
        ),
    ]
    reply_2 = sim.generate_reply(session=sess, messages=messages_turn_2)
    assert any(w in reply_2.lower() for w in ["thank you", "apology", "reassuring", "relief"])

    # Turn 3: Third employee response (fully de-escalated and appreciative)
    messages_turn_3 = messages_turn_2 + [
        MessageResponse(
            message_id="m5",
            session_id=sess.session_id,
            sender="customer",
            message_text=reply_2,
            timestamp="2026-11-23T12:01:00Z",
        ),
        MessageResponse(
            message_id="m6",
            session_id=sess.session_id,
            sender="employee",
            message_text="Your tracking number is 1Z99999. Thank you for your patience!",
            timestamp="2026-11-23T12:01:15Z",
        ),
    ]
    reply_3 = sim.generate_reply(session=sess, messages=messages_turn_3)
    assert any(w in reply_3.lower() for w in ["fair", "reasonable", "appreciate", "efficiently", "thank you"])


def test_emotional_progression_calm_to_frustrated():
    """
    Verifies that calm_to_frustrated begins measured and polite,
    escalates to irritation on turn 2, and reaches outrage/demanding refund on turn 3+.
    """
    sim = CustomerSimulator()
    sess = create_session(persona="Angry", progression="calm_to_frustrated")

    # Turn 1: Initial polite inquiry
    messages_turn_1 = [
        MessageResponse(
            message_id="m1",
            session_id=sess.session_id,
            sender="customer",
            message_text="Hello, I received my product today with an issue.",
            timestamp="2026-11-23T12:00:00Z",
        ),
        MessageResponse(
            message_id="m2",
            session_id=sess.session_id,
            sender="employee",
            message_text="Hello! Could you try power cycling the device?",
            timestamp="2026-11-23T12:00:15Z",
        ),
    ]
    reply_1 = sim.generate_reply(session=sess, messages=messages_turn_1)
    assert any(w in reply_1.lower() for w in ["hello", "received", "can you help"])

    # Turn 2: Growing irritation
    messages_turn_2 = messages_turn_1 + [
        MessageResponse(
            message_id="m3",
            session_id=sess.session_id,
            sender="customer",
            message_text=reply_1,
            timestamp="2026-11-23T12:00:30Z",
        ),
        MessageResponse(
            message_id="m4",
            session_id=sess.session_id,
            sender="employee",
            message_text="Now please verify the firmware version in your mobile app.",
            timestamp="2026-11-23T12:00:45Z",
        ),
    ]
    reply_2 = sim.generate_reply(session=sess, messages=messages_turn_2)
    assert any(w in reply_2.lower() for w in ["already tried", "too long", "needed this working"])

    # Turn 3: Full outrage / demand refund
    messages_turn_3 = messages_turn_2 + [
        MessageResponse(
            message_id="m5",
            session_id=sess.session_id,
            sender="customer",
            message_text=reply_2,
            timestamp="2026-11-23T12:01:00Z",
        ),
        MessageResponse(
            message_id="m6",
            session_id=sess.session_id,
            sender="employee",
            message_text="Please submit diagnostic logs before we can escalate.",
            timestamp="2026-11-23T12:01:15Z",
        ),
    ]
    reply_3 = sim.generate_reply(session=sess, messages=messages_turn_3)
    assert any(w in reply_3.lower() for w in ["ridiculous", "refund", "dispute", "done jumping", "immediately"])


def test_coaching_report_structure_and_score_bounds():
    """
    Verifies that CoachingService produces a complete CoachingReportResponse
    with all 10 schema fields populated and evaluation_score bounded in [0, 100].
    """
    coach = CoachingService()
    sess = create_session(persona="Patient", progression="stable")

    messages = [
        MessageResponse(
            message_id="m1",
            session_id=sess.session_id,
            sender="customer",
            message_text="Hello, my headphones are not connecting. Order #ORD-12390.",
            timestamp="2026-11-23T12:00:00Z",
        ),
        MessageResponse(
            message_id="m2",
            session_id=sess.session_id,
            sender="employee",
            message_text="I am so sorry to hear that! Let me replace this for you under warranty. Express delivery arrives in 2 business days.",
            timestamp="2026-11-23T12:00:20Z",
        ),
    ]

    report = coach.generate_report(session=sess, messages=messages)

    assert isinstance(report, CoachingReportResponse)
    assert report.session_id == sess.session_id
    assert report.report_id.startswith("REP-")
    assert 0 <= report.evaluation_score <= 100
    assert len(report.conversation_summary) > 10
    assert len(report.customer_sentiment) > 0
    assert len(report.employee_evaluation) > 20

    # Ensure list fields are non-empty lists of strings
    assert isinstance(report.strengths, list) and len(report.strengths) >= 2
    assert isinstance(report.areas_for_improvement, list) and len(report.areas_for_improvement) >= 1
    assert isinstance(report.recommendations, list) and len(report.recommendations) >= 1
    assert isinstance(report.recommended_replies, list) and len(report.recommended_replies) >= 1

    for s in report.strengths:
        assert isinstance(s, str) and len(s) > 0
    for r in report.recommended_replies:
        assert isinstance(r, str) and len(r) > 0


def test_coaching_report_empathy_and_sla_scoring_boost():
    """Verifies that employee responses with empathy and SLA clarity deterministically score higher."""
    coach = CoachingService()
    sess = create_session(persona="Angry", progression="escalating_to_calm")

    # Dialogue without empathy or SLA
    terse_messages = [
        MessageResponse(
            message_id="m1",
            session_id=sess.session_id,
            sender="employee",
            message_text="What is your serial number?",
            timestamp="2026-11-23T12:00:00Z",
        )
    ]
    terse_report = coach.generate_report(session=sess, messages=terse_messages)

    # Dialogue with empathy, resolution, and SLA
    rich_messages = [
        MessageResponse(
            message_id="m1",
            session_id=sess.session_id,
            sender="employee",
            message_text="I am truly sorry for the trouble. I will process a full replacement under warranty. It will arrive in 2 business days.",
            timestamp="2026-11-23T12:00:00Z",
        )
    ]
    rich_report = coach.generate_report(session=sess, messages=rich_messages)

    assert rich_report.evaluation_score > terse_report.evaluation_score
    assert rich_report.evaluation_score <= 100
