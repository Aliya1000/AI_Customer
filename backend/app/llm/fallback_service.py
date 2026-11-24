import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, TypeVar

from backend.app.config import settings
from backend.app.llm.mock_generator import (
    generate_mock_agent_outputs,
    generate_mock_customer_reply,
    generate_mock_coaching_report,
)
from backend.app.llm.prompts import (
    AGENT_OUTPUTS_PROMPT,
    COACHING_REPORT_PROMPT,
    SIMULATOR_PROMPT,
    agent_outputs_parser,
    coaching_report_parser,
    extract_json_from_response,
    format_conversation_history,
    format_rag_context,
    get_turn_guidance,
)
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
from backend.app.schemas.report import CoachingReportResponse

logger = logging.getLogger("backend.app.llm.fallback_service")

T = TypeVar("T")


def _get_field(obj: Any, key: str, default: Any = "") -> Any:
    """Helper to extract a field from a dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _clean_content(content: Any) -> str:
    """Converts LLM response content into a clean string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Handles list of content parts/blocks
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
        return "\n".join(parts)
    return str(content) if content is not None else ""


def _sanitize_agent_outputs_dict(raw: Dict[str, Any]) -> AgentOutputs:
    """Sanitizes raw parsed dictionary into valid AgentOutputs satisfying all bounds."""
    # 1. Supervisor
    sup_raw = raw.get("supervisor") or {}
    try:
        raw_agents = sup_raw.get("agents_completed")
        agents_completed = int(raw_agents if raw_agents is not None else 6)
    except (ValueError, TypeError):
        agents_completed = 6

    supervisor = SupervisorOutput(
        status=str(sup_raw.get("status") or "Completed"),
        active_pattern=str(sup_raw.get("active_pattern") or "Context-Aware LLM + RAG Retrieval"),
        agents_completed=agents_completed,
    )

    # 2. Query Analysis
    qa_raw = raw.get("query_analysis") or {}
    query_analysis = QueryAnalysisOutput(
        summary=str(qa_raw.get("summary") or ""),
        intent=str(qa_raw.get("intent") or "General Product Inquiries / Support"),
        sentiment=str(qa_raw.get("sentiment") or "Neutral / Inquiring"),
    )

    # 3. Knowledge Retrieval
    kr_raw = raw.get("knowledge_retrieval") or {}
    articles: List[Article] = []
    articles_raw = kr_raw.get("articles") or []
    for art in articles_raw:
        if not isinstance(art, dict):
            continue
        try:
            raw_score = art.get("relevance_score")
            score = float(raw_score if raw_score is not None else 0.8)
        except (ValueError, TypeError):
            score = 0.8
        articles.append(Article(
            title=str(art.get("title") or "Resource"),
            source=str(art.get("source") or "knowledge_base"),
            relevance_score=min(max(score, 0.0), 1.0),
            snippet=str(art.get("snippet") or ""),
        ))
    
    faqs: List[FAQ] = []
    faqs_raw = kr_raw.get("faqs") or []
    for f in faqs_raw:
        if not isinstance(f, dict):
            continue
        faqs.append(FAQ(
            question=str(f.get("question") or ""),
            answer=str(f.get("answer") or ""),
        ))

    troubleshooting_steps = [str(s) for s in (kr_raw.get("troubleshooting_steps") or []) if s]

    knowledge_retrieval = KnowledgeRetrievalOutput(
        summary=str(kr_raw.get("summary") or ""),
        articles=articles,
        faqs=faqs,
        troubleshooting_steps=troubleshooting_steps,
    )

    # 4. Product Information
    pi_raw = raw.get("product_information") or {}
    product_information = ProductInformationOutput(
        product_name=str(pi_raw.get("product_name") or ""),
        product_category=str(pi_raw.get("product_category") or "Audio & Electronics"),
        product_description=str(pi_raw.get("product_description") or ""),
        warranty_status=str(pi_raw.get("warranty_status") or "Active — 1-Year Limited Warranty"),
    )

    # 5. Response Generation
    rg_raw = raw.get("response_generation") or {}
    response_generation = ResponseGenerationOutput(
        suggested_response=str(rg_raw.get("suggested_response") or ""),
    )

    # 6. Evaluation and Coaching
    ec_raw = raw.get("evaluation_and_coaching") or {}
    try:
        raw_score = ec_raw.get("evaluation_score")
        score_val = int(raw_score if raw_score is not None else 80)
    except (ValueError, TypeError):
        score_val = 80
    evaluation_score = min(max(score_val, 0), 100)
    tips = [str(t) for t in (ec_raw.get("tips") or []) if t]

    evaluation_and_coaching = EvaluationAndCoachingOutput(
        evaluation_score=evaluation_score,
        tips=tips,
    )

    return AgentOutputs(
        supervisor=supervisor,
        query_analysis=query_analysis,
        knowledge_retrieval=knowledge_retrieval,
        product_information=product_information,
        response_generation=response_generation,
        evaluation_and_coaching=evaluation_and_coaching,
    )


def _sanitize_coaching_report_dict(raw: Dict[str, Any], session_id: str) -> CoachingReportResponse:
    """Sanitizes raw parsed dictionary into valid CoachingReportResponse satisfying all bounds."""
    short_id = session_id.split("-")[-1] if "-" in session_id else session_id[:8]
    default_report_id = f"REP-{short_id.upper()}"
    report_id = str(raw.get("report_id") or default_report_id)

    try:
        raw_score = raw.get("evaluation_score")
        score_val = int(raw_score if raw_score is not None else 85)
    except (ValueError, TypeError):
        score_val = 85
    evaluation_score = min(max(score_val, 0), 100)

    return CoachingReportResponse(
        report_id=report_id,
        session_id=session_id,
        conversation_summary=str(raw.get("conversation_summary") or ""),
        customer_sentiment=str(raw.get("customer_sentiment") or "Neutral -> Satisfied"),
        evaluation_score=evaluation_score,
        employee_evaluation=str(raw.get("employee_evaluation") or ""),
        strengths=[str(s) for s in (raw.get("strengths") or []) if s],
        areas_for_improvement=[str(s) for s in (raw.get("areas_for_improvement") or []) if s],
        recommendations=[str(s) for s in (raw.get("recommendations") or []) if s],
        recommended_replies=[str(s) for s in (raw.get("recommended_replies") or []) if s],
    )


class FallbackLLMService:
    """
    Multi-provider LLM Inference Service with resilient fallback cascade:
    Groq (llama-3.3-70b-versatile)
      -> OpenAI (gpt-4o-mini)
      -> Anthropic (claude-3-5-haiku-20241022)
      -> Gemini (gemini-2.0-flash)
      -> Deterministic Mock Fallback.
    """

    def __init__(
        self,
        force_mock: bool = False,
        providers: Optional[List[str]] = None,
        model_names: Optional[Dict[str, str]] = None,
    ):
        self.force_mock = force_mock
        self.providers = providers or ["groq", "openai", "anthropic", "gemini", "mock"]
        self.model_names = model_names or {
            "groq": getattr(settings, "groq_model", "qwen/qwen3.8-27b") or "qwen/qwen3.8-27b",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "gemini": "gemini-2.0-flash",
        }

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Retrieves and checks API key for provider."""
        key: Optional[str] = None
        if provider == "groq":
            key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
        elif provider == "openai":
            key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        elif provider == "anthropic":
            key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        elif provider == "gemini":
            key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        
        if key and isinstance(key, str):
            k = key.strip()
            if k and not k.startswith("your_") and not k.startswith("placeholder"):
                return k
        return None

    def _is_provider_installed(self, provider: str) -> bool:
        """Checks if required library is importable without top-level module errors."""
        try:
            if provider == "groq":
                import langchain_groq  # noqa: F401
                return True
            elif provider == "openai":
                import langchain_openai  # noqa: F401
                return True
            elif provider == "anthropic":
                import langchain_anthropic  # noqa: F401
                return True
            elif provider == "gemini":
                import langchain_google_genai  # noqa: F401
                return True
        except ImportError:
            return False
        return False

    def _is_provider_available(self, provider: str) -> bool:
        """Provider is available if it has an API key and required package is installed."""
        if provider == "mock":
            return True
        if not self._get_api_key(provider):
            return False
        return self._is_provider_installed(provider)

    def get_active_provider_name(self) -> str:
        """Returns the name of the first available provider or 'mock'."""
        if self.force_mock:
            return "mock"
        for provider in self.providers:
            if provider == "mock":
                return "mock"
            if self._is_provider_available(provider):
                return provider
        return "mock"

    def _get_llm_client(self, provider: str) -> Any:
        """Instantiates client for the given provider."""
        key = self._get_api_key(provider)
        if not key:
            raise ValueError(f"No valid API key configured for provider '{provider}'")

        if provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=self.model_names.get("groq", "qwen/qwen3.8-27b"),
                api_key=key,
                temperature=0.1,
            )
        elif provider == "openai":

            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=self.model_names.get("openai", "gpt-4o-mini"),
                api_key=key,
                temperature=0.1,
            )
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self.model_names.get("anthropic", "claude-3-5-haiku-20241022"),
                    api_key=key,
                    temperature=0.1,
                )
            except ImportError as err:
                raise RuntimeError("langchain-anthropic is not installed") from err
        elif provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=self.model_names.get("gemini", "gemini-2.0-flash"),
                    google_api_key=key,
                    temperature=0.1,
                )
            except ImportError as err:
                raise RuntimeError("langchain-google-genai is not installed") from err
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _invoke_with_fallback(
        self,
        run_provider_fn: Callable[[str], T],
        mock_fn: Callable[[], T],
    ) -> T:
        """
        Executes operation across cascade of providers, falling back gracefully
        upon missing keys, missing packages, network/auth errors, or JSON parse failures.
        """
        if self.force_mock:
            logger.info("force_mock is active; executing deterministic mock fallback.")
            return mock_fn()

        for provider in self.providers:
            if provider == "mock":
                if settings.environment == "production" and not self.force_mock:
                    raise RuntimeError(
                        "Production Mode Error: Live LLM inference is required, but all configured providers "
                        "(Groq, OpenAI, Anthropic, Gemini) failed or were unconfigured. Mock responses are disabled in production."
                    )
                return mock_fn()

            if not self._is_provider_available(provider):
                continue

            try:
                logger.info(f"Executing LLM inference via provider: '{provider}'")
                result = run_provider_fn(provider)
                return result

                
            except Exception as exc:
                logger.warning(
                    f"Provider '{provider}' failed with {type(exc).__name__}: {exc}. "
                    f"Proceeding to next provider in fallback cascade."
                )
                continue

        if settings.environment == "production" and not self.force_mock:
            raise RuntimeError(
                "Production Mode Error: Live LLM inference is required, but all configured providers "
                "(Groq, OpenAI, Anthropic, Gemini) failed or were unconfigured. Mock responses are disabled in production."
            )
        logger.info("All providers unconfigured or failed; falling back to deterministic mock.")
        return mock_fn()

    def generate_agent_outputs(
        self,
        session: Any,
        messages: Optional[List[Any]] = None,
        rag_context: Optional[List[Any]] = None,
        product: Optional[Any] = None,
    ) -> AgentOutputs:
        """
        Runs single context-aware LangChain LLM pipeline synthesizing session history,
        product catalog information, and retrieved RAG context into structured AgentOutputs.
        Falls back through provider chain to deterministic mock generator.
        """
        msgs = messages or []
        session_id = _get_field(session, "session_id") or "sess-default"
        product_name = _get_field(session, "product_name") or "Product"
        product_context = _get_field(session, "product_context") or ""
        customer_scenario = _get_field(session, "customer_scenario") or "General inquiry"
        persona = _get_field(session, "persona") or "Patient"
        progression = _get_field(session, "emotional_progression") or "stable"
        interaction_mode = _get_field(session, "interaction_mode") or "simulator"

        product_category = _get_field(product, "product_category") or "Audio & Electronics"
        product_description = _get_field(product, "product_description") or product_context or f"Premium {product_name}."

        formatted_history = format_conversation_history(msgs)
        formatted_rag = format_rag_context(rag_context)
        format_instructions = agent_outputs_parser.get_format_instructions()

        prompt_values = {
            "interaction_mode": interaction_mode,
            "product_name": product_name,
            "product_context": product_context,
            "customer_scenario": customer_scenario,
            "persona": persona,
            "emotional_progression": progression,
            "product_category": product_category,
            "product_description": product_description,
            "rag_context": formatted_rag,
            "conversation_history": formatted_history,
            "format_instructions": format_instructions,
        }

        def run_provider(provider: str) -> AgentOutputs:
            client = self._get_llm_client(provider)
            chain = AGENT_OUTPUTS_PROMPT | client
            response = chain.invoke(prompt_values)
            raw_text = _clean_content(response.content)
            json_str = extract_json_from_response(raw_text)

            # Try parsing with Pydantic parser first
            try:
                parsed = agent_outputs_parser.parse(json_str)
                return parsed
            except Exception:
                # Fallback to json dict + sanitizer
                data = json.loads(json_str)
                return _sanitize_agent_outputs_dict(data)

        def run_mock() -> AgentOutputs:
            return generate_mock_agent_outputs(
                session=session,
                messages=msgs,
                rag_context=rag_context,
                product=product,
            )

        return self._invoke_with_fallback(run_provider, run_mock)

    def generate_customer_reply(
        self,
        session: Any,
        messages: Optional[List[Any]] = None,
    ) -> str:
        """
        Generates simulated customer reply via LLM with fallback.
        Adheres to customer persona, emotional progression mode, and current turn count.
        """
        msgs = messages or []
        product_name = _get_field(session, "product_name") or "Product"
        customer_scenario = _get_field(session, "customer_scenario") or "General inquiry"
        persona = _get_field(session, "persona") or "Patient"
        progression = _get_field(session, "emotional_progression") or "stable"

        employee_turns = sum(1 for m in msgs if (_get_field(m, "sender") or _get_field(m, "role", "")).lower() == "employee")
        turn_number = max(employee_turns, 1)
        turn_guidance = get_turn_guidance(persona, progression, turn_number)
        formatted_history = format_conversation_history(msgs)

        prompt_values = {
            "product_name": product_name,
            "customer_scenario": customer_scenario,
            "persona": persona,
            "emotional_progression": progression,
            "turn_number": turn_number,
            "turn_guidance": turn_guidance,
            "conversation_history": formatted_history,
        }

        def run_provider(provider: str) -> str:
            client = self._get_llm_client(provider)
            chain = SIMULATOR_PROMPT | client
            response = chain.invoke(prompt_values)
            raw_text = _clean_content(response.content).strip()
            # Clean common prefixes like "Customer: "
            cleaned = raw_text
            if cleaned.lower().startswith("customer:"):
                cleaned = cleaned[len("customer:") :].strip()
            cleaned = cleaned.strip('"').strip("'").strip()
            if not cleaned:
                raise ValueError("Empty reply received from LLM")
            return cleaned

        def run_mock() -> str:
            return generate_mock_customer_reply(
                session=session,
                messages=msgs,
            )

        return self._invoke_with_fallback(run_provider, run_mock)

    def generate_coaching_report(
        self,
        session: Any,
        messages: Optional[List[Any]] = None,
    ) -> CoachingReportResponse:
        """
        Generates comprehensive CoachingReportResponse via LLM with fallback.
        Evaluates full conversation against professional customer support standards.
        """
        msgs = messages or []
        session_id = str(_get_field(session, "session_id") or "sess-default")
        product_name = _get_field(session, "product_name") or "Product"
        customer_scenario = _get_field(session, "customer_scenario") or "General inquiry"
        persona = _get_field(session, "persona") or "Patient"

        formatted_history = format_conversation_history(msgs)
        format_instructions = coaching_report_parser.get_format_instructions()

        prompt_values = {
            "session_id": session_id,
            "product_name": product_name,
            "customer_scenario": customer_scenario,
            "persona": persona,
            "conversation_history": formatted_history,
            "format_instructions": format_instructions,
        }

        def run_provider(provider: str) -> CoachingReportResponse:
            client = self._get_llm_client(provider)
            chain = COACHING_REPORT_PROMPT | client
            response = chain.invoke(prompt_values)
            raw_text = _clean_content(response.content)
            json_str = extract_json_from_response(raw_text)

            data = json.loads(json_str)
            return _sanitize_coaching_report_dict(data, session_id=session_id)

        def run_mock() -> CoachingReportResponse:
            return generate_mock_coaching_report(
                session=session,
                messages=msgs,
            )

        return self._invoke_with_fallback(run_provider, run_mock)
