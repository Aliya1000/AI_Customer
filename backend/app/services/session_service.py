import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

try:
    from backend.app.schemas.session import SessionCreate, SessionResponse, SessionUpdate
    from backend.app.supabase_client.session_repo import SessionRepository
    from backend.app.supabase_client.message_repo import MessageRepository
    from backend.app.supabase_client.product_repo import ProductRepository
    from backend.app.llm.fallback_service import FallbackLLMService
except ImportError:
    from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate
    from app.supabase_client.session_repo import SessionRepository
    from app.supabase_client.message_repo import MessageRepository
    from app.supabase_client.product_repo import ProductRepository
    from app.llm.fallback_service import FallbackLLMService

try:
    from backend.app.services.rag_client import RAGServiceClient
except ImportError:
    from app.services.rag_client import RAGServiceClient

logger = logging.getLogger("backend.app.services.session_service")


class SessionService:
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        product_repo: Optional[ProductRepository] = None,
        llm_service: Optional[FallbackLLMService] = None,
        rag_client: Optional[RAGServiceClient] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.message_repo = message_repo or MessageRepository()
        self.product_repo = product_repo or ProductRepository()
        self.llm_service = llm_service or FallbackLLMService()
        self.rag_client = rag_client or RAGServiceClient()

    def create_session(self, data: SessionCreate) -> SessionResponse:
        session_dict = self.session_repo.create_session(data)
        session_id = session_dict["session_id"]

        # Automatically seed opening customer message
        initial_text = session_dict.get("customer_scenario", "").strip() or "Customer initiated support session."
        self.message_repo.create_message(
            session_id=session_id,
            sender="customer",
            message_text=initial_text,
        )

        return SessionResponse(**session_dict)

    def list_sessions(self, limit: int = 100) -> List[SessionResponse]:
        sessions = self.session_repo.list_sessions(limit=limit)
        return [SessionResponse(**s) for s in sessions]

    async def get_session(self, session_id: str) -> SessionResponse:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        messages = self.message_repo.get_messages_for_session(session_id)

        # Lookup product
        product = self._lookup_product(session.get("product_name", ""))

        # Determine query for RAG context
        query_text = ""
        if messages:
            query_text = messages[-1].get("message_text", "")
        if not query_text:
            query_text = session.get("customer_scenario", "") or session.get("product_name", "")

        rag_chunks = []
        try:
            rag_chunks = await self.rag_client.retrieve_relevant_information(
                query=query_text,
                session_id=session_id,
                top_k=3,
            )
        except Exception as e:
            logger.warning(f"RAG retrieval during get_session failed: {e}")
            rag_chunks = []

        agent_outputs = self.llm_service.generate_agent_outputs(
            session=session,
            messages=messages,
            rag_context=rag_chunks,
            product=product,
        )

        session_copy = dict(session)
        session_copy["agent_outputs"] = agent_outputs
        return SessionResponse(**session_copy)

    def update_session(self, session_id: str, updates: SessionUpdate) -> SessionResponse:
        updated = self.session_repo.update_session(session_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return SessionResponse(**updated)

    def _lookup_product(self, product_name: str) -> Optional[Dict[str, Any]]:
        if not product_name:
            return None
        prod = self.product_repo.get_by_name(product_name)
        if prod:
            return prod
        p_name_lower = product_name.lower().strip()
        for p in self.product_repo.list_products():
            item_name = p.get("product_name", "").lower().strip()
            if p_name_lower == item_name or p_name_lower in item_name or item_name in p_name_lower:
                return p
        return None
