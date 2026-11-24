import json
import pytest
from unittest.mock import MagicMock, patch

from backend.app.llm.fallback_service import (
    FallbackLLMService,
    _sanitize_agent_outputs_dict,
    _sanitize_coaching_report_dict,
)
from backend.app.llm.mock_generator import (
    generate_mock_agent_outputs,
    generate_mock_customer_reply,
    generate_mock_coaching_report,
)
from backend.app.llm.prompts import (
    extract_json_from_response,
    format_conversation_history,
    format_rag_context,
    get_turn_guidance,
)
from backend.app.schemas.agent_outputs import AgentOutputs
from backend.app.schemas.message import MessageResponse
from backend.app.schemas.product import ProductResponse
from backend.app.schemas.report import CoachingReportResponse
from backend.app.schemas.session import SessionResponse


@pytest.fixture
def sample_session() -> SessionResponse:
    return SessionResponse(
        session_id="sess-fallback-001",
        interaction_mode="simulator",
        product_name="AeroSound Pro Headphones",
        product_context="Wireless ANC headphones with 40mm drivers",
        customer_scenario="Loud buzzing noise in left ear cup",
        persona="Angry",
        emotional_progression="escalating_to_calm",
        status="active",
        created_at="2026-11-23T12:00:00Z",
    )


@pytest.fixture
def sample_messages() -> list:
    return [
        MessageResponse(
            message_id="msg-1",
            session_id="sess-fallback-001",
            sender="customer",
            message_text="My headphones have a terrible buzzing noise! Order #ORD-88219.",
            timestamp="2026-11-23T12:00:10Z",
        ),
        MessageResponse(
            message_id="msg-2",
            session_id="sess-fallback-001",
            sender="employee",
            message_text="I am so sorry for the buzzing noise. I can process an express replacement right away.",
            timestamp="2026-11-23T12:00:30Z",
        ),
    ]


@pytest.fixture
def sample_product() -> ProductResponse:
    return ProductResponse(
        product_id="prod-101",
        product_name="AeroSound Pro Headphones",
        product_description="Flagship wireless headphones featuring active noise cancellation.",
        product_category="Audio",
    )


def test_unconfigured_keys_immediately_uses_mock(sample_session, sample_messages, sample_product):
    """When no LLM API keys are set, service defaults safely to mock without network calls."""
    svc = FallbackLLMService()
    # Ensure all provider keys are None
    with patch.object(svc, "_get_api_key", return_value=None):
        assert svc.get_active_provider_name() == "mock"
        outputs = svc.generate_agent_outputs(
            session=sample_session,
            messages=sample_messages,
            product=sample_product,
        )
        assert isinstance(outputs, AgentOutputs)
        assert outputs.supervisor.status == "Completed"
        assert outputs.supervisor.agents_completed == 6
        assert 0 <= outputs.evaluation_and_coaching.evaluation_score <= 100


def test_force_mock_flag_bypasses_all_providers(sample_session, sample_messages):
    """When force_mock=True, mock is used immediately even if keys are present."""
    svc = FallbackLLMService(force_mock=True)
    with patch.object(svc, "_get_api_key", return_value="fake_valid_key"):
        assert svc.get_active_provider_name() == "mock"
        outputs = svc.generate_agent_outputs(session=sample_session, messages=sample_messages)
        assert isinstance(outputs, AgentOutputs)


def test_fallback_chain_groq_failure_cascades_to_openai(sample_session, sample_messages):
    """When Groq fails with an error (e.g. 429 or 401), execution cascades to OpenAI."""
    svc = FallbackLLMService()

    # Simulate Groq and OpenAI keys configured
    def mock_get_api_key(provider):
        if provider in ("groq", "openai"):
            return "sk-test-key-12345"
        return None

    mock_openai_client = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.content = json.dumps({
        "supervisor": {"status": "Completed", "active_pattern": "OpenAI Chain", "agents_completed": 6},
        "query_analysis": {"summary": "Customer has buzzing noise", "intent": "Hardware Defect / Replacement", "sentiment": "Frustrated"},
        "knowledge_retrieval": {
            "summary": "Retrieved warranty manual",
            "articles": [{"title": "Warranty", "source": "docs/warranty.pdf", "relevance_score": 0.95, "snippet": "Covers buzzing"}],
            "faqs": [{"question": "Is replacement free?", "answer": "Yes"}],
            "troubleshooting_steps": ["Power cycle device"],
        },
        "product_information": {"product_name": "AeroSound Pro Headphones", "product_category": "Audio", "product_description": "ANC Headphones", "warranty_status": "Active"},
        "response_generation": {"suggested_response": "I apologize for the buzzing and will ship a replacement."},
        "evaluation_and_coaching": {"evaluation_score": 92, "tips": ["Great job apologizing."]},
    })
    mock_openai_client.invoke.return_value = mock_openai_response

    with patch.object(svc, "_get_api_key", side_effect=mock_get_api_key):
        with patch.object(svc, "_is_provider_installed", return_value=True):
            # Groq client raises exception when invoked
            def mock_get_client(provider):
                if provider == "groq":
                    mock_groq = MagicMock()
                    mock_groq.invoke.side_effect = RuntimeError("Groq 429 Rate Limit Exceeded")
                    return mock_groq
                elif provider == "openai":
                    return mock_openai_client
                raise ValueError(f"Unexpected provider: {provider}")

            with patch.object(svc, "_get_llm_client", side_effect=mock_get_client):
                # We need AGENT_OUTPUTS_PROMPT | client to invoke client
                with patch("backend.app.llm.fallback_service.AGENT_OUTPUTS_PROMPT") as mock_prompt:
                    # Let prompt | client return mock_openai_client directly
                    mock_prompt.__or__.side_effect = lambda client: client

                    outputs = svc.generate_agent_outputs(session=sample_session, messages=sample_messages)
                    assert isinstance(outputs, AgentOutputs)
                    assert outputs.supervisor.active_pattern == "OpenAI Chain"
                    assert outputs.evaluation_and_coaching.evaluation_score == 92


def test_fallback_chain_all_providers_fail_cascades_to_mock(sample_session, sample_messages):
    """When all external providers fail with exceptions, execution falls back cleanly to mock."""
    svc = FallbackLLMService()

    with patch.object(svc, "_get_api_key", return_value="sk-test-key-all-fail"):
        with patch.object(svc, "_is_provider_installed", return_value=True):
            with patch.object(svc, "_get_llm_client") as mock_get_client:
                failing_client = MagicMock()
                failing_client.invoke.side_effect = ConnectionError("Connection refused by provider API")
                mock_get_client.return_value = failing_client

                with patch("backend.app.llm.fallback_service.AGENT_OUTPUTS_PROMPT") as mock_prompt:
                    mock_prompt.__or__.side_effect = lambda client: client

                    outputs = svc.generate_agent_outputs(session=sample_session, messages=sample_messages)
                    assert isinstance(outputs, AgentOutputs)
                    assert outputs.supervisor.status == "Completed"
                    assert outputs.supervisor.agents_completed == 6
                    assert 0 <= outputs.evaluation_and_coaching.evaluation_score <= 100


def test_active_provider_name_selection():
    """Verifies get_active_provider_name picks the highest priority available provider."""
    svc = FallbackLLMService()

    # 1. Groq available
    with patch.object(svc, "_get_api_key", side_effect=lambda p: "key" if p in ("groq", "openai") else None):
        with patch.object(svc, "_is_provider_installed", return_value=True):
            assert svc.get_active_provider_name() == "groq"

    # 2. Only OpenAI available (Groq missing key)
    with patch.object(svc, "_get_api_key", side_effect=lambda p: "key" if p == "openai" else None):
        with patch.object(svc, "_is_provider_installed", return_value=True):
            assert svc.get_active_provider_name() == "openai"

    # 3. No keys available -> returns 'mock'
    with patch.object(svc, "_get_api_key", return_value=None):
        assert svc.get_active_provider_name() == "mock"


def test_missing_package_skipped_cleanly():
    """When a package is not installed (e.g. anthropic), it is skipped without error."""
    svc = FallbackLLMService()
    with patch.object(svc, "_get_api_key", return_value="sk-valid-key"):
        with patch.object(svc, "_is_provider_installed", side_effect=lambda p: p != "anthropic"):
            assert svc._is_provider_available("anthropic") is False


def test_markdown_json_fence_extraction():
    """Tests extraction of JSON from responses with code blocks, fences, and extraneous text."""
    # 1. Standard markdown json fence
    raw_1 = '```json\n{"supervisor": {"status": "Completed"}}\n```'
    assert extract_json_from_response(raw_1) == '{"supervisor": {"status": "Completed"}}'

    # 2. Markdown fence without json tag
    raw_2 = '```\n{"score": 90}\n```'
    assert extract_json_from_response(raw_2) == '{"score": 90}'

    # 3. Conversational text before and after
    raw_3 = 'Here is the analysis:\n```json\n{"status": "ok"}\n```\nHope this helps!'
    assert extract_json_from_response(raw_3) == '{"status": "ok"}'

    # 4. Bare JSON surrounded by text without fences
    raw_4 = 'Sure! {"intent": "Hardware Defect"} is the result.'
    assert extract_json_from_response(raw_4) == '{"intent": "Hardware Defect"}'

    # 5. Clean JSON
    raw_5 = '{"product": "Headphones"}'
    assert extract_json_from_response(raw_5) == '{"product": "Headphones"}'

    # 6. Empty string
    assert extract_json_from_response("") == ""


def test_mock_agent_outputs_schema_integrity(sample_session, sample_messages):
    """Verifies that generated mock AgentOutputs strictly adheres to all Pydantic constraints."""
    rag_chunks = [
        {"source": "kb/doc1.pdf", "score": 1.25, "content": "Content exceeding 1.0 score bound"},
        {"source": "kb/doc2.pdf", "score": -0.5, "content": "Content below 0.0 score bound"},
    ]
    outputs = generate_mock_agent_outputs(
        session=sample_session,
        messages=sample_messages,
        rag_context=rag_chunks,
    )

    assert isinstance(outputs, AgentOutputs)
    assert outputs.supervisor.status == "Completed"
    assert outputs.supervisor.agents_completed == 6
    assert 0 <= outputs.evaluation_and_coaching.evaluation_score <= 100
    assert len(outputs.evaluation_and_coaching.tips) > 0

    # Ensure relevance_score is clamped into [0.0, 1.0]
    for article in outputs.knowledge_retrieval.articles:
        assert 0.0 <= article.relevance_score <= 1.0

    assert outputs.query_analysis.intent == "Hardware Defect / Replacement"
    assert "AeroSound Pro Headphones" in outputs.product_information.product_name


def test_sanitize_agent_outputs_clamps_out_of_bound_values():
    """Verifies that _sanitize_agent_outputs_dict clamps scores and formats lists safely."""
    raw_dict = {
        "supervisor": {"status": "In Progress", "agents_completed": "6"},
        "query_analysis": {"summary": "Summary", "intent": "Defect", "sentiment": "Upset"},
        "knowledge_retrieval": {
            "summary": "KR summary",
            "articles": [{"title": "Art", "source": "src", "relevance_score": 2.5, "snippet": "Snip"}],
            "faqs": [{"question": "Q?", "answer": "A"}],
            "troubleshooting_steps": ["Step 1"],
        },
        "product_information": {"product_name": "Test Prod", "product_category": "Cat", "product_description": "Desc", "warranty_status": "Active"},
        "response_generation": {"suggested_response": "Hello"},
        "evaluation_and_coaching": {"evaluation_score": 150, "tips": ["Tip 1"]},
    }

    sanitized = _sanitize_agent_outputs_dict(raw_dict)
    assert sanitized.evaluation_and_coaching.evaluation_score == 100
    assert sanitized.knowledge_retrieval.articles[0].relevance_score == 1.0


def test_sanitize_coaching_report_clamps_out_of_bound_values():
    """Verifies that _sanitize_coaching_report_dict clamps evaluation score safely."""
    raw_dict = {
        "evaluation_score": -25,
        "conversation_summary": "Summary",
        "customer_sentiment": "Angry",
        "employee_evaluation": "Good",
        "strengths": ["Empathy"],
        "areas_for_improvement": ["SLA"],
        "recommendations": ["Playbook"],
        "recommended_replies": ["Reply"],
    }
    sanitized = _sanitize_coaching_report_dict(raw_dict, session_id="sess-test-999")
    assert sanitized.evaluation_score == 0
    assert sanitized.session_id == "sess-test-999"
    assert sanitized.report_id == "REP-999"


def test_sanitize_coaching_report_handles_explicit_none_and_null_fields():
    """Verifies that _sanitize_coaching_report_dict gracefully handles explicit None/null values."""
    raw_dict = {
        "report_id": None,
        "conversation_summary": None,
        "customer_sentiment": None,
        "evaluation_score": None,
        "employee_evaluation": None,
        "strengths": None,
        "areas_for_improvement": None,
        "recommendations": None,
        "recommended_replies": None,
    }
    sanitized = _sanitize_coaching_report_dict(raw_dict, session_id="sess-test-none001")
    assert isinstance(sanitized, CoachingReportResponse)
    assert sanitized.report_id == "REP-NONE001"
    assert sanitized.session_id == "sess-test-none001"
    assert sanitized.conversation_summary == ""
    assert sanitized.customer_sentiment == "Neutral -> Satisfied"
    assert sanitized.employee_evaluation == ""
    assert sanitized.evaluation_score == 85
    assert sanitized.strengths == []
    assert sanitized.areas_for_improvement == []
    assert sanitized.recommendations == []
    assert sanitized.recommended_replies == []

    # Also test with lists containing None or empty string elements
    raw_with_none_elements = {
        "strengths": ["Strong empathy", None, ""],
        "areas_for_improvement": [None, "Faster resolution", ""],
        "recommendations": ["Review manual", None],
        "recommended_replies": [None, "How can I assist today?"],
    }
    sanitized_elems = _sanitize_coaching_report_dict(raw_with_none_elements, session_id="sess-test-none002")
    assert sanitized_elems.strengths == ["Strong empathy"]
    assert sanitized_elems.areas_for_improvement == ["Faster resolution"]
    assert sanitized_elems.recommendations == ["Review manual"]
    assert sanitized_elems.recommended_replies == ["How can I assist today?"]


def test_sanitize_agent_outputs_handles_explicit_none_and_null_submodels():
    """Verifies that _sanitize_agent_outputs_dict gracefully handles top-level None submodels."""
    raw_dict = {
        "supervisor": None,
        "query_analysis": None,
        "knowledge_retrieval": None,
        "product_information": None,
        "response_generation": None,
        "evaluation_and_coaching": None,
    }
    sanitized = _sanitize_agent_outputs_dict(raw_dict)
    assert isinstance(sanitized, AgentOutputs)
    assert sanitized.supervisor.status == "Completed"
    assert sanitized.supervisor.agents_completed == 6
    assert sanitized.query_analysis.summary == ""
    assert sanitized.knowledge_retrieval.summary == ""
    assert sanitized.knowledge_retrieval.articles == []
    assert sanitized.knowledge_retrieval.faqs == []
    assert sanitized.knowledge_retrieval.troubleshooting_steps == []
    assert sanitized.product_information.product_name == ""
    assert sanitized.response_generation.suggested_response == ""
    assert sanitized.evaluation_and_coaching.evaluation_score == 80
    assert sanitized.evaluation_and_coaching.tips == []


def test_sanitize_agent_outputs_handles_nested_none_lists_and_non_numeric_values():
    """Verifies that _sanitize_agent_outputs_dict handles nested None lists and non-numeric agents_completed."""
    raw_dict = {
        "supervisor": {
            "status": None,
            "active_pattern": None,
            "agents_completed": "not_a_number_six",
        },
        "query_analysis": {
            "summary": None,
            "intent": None,
            "sentiment": None,
        },
        "knowledge_retrieval": {
            "summary": None,
            "articles": [
                None,
                {"title": "Valid Doc", "source": None, "relevance_score": None, "snippet": None},
                "invalid_non_dict_entry",
            ],
            "faqs": [
                None,
                {"question": "How to reset?", "answer": None},
                42,
            ],
            "troubleshooting_steps": ["Step 1: Check power", None, "", "Step 2: Re-pair bluetooth"],
        },
        "product_information": {
            "product_name": None,
            "product_category": None,
            "product_description": None,
            "warranty_status": None,
        },
        "response_generation": {
            "suggested_response": None,
        },
        "evaluation_and_coaching": {
            "evaluation_score": None,
            "tips": ["Tip 1: Active listening", None, ""],
        },
    }
    sanitized = _sanitize_agent_outputs_dict(raw_dict)
    assert isinstance(sanitized, AgentOutputs)
    assert sanitized.supervisor.status == "Completed"
    assert sanitized.supervisor.active_pattern == "Context-Aware LLM + RAG Retrieval"
    assert sanitized.supervisor.agents_completed == 6

    assert sanitized.query_analysis.intent == "General Product Inquiries / Support"
    assert sanitized.query_analysis.sentiment == "Neutral / Inquiring"

    assert len(sanitized.knowledge_retrieval.articles) == 1
    assert sanitized.knowledge_retrieval.articles[0].title == "Valid Doc"
    assert sanitized.knowledge_retrieval.articles[0].source == "knowledge_base"
    assert sanitized.knowledge_retrieval.articles[0].relevance_score == 0.8
    assert sanitized.knowledge_retrieval.articles[0].snippet == ""

    assert len(sanitized.knowledge_retrieval.faqs) == 1
    assert sanitized.knowledge_retrieval.faqs[0].question == "How to reset?"
    assert sanitized.knowledge_retrieval.faqs[0].answer == ""

    assert sanitized.knowledge_retrieval.troubleshooting_steps == [
        "Step 1: Check power",
        "Step 2: Re-pair bluetooth",
    ]

    assert sanitized.product_information.product_name == ""
    assert sanitized.product_information.product_category == "Audio & Electronics"
    assert sanitized.product_information.warranty_status == "Active — 1-Year Limited Warranty"

    assert sanitized.response_generation.suggested_response == ""

    assert sanitized.evaluation_and_coaching.evaluation_score == 80
    assert sanitized.evaluation_and_coaching.tips == ["Tip 1: Active listening"]
