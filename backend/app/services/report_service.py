import logging
from typing import Optional
from fastapi import HTTPException

try:
    from backend.app.schemas.report import CoachingReportResponse
    from backend.app.sqlite_client.repositories import (
    ReportRepository,
    SessionRepository,
    MessageRepository,
)
    from backend.app.llm.fallback_service import FallbackLLMService
except ImportError:
    from app.schemas.report import CoachingReportResponse
    from app.sqlite_client.repositories import (
    ReportRepository,
    SessionRepository,
    MessageRepository,
)
    from app.llm.fallback_service import FallbackLLMService

logger = logging.getLogger("backend.app.services.report_service")


class ReportService:
    def __init__(
        self,
        report_repo: Optional[ReportRepository] = None,
        session_repo: Optional[SessionRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        llm_service: Optional[FallbackLLMService] = None,
    ):
        self.report_repo = report_repo or ReportRepository()
        self.session_repo = session_repo or SessionRepository()
        self.message_repo = message_repo or MessageRepository()
        self.llm_service = llm_service or FallbackLLMService()

    def get_coaching_report(self, session_id: str) -> CoachingReportResponse:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        # 1. Check for existing coaching report (idempotency)
        existing = self.report_repo.get_by_session_id(session_id)
        if existing:
            return CoachingReportResponse(**existing)

        # 2. Lazily generate coaching report
        messages = self.message_repo.get_messages_for_session(session_id)
        generated = self.llm_service.generate_coaching_report(session, messages)

        report_dict = generated.model_dump()
        report_dict["session_id"] = session_id

        # 3. Save to repository
        saved = self.report_repo.create_report(report_dict)
        return CoachingReportResponse(**saved)

    def override_report(self, session_id: str, updates: dict) -> CoachingReportResponse:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        existing = self.report_repo.get_by_session_id(session_id)
        if not existing:
            self.get_coaching_report(session_id)
            existing = self.report_repo.get_by_session_id(session_id)
        report_id = existing["report_id"]
        updated = self.report_repo.update_report(report_id, updates)
        return CoachingReportResponse(**updated)

    def export_report_html(self, session_id: str) -> str:
        report = self.get_coaching_report(session_id)
        session = self.session_repo.get_session(session_id) or {}
        strengths_html = "".join(f"<li>{s}</li>" for s in report.strengths)
        improvements_html = "".join(f"<li>{i}</li>" for i in report.areas_for_improvement)
        recs_html = "".join(f"<li>{r}</li>" for r in report.recommendations)

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Coaching Report - {report.report_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; color: #1e293b; }}
        .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }}
        .score {{ font-size: 36px; font-weight: bold; color: #2563eb; }}
        .badge {{ background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-size: 14px; font-weight: 600; }}
        h2 {{ color: #0f172a; margin-top: 24px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Support Coaching Report</h1>
        <p>Session ID: <strong>{session_id}</strong> | Product: <strong>{session.get('product_name', 'N/A')}</strong></p>
        <p>Evaluation Score: <span class="score">{report.evaluation_score}/100</span> | Sentiment: <span class="badge">{report.customer_sentiment}</span></p>
    </div>
    <h2>Conversation Summary</h2>
    <p>{report.conversation_summary}</p>
    <h2>Employee Evaluation</h2>
    <p>{report.employee_evaluation}</p>
    <h2>Strengths</h2>
    <ul>{strengths_html}</ul>
    <h2>Areas for Improvement</h2>
    <ul>{improvements_html}</ul>
    <h2>Recommendations</h2>
    <ul>{recs_html}</ul>
</body>
</html>"""
