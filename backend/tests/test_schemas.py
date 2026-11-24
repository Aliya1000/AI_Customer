import pytest
from pydantic import ValidationError
from backend.app.schemas.agent_outputs import (
    AgentOutputs,
    Article,
    EvaluationAndCoachingOutput,
    FAQ,
    KnowledgeRetrievalOutput,
    ProductInformationOutput,
    QueryAnalysisOutput,
    ResponseGenerationOutput,
    SupervisorOutput,
)
from backend.app.schemas.knowledge import (
    KnowledgeDocCreate,
    KnowledgeDocDeleteResponse,
    KnowledgeDocResponse,
)
from backend.app.schemas.message import (
    MessageCreate,
    MessageResponse,
    SendMessageResponse,
)
from backend.app.schemas.product import ProductCreate, ProductResponse
from backend.app.schemas.report import CoachingReportCreate, CoachingReportResponse
from backend.app.schemas.session import (
    PersonaType,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)


# ==============================================================================
# 1. Product Schemas
# ==============================================================================


def test_product_create_and_response_valid():
    create_dto = ProductCreate(
        product_name="AeroSound Pro ANC Headphones",
        product_description="Wireless ANC headphones with 1-year warranty.",
        product_category="Audio Hardware",
    )
    assert create_dto.product_id is None
    assert create_dto.product_name == "AeroSound Pro ANC Headphones"

    resp = ProductResponse(
        product_id="PRD-01",
        product_name=create_dto.product_name,
        product_description=create_dto.product_description,
        product_category=create_dto.product_category,
    )
    dumped = resp.model_dump()
    assert dumped["product_id"] == "PRD-01"
    assert resp.model_dump_json() is not None


def test_product_create_empty_fields_fail():
    with pytest.raises(ValidationError):
        ProductCreate(
            product_name="",
            product_description="Some desc",
            product_category="Hardware",
        )

    with pytest.raises(ValidationError):
        ProductCreate(
            product_name="Some Name",
            product_description="",
            product_category="Hardware",
        )


# ==============================================================================
# 2. Session Schemas
# ==============================================================================


def test_session_create_defaults_and_valid():
    session_data = SessionCreate(
        interaction_mode="simulator",
        product_name="PulseWatch S4",
        customer_scenario="Battery draining too fast after update",
    )
    assert session_data.interaction_mode == "simulator"
    assert session_data.persona == "Patient"
    assert session_data.product_context == ""
    assert session_data.emotional_progression is None
    assert session_data.replay_transcript is None


def test_session_create_invalid_mode_fails():
    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="invalid_mode",  # type: ignore
            product_name="PulseWatch S4",
            customer_scenario="Battery draining",
        )


def test_session_create_empty_strings_fail():
    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="manual",
            product_name="",
            customer_scenario="Scenario",
        )
    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="manual",
            product_name="Product",
            customer_scenario="",
        )


def test_session_create_whitespace_strings_fail():
    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="manual",
            product_name="   ",
            customer_scenario="Scenario",
        )
    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="manual",
            product_name="Product",
            customer_scenario="   ",
        )
    with pytest.raises(ValidationError):
        SessionUpdate(customer_scenario="   ")


def test_session_create_persona_validation():
    for persona in ["Angry", "Confused", "Impatient", "Patient", "Standard"]:
        sess = SessionCreate(
            interaction_mode="simulator",
            product_name="PulseWatch S4",
            customer_scenario="Battery draining",
            persona=persona,  # type: ignore
        )
        assert sess.persona == persona

    with pytest.raises(ValidationError):
        SessionCreate(
            interaction_mode="simulator",
            product_name="PulseWatch S4",
            customer_scenario="Battery draining",
            persona="TotallyInvalidPersona",  # type: ignore
        )

    with pytest.raises(ValidationError):
        SessionUpdate(persona="InvalidPersona")  # type: ignore


def test_session_update_valid_and_invalid():
    upd = SessionUpdate(status="completed", customer_scenario="Updated scenario")
    assert upd.status == "completed"
    assert upd.persona is None

    with pytest.raises(ValidationError):
        SessionUpdate(status="unknown_status")  # type: ignore


def test_session_response_full_serialization():
    data = {
        "session_id": "SES-2026-0001",
        "interaction_mode": "simulator",
        "product_name": "AeroSound Pro ANC Headphones",
        "product_context": "Purchased 14 days ago.",
        "customer_scenario": "Cracked left earcup",
        "persona": "Angry",
        "status": "active",
        "created_at": "2026-11-21T09:15:00Z",
    }
    resp = SessionResponse(**data)
    assert resp.session_id == "SES-2026-0001"
    assert resp.status == "active"
    assert resp.agent_outputs is None


# ==============================================================================
# 3. Message Schemas
# ==============================================================================


def test_message_create_valid_and_defaults():
    msg = MessageCreate(message_text="Hello, how can I help you?")
    assert msg.sender == "employee"
    assert msg.message_text == "Hello, how can I help you?"

    cust_msg = MessageCreate(sender="customer", message_text="My order is broken")
    assert cust_msg.sender == "customer"


def test_message_create_invalid_sender_or_empty_text():
    with pytest.raises(ValidationError):
        MessageCreate(sender="admin", message_text="Hi")  # type: ignore

    with pytest.raises(ValidationError):
        MessageCreate(sender="customer", message_text="")


def test_message_response_and_send_message_response(sample_agent_outputs):
    saved = MessageResponse(
        message_id="MSG-001",
        session_id="SES-2026-0001",
        sender="employee",
        message_text="We apologize for the inconvenience.",
        timestamp="2026-11-21T09:16:00Z",
    )
    reply = MessageResponse(
        message_id="MSG-002",
        session_id="SES-2026-0001",
        sender="customer",
        message_text="Thank you, my order is #ORD-1234.",
        timestamp="2026-11-21T09:16:15Z",
    )

    send_resp = SendMessageResponse(
        saved_message=saved,
        simulated_customer_reply=reply,
        agent_outputs=sample_agent_outputs,
    )
    assert send_resp.saved_message.message_id == "MSG-001"
    assert send_resp.simulated_customer_reply.sender == "customer"
    assert send_resp.agent_outputs.supervisor.agents_completed == 6


# ==============================================================================
# 4. Knowledge Document Schemas
# ==============================================================================


def test_knowledge_doc_create_valid():
    doc = KnowledgeDocCreate(
        filename="troubleshooting_guide.pdf",
        file_type="PDF",
    )
    assert doc.processing_status == "pending"
    assert doc.storage_path is None


def test_knowledge_doc_create_invalid_status_or_empty_filename():
    with pytest.raises(ValidationError):
        KnowledgeDocCreate(
            filename="",
            file_type="PDF",
        )
    with pytest.raises(ValidationError):
        KnowledgeDocCreate(
            filename="guide.pdf",
            file_type="PDF",
            processing_status="unsupported",  # type: ignore
        )


def test_knowledge_doc_response_and_delete_response():
    resp = KnowledgeDocResponse(
        document_id="DOC-101",
        filename="warranty_policy.pdf",
        file_type="PDF",
        upload_time="2026-11-15T10:00:00Z",
        processing_status="indexed",
        storage_path="DOC-101/warranty_policy.pdf",
    )
    assert resp.document_id == "DOC-101"

    del_resp = KnowledgeDocDeleteResponse(document_id="DOC-101")
    assert del_resp.deleted is True
    assert del_resp.document_id == "DOC-101"


# ==============================================================================
# 5. Coaching Report Schemas
# ==============================================================================


def test_coaching_report_create_valid_and_defaults():
    rep = CoachingReportCreate(
        session_id="SES-2026-0001",
        conversation_summary="Customer requested replacement for cracked earcup.",
        evaluation_score=85,
    )
    assert rep.customer_sentiment == "Neutral"
    assert rep.evaluation_score == 85
    assert rep.strengths == []
    assert rep.areas_for_improvement == []


def test_coaching_report_score_boundary_conditions():
    # Boundary 0
    r0 = CoachingReportCreate(
        session_id="SES-0",
        conversation_summary="Summary",
        evaluation_score=0,
    )
    assert r0.evaluation_score == 0

    # Boundary 100
    r100 = CoachingReportCreate(
        session_id="SES-100",
        conversation_summary="Summary",
        evaluation_score=100,
    )
    assert r100.evaluation_score == 100

    # Below 0
    with pytest.raises(ValidationError):
        CoachingReportCreate(
            session_id="SES-neg",
            conversation_summary="Summary",
            evaluation_score=-1,
        )

    # Above 100
    with pytest.raises(ValidationError):
        CoachingReportCreate(
            session_id="SES-high",
            conversation_summary="Summary",
            evaluation_score=101,
        )


def test_coaching_report_response_full_fixture():
    data = {
        "report_id": "REP-0001",
        "session_id": "SES-2026-0001",
        "conversation_summary": "Customer reported physical damage on arrival.",
        "customer_sentiment": "Angry (High Escalation Risk)",
        "evaluation_score": 84,
        "employee_evaluation": "Good empathy and quick response.",
        "strengths": ["Acknowledged defect quickly", "Offered replacement"],
        "areas_for_improvement": ["State 48-hour SLA upfront"],
        "recommendations": ["Follow DOA replacement workflow"],
        "recommended_replies": ["I apologize and will ship a replacement today."],
    }
    resp = CoachingReportResponse(**data)
    assert resp.report_id == "REP-0001"
    assert len(resp.strengths) == 2
    assert resp.evaluation_score == 84


# ==============================================================================
# 6. Agent Outputs Schemas
# ==============================================================================


@pytest.fixture
def sample_agent_outputs() -> AgentOutputs:
    return AgentOutputs(
        supervisor=SupervisorOutput(
            status="Completed",
            active_pattern="Context-Aware LLM + RAG Retrieval",
            agents_completed=6,
        ),
        query_analysis=QueryAnalysisOutput(
            summary="Customer inquiry regarding cracked earcup and static noise.",
            intent="Hardware Defect / Replacement",
            sentiment="Frustrated / Urgent",
        ),
        knowledge_retrieval=KnowledgeRetrievalOutput(
            summary="Retrieved warranty policy and de-escalation tips.",
            articles=[
                Article(
                    title="Warranty & Replacement Guide",
                    source="aerosound_warranty_and_doa_policy.pdf",
                    relevance_score=0.95,
                    snippet="30-day DOA qualifies for express dispatch.",
                )
            ],
            faqs=[
                FAQ(
                    question="Is return shipping covered?",
                    answer="Yes, prepaid label generated automatically.",
                )
            ],
            troubleshooting_steps=[
                "Acknowledge defect with empathy.",
                "Trigger express RMA.",
            ],
        ),
        product_information=ProductInformationOutput(
            product_name="AeroSound Pro ANC Headphones",
            product_category="Audio Hardware",
            product_description="Over-ear headphones with ANC.",
            warranty_status="Active — Eligible for Express Support",
        ),
        response_generation=ResponseGenerationOutput(
            suggested_response="I sincerely apologize for the cracked earcup. I have initiated an express replacement."
        ),
        evaluation_and_coaching=EvaluationAndCoachingOutput(
            evaluation_score=92,
            tips=["Strong empathetic opening.", "Mention replacement tracking."],
        ),
    )


def test_agent_outputs_hierarchy(sample_agent_outputs):
    dumped = sample_agent_outputs.model_dump()
    assert dumped["supervisor"]["status"] == "Completed"
    assert dumped["query_analysis"]["intent"] == "Hardware Defect / Replacement"
    assert len(dumped["knowledge_retrieval"]["articles"]) == 1
    assert dumped["knowledge_retrieval"]["articles"][0]["relevance_score"] == 0.95
    assert dumped["product_information"]["product_name"] == "AeroSound Pro ANC Headphones"
    assert dumped["evaluation_and_coaching"]["evaluation_score"] == 92


def test_article_relevance_score_boundaries():
    a0 = Article(
        title="Doc 0", source="src", relevance_score=0.0, snippet="Snippet"
    )
    assert a0.relevance_score == 0.0

    a1 = Article(
        title="Doc 1", source="src", relevance_score=1.0, snippet="Snippet"
    )
    assert a1.relevance_score == 1.0

    with pytest.raises(ValidationError):
        Article(
            title="Doc -0.1", source="src", relevance_score=-0.1, snippet="Snippet"
        )

    with pytest.raises(ValidationError):
        Article(
            title="Doc 1.1", source="src", relevance_score=1.1, snippet="Snippet"
        )
