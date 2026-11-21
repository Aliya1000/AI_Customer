import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db_config import get_connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ============================================================
# 1. PRODUCTS
# ============================================================

def get_all_products() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, product_name, product_description, product_category FROM products ORDER BY product_name ASC"
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 2. SESSIONS
# ============================================================

def create_session(data: Dict[str, Any]) -> Dict[str, Any]:
    session_id = data.get("session_id") or _new_id("SES")
    created_at = _utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, interaction_mode, product_name, product_context,
                customer_scenario, persona, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                data["interaction_mode"],
                data["product_name"],
                data.get("product_context", ""),
                data["customer_scenario"],
                data.get("persona", "Patient"),
                data.get("status", "active"),
                created_at,
            ),
        )
        conn.commit()

    return get_session_by_id(session_id)


def get_all_sessions() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def update_session_status(session_id: str, status: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE sessions SET status = ? WHERE session_id = ?",
            (status, session_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# 3. MESSAGES
# ============================================================

def save_message(session_id: str, sender: str, message_text: str) -> Dict[str, Any]:
    message_id = _new_id("MSG")
    timestamp = _utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (message_id, session_id, sender, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, session_id, sender, message_text, timestamp),
        )
        conn.commit()

    return {
        "message_id": message_id,
        "session_id": session_id,
        "sender": sender,
        "message_text": message_text,
        "timestamp": timestamp,
    }


def get_messages_by_session(session_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC, rowid ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 4. KNOWLEDGE DOCUMENTS
# ============================================================

def save_knowledge_document(
    filename: str,
    file_type: str,
    processing_status: str = "pending",
) -> Dict[str, Any]:
    document_id = _new_id("DOC")
    upload_time = _utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_documents (
                document_id, filename, file_type, upload_time, processing_status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, filename, file_type.upper(), upload_time, processing_status),
        )
        conn.commit()

    return {
        "document_id": document_id,
        "filename": filename,
        "file_type": file_type.upper(),
        "upload_time": upload_time,
        "processing_status": processing_status,
    }


def get_all_knowledge_documents() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_documents ORDER BY upload_time DESC, rowid DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_document_status(document_id: str, processing_status: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE knowledge_documents SET processing_status = ? WHERE document_id = ?",
            (processing_status, document_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_knowledge_document(document_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM knowledge_documents WHERE document_id = ?",
            (document_id,),
        )
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# 5. COACHING REPORTS
# ============================================================

def save_coaching_report(
    session_id: str,
    conversation_summary: str,
    evaluation_score: int,
    recommendations: Dict[str, Any],
) -> Dict[str, Any]:
    report_id = _new_id("REP")
    rec_json = json.dumps(recommendations)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO coaching_reports (
                report_id, session_id, conversation_summary, evaluation_score, recommendations
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                conversation_summary = excluded.conversation_summary,
                evaluation_score = excluded.evaluation_score,
                recommendations = excluded.recommendations
            """,
            (report_id, session_id, conversation_summary, evaluation_score, rec_json),
        )
        conn.commit()

    return get_coaching_report_by_session(session_id)


def get_coaching_report_by_session(session_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM coaching_reports WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None

        data = dict(row)
        rec = json.loads(data["recommendations"]) if data.get("recommendations") else {}
        return {
            "report_id": data["report_id"],
            "session_id": data["session_id"],
            "conversation_summary": data["conversation_summary"],
            "evaluation_score": data["evaluation_score"],
            "customer_sentiment": rec.get("customer_sentiment", "Neutral"),
            "employee_evaluation": rec.get("employee_evaluation", ""),
            "strengths": rec.get("strengths", []),
            "areas_for_improvement": rec.get("areas_for_improvement", []),
            "recommendations": rec.get("recommendations", []),
            "recommended_replies": rec.get("recommended_replies", []),
        }