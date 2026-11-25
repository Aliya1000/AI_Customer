"""
Golden Dataset Curation and Feedback Loop Service.
Curates high-scoring sessions and customer interactions into reusable few-shot training examples.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from backend.app.supabase_client import (
        SessionRepository,
        MessageRepository,
        ReportRepository,
    )
except ImportError:
    from app.supabase_client import (
        SessionRepository,
        MessageRepository,
        ReportRepository,
    )


class GoldenDatasetService:
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        report_repo: Optional[ReportRepository] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.message_repo = message_repo or MessageRepository()
        self.report_repo = report_repo or ReportRepository()

    def harvest_golden_sessions(self, min_score: int = 90) -> List[Dict[str, Any]]:
        """Harvests completed sessions with high evaluation scores into golden dataset examples."""
        reports = self.report_repo.list_reports()
        golden_examples = []

        for r in reports:
            score = r.get("evaluation_score", 0)
            if score >= min_score:
                session_id = r.get("session_id")
                session = self.session_repo.get_session(session_id) or {}
                messages = self.message_repo.get_messages_for_session(session_id)

                golden_examples.append({
                    "session_id": session_id,
                    "product_name": session.get("product_name"),
                    "scenario": session.get("customer_scenario"),
                    "score": score,
                    "conversation_transcript": [
                        {"sender": m["sender"], "text": m["message_text"]}
                        for m in messages
                    ],
                    "strengths": r.get("strengths", []),
                    "best_practices": r.get("recommendations", []),
                })

        return golden_examples

    def export_to_jsonl(self, output_path: str, min_score: int = 90) -> int:
        examples = self.harvest_golden_sessions(min_score=min_score)
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        return len(examples)
