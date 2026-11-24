from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid
from backend.app.schemas.session import SessionCreate, SessionUpdate
from backend.app.supabase_client.client import get_supabase_client


class SessionRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def create_session(
        self, data: Union[Dict[str, Any], SessionCreate]
    ) -> Dict[str, Any]:
        if isinstance(data, SessionCreate):
            record = data.model_dump(exclude_none=True)
        else:
            record = dict(data)

        if not record.get("session_id"):
            year = datetime.now(timezone.utc).year
            record["session_id"] = f"SES-{year}-{uuid.uuid4().hex[:6].upper()}"

        if not record.get("created_at"):
            record["created_at"] = (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            )

        if "status" not in record:
            record["status"] = "active"

        if "product_context" not in record:
            record["product_context"] = ""

        res = self.client.table("sessions").insert(record).execute()
        return res.data[0] if res.data else record

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("sessions")
            .select("*")
            .eq("session_id", session_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        res = (
            self.client.table("sessions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def update_session(
        self, session_id: str, updates: Union[Dict[str, Any], SessionUpdate]
    ) -> Optional[Dict[str, Any]]:
        if isinstance(updates, SessionUpdate):
            upd = updates.model_dump(exclude_none=True)
        else:
            upd = {k: v for k, v in updates.items() if v is not None}

        if not upd:
            return self.get_session(session_id)

        res = (
            self.client.table("sessions")
            .update(upd)
            .eq("session_id", session_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def delete_session(self, session_id: str) -> bool:
        res = (
            self.client.table("sessions")
            .delete()
            .eq("session_id", session_id)
            .execute()
        )
        return bool(res.data)


session_repo = SessionRepository()
