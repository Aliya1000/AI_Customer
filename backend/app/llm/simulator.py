from typing import Any, List, Optional

from backend.app.llm.fallback_service import FallbackLLMService


class CustomerSimulator:
    """
    Persona-driven customer simulator service.
    Produces simulated customer replies based on customer persona (Patient, Impatient,
    Confused, Angry, Standard), emotional progression (stable, escalating_to_calm,
    calm_to_frustrated), customer scenario, and conversation history.
    """

    def __init__(self, llm_service: Optional[FallbackLLMService] = None):
        self.llm_service = llm_service or FallbackLLMService()

    def generate_reply(
        self,
        session: Any,
        messages: Optional[List[Any]] = None,
    ) -> str:
        """
        Generates simulated customer reply adhering to persona and emotional progression.
        Invokes LLM with automatic multi-provider fallback to deterministic mock generator.
        """
        return self.llm_service.generate_customer_reply(session, messages)
