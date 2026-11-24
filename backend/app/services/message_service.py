from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

try:
    from backend.app.schemas.message import MessageCreate, MessageResponse, SendMessageResponse
    from backend.app.sqlite_client.repositories import (
    MessageRepository,
    SessionRepository,
    ProductRepository,
)
    from backend.app.llm.fallback_service import FallbackLLMService
    from backend.app.llm.simulator import CustomerSimulator
except ImportError:
    from app.schemas.message import MessageCreate, MessageResponse, SendMessageResponse
    from app.sqlite_client.repositories import (
    MessageRepository,
    SessionRepository,
    ProductRepository,
)
    from app.llm.fallback_service import FallbackLLMService
    from app.llm.simulator import CustomerSimulator

try:
    from backend.app.services.rag_client import RAGServiceClient
except ImportError:
    from app.services.rag_client import RAGServiceClient

logger = logging.getLogger("backend.app.services.message_service")


class MessageService:
    def __init__(
        self,
        message_repo: Optional[MessageRepository] = None,
        session_repo: Optional[SessionRepository] = None,
        product_repo: Optional[ProductRepository] = None,
        llm_service: Optional[FallbackLLMService] = None,
        simulator: Optional[CustomerSimulator] = None,
        rag_client: Optional[RAGServiceClient] = None,
    ):
        self.message_repo = message_repo or MessageRepository()
        self.session_repo = session_repo or SessionRepository()
        self.product_repo = product_repo or ProductRepository()
        self.llm_service = llm_service or FallbackLLMService()
        self.simulator = simulator or CustomerSimulator(self.llm_service)
        self.rag_client = rag_client or RAGServiceClient()

    async def send_message(self, session_id: str, payload: MessageCreate) -> SendMessageResponse:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        # Whitespace validation
        if not payload.message_text or not payload.message_text.strip():
            raise HTTPException(status_code=422, detail="message_text cannot be empty or whitespace-only")

        # 1. Save incoming message
        saved_rec = self.message_repo.create_message(
            session_id=session_id,
            sender=payload.sender,
            message_text=payload.message_text,
        )
        saved_message = MessageResponse(**saved_rec)

        # 2. Simulator mode: trigger simulated reply if sender is employee
        simulated_reply: Optional[MessageResponse] = None
        if session.get("interaction_mode") == "simulator" and payload.sender == "employee":
            history = self.message_repo.get_messages_for_session(session_id)
            sim_text = self.simulator.generate_reply(session, history)

            sim_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if sim_ts < saved_message.timestamp:
                sim_ts = saved_message.timestamp

            sim_rec = self.message_repo.create_message(
                session_id=session_id,
                sender="customer",
                message_text=sim_text,
                timestamp=sim_ts,
            )
            simulated_reply = MessageResponse(**sim_rec)

        # 3. Retrieve RAG context chunks
        all_messages = self.message_repo.get_messages_for_session(session_id)
        rag_chunks = []
        try:
            rag_chunks = await self.rag_client.retrieve_relevant_information(
                query=payload.message_text,
                session_id=session_id,
                top_k=3,
            )
        except Exception as e:
            logger.warning(f"RAG retrieval during send_message failed: {e}")
            rag_chunks = []

        # 4. Generate structured AgentOutputs
        product = self._lookup_product(session.get("product_name", ""))
        agent_outputs = self.llm_service.generate_agent_outputs(
            session=session,
            messages=all_messages,
            rag_context=rag_chunks,
            product=product,
        )

        return SendMessageResponse(
            saved_message=saved_message,
            simulated_customer_reply=simulated_reply,
            agent_outputs=agent_outputs,
        )

    def get_messages(self, session_id: str) -> List[MessageResponse]:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        messages = self.message_repo.get_messages_for_session(session_id)
        return [MessageResponse(**m) for m in messages]

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
