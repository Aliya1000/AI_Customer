import sys
from pathlib import Path

# Allow running directly via `python database/test_db.py`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db_config import get_db_path, init_db
from database.db_repository import (
    create_session,
    delete_knowledge_document,
    get_all_knowledge_documents,
    get_all_products,
    get_all_sessions,
    get_coaching_report_by_session,
    get_messages_by_session,
    save_coaching_report,
    save_knowledge_document,
    save_message,
    update_document_status,
)


def run_tests() -> None:
    print("1. Initializing SQLite database...")
    init_db()
    print(f"   Database file ready at: {get_db_path()}")

    print("2. Checking seeded products...")
    products = get_all_products()
    assert len(products) >= 3, "Expected at least 3 seeded products"
    print(f"   Found {len(products)} products.")

    print("3. Creating a test session...")
    session = create_session({
        "interaction_mode": "simulator",
        "product_name": "AeroSound Pro ANC Headphones",
        "product_context": "Purchased 10 days ago, under warranty.",
        "customer_scenario": "Left earcup cracked on arrival.",
        "persona": "Angry",
    })
    sid = session["session_id"]
    print(f"   Created session: {sid}")
    assert len(get_all_sessions()) >= 1

    print("4. Saving and reading messages...")
    save_message(sid, "customer", "My headphones arrived cracked!")
    save_message(sid, "employee", "I sincerely apologize. I can arrange an immediate replacement.")
    msgs = get_messages_by_session(sid)
    assert len(msgs) == 2
    print(f"   Saved and fetched {len(msgs)} messages.")

    print("5. Testing knowledge document upload, status update, and delete...")
    doc = save_knowledge_document("test_warranty.pdf", "PDF", "pending")
    update_document_status(doc["document_id"], "indexed")
    docs = get_all_knowledge_documents()
    assert any(d["document_id"] == doc["document_id"] and d["processing_status"] == "indexed" for d in docs)
    assert delete_knowledge_document(doc["document_id"]) is True
    print("   Knowledge document lifecycle passed.")

    print("6. Saving and reading coaching report...")
    save_coaching_report(
        session_id=sid,
        conversation_summary="Agent handled damaged headphones complaint professionally.",
        evaluation_score=92,
        recommendations={
            "customer_sentiment": "Angry -> Calm",
            "employee_evaluation": "Empathetic and clear.",
            "strengths": ["Fast apology", "Clear replacement offer"],
            "areas_for_improvement": ["Mention 48-hour shipping ETA"],
            "recommendations": ["Send prepaid RMA label immediately"],
            "recommended_replies": ["I've sent your prepaid label and expedited a replacement."],
        },
    )
    report = get_coaching_report_by_session(sid)
    assert report is not None and report["evaluation_score"] == 92
    print(f"   Coaching report verified (Score: {report['evaluation_score']}/100).")

    print("\nALL DATABASE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()