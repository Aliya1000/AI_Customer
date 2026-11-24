
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db_config import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _to_dict(data):
    """Convert Pydantic models or dictionaries into dictionaries."""
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    if isinstance(data, dict):
        return data.copy()
    return {}


# ============================================================
# SESSION REPOSITORY
# ============================================================

class SessionRepository:

    def create_session(self, data):
        values = _to_dict(data)

        session_id = values.get("session_id") or _new_id("SES")
        created_at = values.get("created_at") or _now()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, interaction_mode, product_name,
                    product_context, customer_scenario, persona,
                    status, created_at, emotional_progression,
                    replay_transcript
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    values["interaction_mode"],
                    values["product_name"],
                    values.get("product_context", ""),
                    values["customer_scenario"],
                    values.get("persona", "Patient"),
                    values.get("status", "active"),
                    created_at,
                    values.get("emotional_progression"),
                    values.get("replay_transcript"),
                ),
            )
            conn.commit()

        return self.get_session(session_id)

    def get_session(self, session_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit=100):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_session(self, session_id, updates):
        values = _to_dict(updates)

        allowed = {
            "status",
            "product_context",
            "customer_scenario",
            "persona",
            "emotional_progression",
            "replay_transcript",
        }

        changes = {
            key: value
            for key, value in values.items()
            if key in allowed
        }

        if changes:
            assignments = ", ".join(
                f"{column} = ?" for column in changes
            )

            with get_connection() as conn:
                cursor = conn.execute(
                    f"UPDATE sessions SET {assignments} WHERE session_id = ?",
                    (*changes.values(), session_id),
                )
                conn.commit()

                if cursor.rowcount == 0:
                    return None

        return self.get_session(session_id)


# ============================================================
# MESSAGE REPOSITORY
# ============================================================

class MessageRepository:

    def create_message(
        self,
        session_id,
        sender,
        message_text,
        timestamp=None,
        message_id=None,
    ):
        message_id = message_id or _new_id("MSG")
        timestamp = timestamp or _now()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, session_id, sender,
                    message_text, timestamp
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    sender,
                    message_text,
                    timestamp,
                ),
            )
            conn.commit()

        return {
            "message_id": message_id,
            "session_id": session_id,
            "sender": sender,
            "message_text": message_text,
            "timestamp": timestamp,
        }

    def get_messages_for_session(self, session_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC, rowid ASC
                """,
                (session_id,),
            ).fetchall()

            return [dict(row) for row in rows]


# ============================================================
# PRODUCT REPOSITORY
# ============================================================

class ProductRepository:

    def list_products(self):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT product_id, product_name,
                       product_description, product_category
                FROM products
                ORDER BY product_name ASC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def get_by_id(self, product_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE product_id = ?",
                (product_id,),
            ).fetchone()

            return dict(row) if row else None

    def get_by_name(self, product_name):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM products
                WHERE LOWER(product_name) = LOWER(?)
                LIMIT 1
                """,
                (product_name,),
            ).fetchone()

            return dict(row) if row else None


# ============================================================
# REPORT REPOSITORY
# ============================================================

class ReportRepository:

    def _decode(self, row):
        if not row:
            return None

        data = dict(row)

        try:
            details = json.loads(data.get("recommendations") or "{}")
        except (TypeError, json.JSONDecodeError):
            details = {}

        return {
            "report_id": data["report_id"],
            "session_id": data["session_id"],
            "conversation_summary": data.get("conversation_summary", ""),
            "evaluation_score": data.get("evaluation_score", 0),
            "customer_sentiment": details.get("customer_sentiment", "Neutral"),
            "employee_evaluation": details.get("employee_evaluation", ""),
            "strengths": details.get("strengths", []),
            "areas_for_improvement": details.get("areas_for_improvement", []),
            "recommendations": details.get("recommendations", []),
            "recommended_replies": details.get("recommended_replies", []),
        }

    def create_report(self, report):
        values = _to_dict(report)

        session_id = values["session_id"]
        report_id = values.get("report_id") or _new_id("REP")

        details = {
            "customer_sentiment": values.get("customer_sentiment", "Neutral"),
            "employee_evaluation": values.get("employee_evaluation", ""),
            "strengths": values.get("strengths", []),
            "areas_for_improvement": values.get("areas_for_improvement", []),
            "recommendations": values.get("recommendations", []),
            "recommended_replies": values.get("recommended_replies", []),
        }

        with get_connection() as conn:
            existing = conn.execute(
                "SELECT report_id FROM coaching_reports WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if existing:
                report_id = existing["report_id"]

            conn.execute(
                """
                INSERT INTO coaching_reports (
                    report_id, session_id, conversation_summary,
                    evaluation_score, recommendations
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    conversation_summary = excluded.conversation_summary,
                    evaluation_score = excluded.evaluation_score,
                    recommendations = excluded.recommendations
                """,
                (
                    report_id,
                    session_id,
                    values.get("conversation_summary", ""),
                    values.get("evaluation_score", 0),
                    json.dumps(details),
                ),
            )
            conn.commit()

        return self.get_by_session_id(session_id)

    def get_by_session_id(self, session_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM coaching_reports WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            return self._decode(row)

    def get_by_id(self, report_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM coaching_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()

            return self._decode(row)

    def list_reports(self):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM coaching_reports
                ORDER BY rowid DESC
                """
            ).fetchall()

            return [self._decode(row) for row in rows]

    def update_report(self, report_id, updates):
        existing = self.get_by_id(report_id)

        if not existing:
            return None

        values = _to_dict(updates)

        merged = {**existing, **values}
        merged["report_id"] = report_id

        return self.create_report(merged)


# ============================================================
# KNOWLEDGE REPOSITORY
# ============================================================

class KnowledgeRepository:

    def create_document(
        self,
        document_id,
        filename,
        file_type,
        storage_path=None,
        processing_status="pending",
        upload_time=None,
        **kwargs,
    ):
        upload_time = upload_time or _now()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_documents (
                    document_id, filename, file_type,
                    upload_time, processing_status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    filename,
                    file_type.upper(),
                    upload_time,
                    processing_status,
                ),
            )
            conn.commit()

        return self.get_document(document_id)

    def list_documents(self, limit=100):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_documents
                ORDER BY upload_time DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            documents = [dict(row) for row in rows]

        for document in documents:
            document["storage_path"] = (
                f'{document["document_id"]}/{document["filename"]}'
            )

        return documents

    def get_document(self, document_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM knowledge_documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()

            if not row:
                return None

            document = dict(row)

        document["storage_path"] = (
            f'{document["document_id"]}/{document["filename"]}'
        )

        return document

    def delete_document(self, document_id):
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM knowledge_documents WHERE document_id = ?",
                (document_id,),
            )
            conn.commit()

            return cursor.rowcount > 0
