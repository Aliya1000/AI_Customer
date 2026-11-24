from typing import Any, List, Optional

from backend.app.llm.fallback_service import FallbackLLMService
from backend.app.schemas.report import CoachingReportResponse


class CoachingService:
    """
    Coaching Report evaluation service.
    Analyzes session history and evaluates employee performance, producing a
    comprehensive CoachingReportResponse with 10 fields covering summary, sentiment,
    score, detailed evaluation, strengths, improvement areas, recommendations,
    and recommended replies.
    """

    def __init__(self, llm_service: Optional[FallbackLLMService] = None):
        self.llm_service = llm_service or FallbackLLMService()

    def generate_report(
        self,
        session: Any,
        messages: Optional[List[Any]] = None,
    ) -> CoachingReportResponse:
        """
        Generates full CoachingReportResponse analyzing the conversation transcript.
        Invokes LLM with automatic multi-provider fallback to deterministic mock generator.
        """
        return self.llm_service.generate_coaching_report(session, messages)
