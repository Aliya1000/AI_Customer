from typing import Any, Dict, Optional, Union
import uuid
from backend.app.schemas.report import CoachingReportCreate
from backend.app.supabase_client.client import get_supabase_client


class ReportRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def create_report(
        self, report_data: Union[Dict[str, Any], CoachingReportCreate]
    ) -> Dict[str, Any]:
        if isinstance(report_data, CoachingReportCreate):
            data = report_data.model_dump(exclude_none=True)
        else:
            data = dict(report_data)

        if not data.get("report_id"):
            session_id = data.get("session_id", "")
            suffix = session_id[-4:] if len(session_id) >= 4 else uuid.uuid4().hex[:4].upper()
            data["report_id"] = f"REP-{suffix}-{uuid.uuid4().hex[:3].upper()}"

        data.setdefault("customer_sentiment", "Neutral")
        data.setdefault("employee_evaluation", "")
        data.setdefault("strengths", [])
        data.setdefault("areas_for_improvement", [])
        data.setdefault("recommendations", [])
        data.setdefault("recommended_replies", [])

        res = self.client.table("coaching_reports").insert(data).execute()
        return res.data[0] if res.data else data

    def get_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("coaching_reports")
            .select("*")
            .eq("session_id", session_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("coaching_reports")
            .select("*")
            .eq("report_id", report_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def update_report(
        self, report_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        upd = {k: v for k, v in updates.items() if v is not None}
        if not upd:
            return self.get_by_id(report_id)

        res = (
            self.client.table("coaching_reports")
            .update(upd)
            .eq("report_id", report_id)
            .execute()
        )
        return res.data[0] if res.data else None


report_repo = ReportRepository()
coaching_report_repo = report_repo
