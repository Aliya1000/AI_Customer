from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from backend.app.supabase_client.client import get_supabase_client


class MessageRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def create_message(
        self,
        session_id: str,
        sender: str,
        message_text: str,
        message_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not message_id:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            message_id = f"MSG-{ts_ms}-{uuid.uuid4().hex[:4].upper()}"

        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        record = {
            "message_id": message_id,
            "session_id": session_id,
            "sender": sender,
            "message_text": message_text,
            "timestamp": timestamp,
        }

        res = self.client.table("messages").insert(record).execute()
        return res.data[0] if res.data else record

    def get_messages_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        res = (
            self.client.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("timestamp", desc=False)
            .execute()
        )
        messages = res.data or []
        # Break ties deterministically using (timestamp, message_id)
        messages.sort(
            key=lambda m: (m.get("timestamp") or "", m.get("message_id") or "")
        )
        return messages

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("messages")
            .select("*")
            .eq("message_id", message_id)
            .execute()
        )
        return res.data[0] if res.data else None


message_repo = MessageRepository()
