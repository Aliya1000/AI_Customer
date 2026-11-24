import concurrent.futures
import pytest
from backend.app.schemas.product import ProductCreate
from backend.app.schemas.report import CoachingReportCreate
from backend.app.schemas.session import SessionCreate, SessionUpdate
from backend.app.supabase_client import (
    DocumentStorage,
    KnowledgeRepository,
    MessageRepository,
    MockSupabaseClient,
    ProductRepository,
    ReportRepository,
    SessionRepository,
    get_mock_store,
    get_supabase_client,
    knowledge_repo,
    message_repo,
    product_repo,
    report_repo,
    reset_mock_store,
    session_repo,
)


@pytest.fixture(autouse=True)
def clean_mock_store():
    """Ensure each test runs with a fresh, pre-seeded mock store."""
    reset_mock_store()
    yield
    reset_mock_store()


# ==============================================================================
# 1. Product Repository Tests
# ==============================================================================


def test_product_repo_preseeded():
    products = product_repo.list_products()
    assert len(products) == 3
    ids = {p["product_id"] for p in products}
    assert ids == {"PRD-01", "PRD-02", "PRD-03"}


def test_product_repo_get_by_id():
    p1 = product_repo.get_by_id("PRD-01")
    assert p1 is not None
    assert p1["product_name"] == "AeroSound Pro ANC Headphones"
    assert p1["product_category"] == "Audio Hardware"

    p_none = product_repo.get_by_id("PRD-NONEXISTENT")
    assert p_none is None


def test_product_repo_get_by_name():
    p2 = product_repo.get_by_name("PulseWatch S4 Smartwatch")
    assert p2 is not None
    assert p2["product_id"] == "PRD-02"

    p_missing = product_repo.get_by_name("Nonexistent Product")
    assert p_missing is None


def test_product_repo_create():
    dto = ProductCreate(
        product_name="EchoWave Earbuds",
        product_description="TWS earbuds with wireless charging.",
        product_category="Audio Hardware",
    )
    created = product_repo.create_product(dto)
    assert created["product_name"] == "EchoWave Earbuds"
    assert created["product_id"].startswith("PRD-")

    retrieved = product_repo.get_by_id(created["product_id"])
    assert retrieved is not None
    assert retrieved["product_description"] == dto.product_description


# ==============================================================================
# 2. Session Repository Tests
# ==============================================================================


def test_session_repo_initially_empty():
    sessions = session_repo.list_sessions()
    assert len(sessions) == 0


def test_session_repo_get_and_not_found():
    dto = SessionCreate(
        interaction_mode="simulator",
        product_name="AeroSound Pro ANC Headphones",
        customer_scenario="Cracked headphone earcup",
        persona="Angry",
    )
    created = session_repo.create_session(dto)
    sid = created["session_id"]
    s1 = session_repo.get_session(sid)
    assert s1 is not None
    assert s1["persona"] == "Angry"
    assert s1["interaction_mode"] == "simulator"

    s_none = session_repo.get_session("SES-9999-9999")
    assert s_none is None


def test_session_repo_create():
    dto = SessionCreate(
        interaction_mode="simulator",
        product_name="PulseWatch S4 Smartwatch",
        customer_scenario="Watch face glass shattered in box",
        persona="Angry",
    )
    created = session_repo.create_session(dto)
    assert created["session_id"].startswith("SES-")
    assert created["status"] == "active"
    assert created["created_at"] is not None

    fetched = session_repo.get_session(created["session_id"])
    assert fetched is not None
    assert fetched["customer_scenario"] == dto.customer_scenario


def test_session_repo_update():
    dto = SessionCreate(
        interaction_mode="simulator",
        product_name="PulseWatch S4 Smartwatch",
        customer_scenario="Battery issues",
        persona="Confused",
    )
    created = session_repo.create_session(dto)
    sid = created["session_id"]
    upd = SessionUpdate(status="completed", product_context="Warranty verified DOA")
    updated = session_repo.update_session(sid, upd)
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["product_context"] == "Warranty verified DOA"

    fetched = session_repo.get_session(sid)
    assert fetched["status"] == "completed"


def test_session_repo_delete_and_cascade():
    dto = SessionCreate(
        interaction_mode="simulator",
        product_name="AeroSound Pro ANC Headphones",
        customer_scenario="Damaged unit",
        persona="Angry",
    )
    created = session_repo.create_session(dto)
    sid = created["session_id"]

    message_repo.create_message(sid, "customer", "Item arrived broken")
    report_repo.create_report(CoachingReportCreate(
        session_id=sid,
        conversation_summary="Broken unit discussion",
        customer_sentiment="Angry",
        evaluation_score=80,
    ))

    msgs = message_repo.get_messages_for_session(sid)
    assert len(msgs) == 1
    report = report_repo.get_by_session_id(sid)
    assert report is not None

    deleted = session_repo.delete_session(sid)
    assert deleted is True

    # Session should now be gone
    assert session_repo.get_session(sid) is None

    # Cascaded messages and reports should also be gone
    assert len(message_repo.get_messages_for_session(sid)) == 0
    assert report_repo.get_by_session_id(sid) is None


# ==============================================================================
# 3. Message Repository Tests
# ==============================================================================


def test_message_repo_get_chronological():
    dto = SessionCreate(
        interaction_mode="manual",
        product_name="PulseWatch S4 Smartwatch",
        customer_scenario="Testing messages",
        persona="Confused",
    )
    created = session_repo.create_session(dto)
    sid = created["session_id"]

    m1 = message_repo.create_message(sid, "customer", "First message")
    m2 = message_repo.create_message(sid, "employee", "Second message")

    msgs = message_repo.get_messages_for_session(sid)
    assert len(msgs) == 2
    assert msgs[0]["message_id"] == m1["message_id"]
    assert msgs[0]["sender"] == "customer"
    assert msgs[1]["message_id"] == m2["message_id"]
    assert msgs[1]["sender"] == "employee"


def test_message_repo_create_and_get():
    s = session_repo.create_session(SessionCreate(interaction_mode="simulator", product_name="AeroSound", customer_scenario="Scenario"))
    sid = s["session_id"]

    new_msg = message_repo.create_message(
        session_id=sid,
        sender="employee",
        message_text="Hello! We are here to help you with the earcup issue.",
    )
    assert new_msg["message_id"].startswith("MSG-")
    assert new_msg["session_id"] == sid

    msgs = message_repo.get_messages_for_session(sid)
    assert len(msgs) == 1
    assert msgs[-1]["message_text"] == "Hello! We are here to help you with the earcup issue."

    single = message_repo.get_message_by_id(new_msg["message_id"])
    assert single is not None
    assert single["sender"] == "employee"


def test_message_repo_get_nonexistent():
    assert message_repo.get_message_by_id("MSG-NONEXISTENT") is None
    assert message_repo.get_messages_for_session("SES-EMPTY") == []


def test_message_repo_subsecond_precision_and_deterministic_tiebreak():
    """
    Verifies that messages created in the same second have sub-second timestamp resolution
    or deterministically sort by message_id on timestamp ties.
    """
    m1 = message_repo.create_message(
        session_id="SES-TIEBREAK",
        sender="customer",
        message_text="First message",
        message_id="MSG-001",
        timestamp="2026-11-23T12:00:00Z",
    )
    m2 = message_repo.create_message(
        session_id="SES-TIEBREAK",
        sender="employee",
        message_text="Second message with identical timestamp",
        message_id="MSG-002",
        timestamp="2026-11-23T12:00:00Z",
    )
    msgs = message_repo.get_messages_for_session("SES-TIEBREAK")
    assert len(msgs) == 2
    assert msgs[0]["message_id"] == "MSG-001"
    assert msgs[1]["message_id"] == "MSG-002"

    # Also verify default timestamp format contains microseconds
    m_auto = message_repo.create_message(
        session_id="SES-TIEBREAK",
        sender="customer",
        message_text="Auto timestamp message",
    )
    assert "." in m_auto["timestamp"]


# ==============================================================================
# 4. Knowledge Document Repository Tests
# ==============================================================================


def test_knowledge_repo_initially_empty():
    docs = knowledge_repo.list_documents()
    assert len(docs) == 0


def test_knowledge_repo_create_and_update_status():
    doc = knowledge_repo.create_document(
        filename="return_logistics_v1.pdf",
        file_type="PDF",
    )
    assert doc["document_id"].startswith("DOC-")
    assert doc["processing_status"] == "pending"

    updated = knowledge_repo.update_document_status(doc["document_id"], "indexed")
    assert updated is not None
    assert updated["processing_status"] == "indexed"

    fetched = knowledge_repo.get_document(doc["document_id"])
    assert fetched["processing_status"] == "indexed"


def test_knowledge_repo_delete():
    doc = knowledge_repo.create_document(
        filename="temp_doc.pdf",
        file_type="PDF",
    )
    doc_id = doc["document_id"]
    del_ok = knowledge_repo.delete_document(doc_id)
    assert del_ok is True
    assert knowledge_repo.get_document(doc_id) is None

    # Deleting again returns False
    assert knowledge_repo.delete_document(doc_id) is False


# ==============================================================================
# 5. Coaching Report Repository Tests
# ==============================================================================


def test_coaching_report_repo_create_and_fetch():
    dto = SessionCreate(
        interaction_mode="simulator",
        product_name="AeroSound Pro ANC Headphones",
        customer_scenario="Broken earcup",
        persona="Angry",
    )
    created_session = session_repo.create_session(dto)
    sid = created_session["session_id"]

    rep = report_repo.create_report(CoachingReportCreate(
        session_id=sid,
        conversation_summary="Customer reported physical damage.",
        customer_sentiment="Angry",
        evaluation_score=84,
        employee_evaluation="Pending review.",
    ))
    rep1 = report_repo.get_by_session_id(sid)
    assert rep1 is not None
    assert rep1["report_id"] == rep["report_id"]
    assert rep1["evaluation_score"] == 84

    rep_by_id = report_repo.get_by_id(rep["report_id"])
    assert rep_by_id is not None
    assert rep_by_id["session_id"] == sid


def test_coaching_report_repo_create():
    s = session_repo.create_session(SessionCreate(interaction_mode="manual", product_name="CloudDesk", customer_scenario="Billing issue"))
    sid = s["session_id"]

    dto = CoachingReportCreate(
        session_id=sid,
        conversation_summary="Billing duplicate charge resolved promptly with refund.",
        customer_sentiment="Relieved",
        evaluation_score=96,
        employee_evaluation="Excellent customer service and immediate refund action.",
        strengths=["Quick resolution", "Clear communication"],
        areas_for_improvement=[],
        recommendations=["Follow up to ensure invoice is corrected."],
        recommended_replies=["Your refund has been initiated."],
    )
    created = report_repo.create_report(dto)
    assert created["session_id"] == sid
    assert created["report_id"].startswith("REP-")
    assert created["evaluation_score"] == 96

    fetched = report_repo.get_by_session_id(sid)
    assert fetched is not None
    assert fetched["customer_sentiment"] == "Relieved"


def test_coaching_report_repo_update():
    s = session_repo.create_session(SessionCreate(interaction_mode="manual", product_name="CloudDesk", customer_scenario="Test"))
    sid = s["session_id"]

    created = report_repo.create_report(CoachingReportCreate(
        session_id=sid,
        conversation_summary="Initial summary",
        evaluation_score=70,
    ))

    upd = report_repo.update_report(
        created["report_id"],
        {"evaluation_score": 90, "customer_sentiment": "Satisfied"},
    )
    assert upd is not None
    assert upd["evaluation_score"] == 90
    assert upd["customer_sentiment"] == "Satisfied"


def test_mock_store_numeric_sorting_with_zero():
    """
    Verifies that sorting by numeric columns containing 0 does not raise TypeError
    and sorts correctly in both ascending and descending directions.
    """
    client = get_supabase_client(force_mock=True)

    s1 = session_repo.create_session(SessionCreate(interaction_mode="manual", product_name="P1", customer_scenario="S1"))
    s2 = session_repo.create_session(SessionCreate(interaction_mode="manual", product_name="P2", customer_scenario="S2"))
    s3 = session_repo.create_session(SessionCreate(interaction_mode="manual", product_name="P3", customer_scenario="S3"))

    report_repo.create_report(
        CoachingReportCreate(
            session_id=s1["session_id"],
            conversation_summary="Session 1",
            evaluation_score=84,
        )
    )
    report_repo.create_report(
        CoachingReportCreate(
            session_id=s2["session_id"],
            conversation_summary="Session 2",
            evaluation_score=91,
        )
    )
    report_repo.create_report(
        CoachingReportCreate(
            session_id=s3["session_id"],
            conversation_summary="Session with 0 evaluation score",
            customer_sentiment="Frustrated",
            evaluation_score=0,
            employee_evaluation="Needs improvement",
        )
    )

    # Query descending: 91, 84, 0
    desc_res = (
        client.table("coaching_reports")
        .select("*")
        .order("evaluation_score", desc=True)
        .execute()
    )
    scores_desc = [r["evaluation_score"] for r in desc_res.data]
    assert scores_desc == [91, 84, 0]

    # Query ascending: 0, 84, 91
    asc_res = (
        client.table("coaching_reports")
        .select("*")
        .order("evaluation_score", desc=False)
        .execute()
    )
    scores_asc = [r["evaluation_score"] for r in asc_res.data]
    assert scores_asc == [0, 84, 91]


# ==============================================================================
# 6. Document Storage Tests
# ==============================================================================


def test_document_storage_upload_download_delete():
    storage = DocumentStorage()
    path = "DOC-999/test_manual.txt"
    payload = b"Hello, this is a unit test manual file for storage verification."

    # Upload
    uploaded_path = storage.upload_file(path, payload, content_type="text/plain")
    assert uploaded_path == path

    # Download
    downloaded = storage.download_file(path)
    assert downloaded == payload

    # List
    files = storage.list_files("DOC-999")
    assert len(files) == 1
    assert files[0]["name"] == "test_manual.txt"

    # Delete
    del_res = storage.delete_file(path)
    assert del_res is True

    # Download after delete raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.download_file(path)


# ==============================================================================
# 7. Thread-Safety / Concurrency Tests
# ==============================================================================


def test_mock_store_concurrent_writes_and_reads():
    """
    Spawns multiple threads concurrently creating sessions and messages
    to verify no race conditions, corrupted state, or deadlocks occur under load.
    """
    num_threads = 10
    sessions_per_thread = 5

    def worker(worker_id: int):
        created_session_ids = []
        for i in range(sessions_per_thread):
            sess = session_repo.create_session(
                SessionCreate(
                    interaction_mode="simulator",
                    product_name="AeroSound Pro ANC Headphones",
                    customer_scenario=f"Concurrent test scenario from worker {worker_id} iteration {i}",
                )
            )
            created_session_ids.append(sess["session_id"])
            message_repo.create_message(
                session_id=sess["session_id"],
                sender="customer",
                message_text=f"Customer message w{worker_id}-i{i}",
            )
            message_repo.create_message(
                session_id=sess["session_id"],
                sender="employee",
                message_text=f"Employee reply w{worker_id}-i{i}",
            )
        return created_session_ids

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, w) for w in range(num_threads)]
        all_ids = []
        for f in concurrent.futures.as_completed(futures):
            all_ids.extend(f.result())

    # Verify that all sessions were created without loss
    total_created = num_threads * sessions_per_thread
    assert len(all_ids) == total_created

    # total_created sessions created concurrently
    all_sessions = session_repo.list_sessions(limit=500)
    assert len(all_sessions) == total_created

    # Spot check that each created session has exactly 2 messages
    for sid in all_ids[:10]:
        msgs = message_repo.get_messages_for_session(sid)
        assert len(msgs) == 2


# ==============================================================================
# 8. Dual-Mode Client Fallback Tests
# ==============================================================================


def test_client_fallback_to_mock_when_unconfigured():
    client = get_supabase_client(force_mock=True)
    assert isinstance(client, MockSupabaseClient)
    assert hasattr(client, "table")
    assert hasattr(client, "storage")

    # Table query works on mock
    res = client.table("products").select("*").execute()
    assert len(res.data) == 3
