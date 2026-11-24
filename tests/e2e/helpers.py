"""Reusable schema and contract assertion helpers for E2E tests."""

from typing import Dict, Any, Optional


def assert_valid_product(prod: Dict[str, Any]) -> None:
    """Assert that a product object adheres to the ProductResponse schema."""
    assert isinstance(prod, dict), f"Expected dict, got {type(prod)}"
    assert "product_id" in prod, "Missing product_id"
    assert isinstance(prod["product_id"], str) and prod["product_id"].startswith("PRD-"), (
        f"Invalid product_id format: {prod.get('product_id')}"
    )
    assert "product_name" in prod and isinstance(prod["product_name"], str), "Invalid product_name"
    assert len(prod["product_name"]) > 0, "Empty product_name"
    assert "product_description" in prod and isinstance(prod["product_description"], str), "Invalid product_description"
    assert "product_category" in prod and isinstance(prod["product_category"], str), "Invalid product_category"


def assert_valid_session(session: Dict[str, Any], expected_mode: Optional[str] = None) -> None:
    """Assert that a session object adheres to the SessionResponse schema."""
    assert isinstance(session, dict), f"Expected dict, got {type(session)}"
    assert "session_id" in session, "Missing session_id"
    assert isinstance(session["session_id"], str) and session["session_id"].startswith("SES-"), (
        f"Invalid session_id format: {session.get('session_id')}"
    )
    assert "interaction_mode" in session, "Missing interaction_mode"
    if expected_mode:
        assert session["interaction_mode"] == expected_mode, (
            f"Expected mode {expected_mode}, got {session['interaction_mode']}"
        )
    assert "product_name" in session and isinstance(session["product_name"], str), "Invalid product_name"
    assert len(session["product_name"]) > 0, "Empty product_name"
    assert "customer_scenario" in session and isinstance(session["customer_scenario"], str), "Invalid customer_scenario"
    assert len(session["customer_scenario"]) > 0, "Empty customer_scenario"
    assert "status" in session and session["status"] in ("active", "completed", "archived"), (
        f"Invalid status: {session.get('status')}"
    )
    assert "created_at" in session and isinstance(session["created_at"], str), "Missing created_at timestamp"


def assert_valid_message(
    msg: Dict[str, Any],
    expected_session_id: Optional[str] = None,
    expected_sender: Optional[str] = None,
) -> None:
    """Assert that a message object adheres to the MessageResponse schema."""
    assert isinstance(msg, dict), f"Expected dict, got {type(msg)}"
    assert "message_id" in msg, "Missing message_id"
    assert isinstance(msg["message_id"], str) and msg["message_id"].startswith("MSG-"), (
        f"Invalid message_id format: {msg.get('message_id')}"
    )
    assert "session_id" in msg, "Missing session_id"
    if expected_session_id:
        assert msg["session_id"] == expected_session_id, (
            f"Expected session_id {expected_session_id}, got {msg.get('session_id')}"
        )
    assert "sender" in msg, "Missing sender"
    if expected_sender:
        assert msg["sender"] == expected_sender, (
            f"Expected sender {expected_sender}, got {msg.get('sender')}"
        )
    else:
        assert msg["sender"] in ("employee", "customer", "system"), (
            f"Invalid sender: {msg.get('sender')}"
        )
    assert "message_text" in msg and isinstance(msg["message_text"], str), "Invalid message_text"
    assert len(msg["message_text"]) > 0, "Empty message_text"
    assert "timestamp" in msg and isinstance(msg["timestamp"], str), "Missing timestamp"


def assert_valid_agent_outputs(outputs: Dict[str, Any]) -> None:
    """Assert that agent_outputs contains all 6 required sections with valid schemas."""
    assert isinstance(outputs, dict), f"Expected dict for agent_outputs, got {type(outputs)}"

    # 1. supervisor
    assert "supervisor" in outputs, "Missing 'supervisor' section in agent_outputs"
    sup = outputs["supervisor"]
    assert isinstance(sup, dict), "supervisor must be a dict"
    assert "status" in sup and isinstance(sup["status"], str)
    assert "active_pattern" in sup and isinstance(sup["active_pattern"], str)
    assert "agents_completed" in sup and isinstance(sup["agents_completed"], int)

    # 2. query_analysis
    assert "query_analysis" in outputs, "Missing 'query_analysis' section in agent_outputs"
    qa = outputs["query_analysis"]
    assert isinstance(qa, dict), "query_analysis must be a dict"
    assert "summary" in qa and isinstance(qa["summary"], str)
    assert "intent" in qa and isinstance(qa["intent"], str)
    assert "sentiment" in qa and isinstance(qa["sentiment"], str)

    # 3. knowledge_retrieval
    assert "knowledge_retrieval" in outputs, "Missing 'knowledge_retrieval' section in agent_outputs"
    kr = outputs["knowledge_retrieval"]
    assert isinstance(kr, dict), "knowledge_retrieval must be a dict"
    assert "summary" in kr and isinstance(kr["summary"], str)
    assert "articles" in kr and isinstance(kr["articles"], list)
    for art in kr["articles"]:
        assert isinstance(art, dict), "Article entry must be a dict"
        assert "title" in art and "source" in art and "relevance_score" in art and "snippet" in art
        assert isinstance(art["relevance_score"], (int, float))
    assert "faqs" in kr and isinstance(kr["faqs"], list)
    for faq in kr["faqs"]:
        assert isinstance(faq, dict), "FAQ entry must be a dict"
        assert "question" in faq and "answer" in faq
    assert "troubleshooting_steps" in kr and isinstance(kr["troubleshooting_steps"], list)

    # 4. product_information
    assert "product_information" in outputs, "Missing 'product_information' section in agent_outputs"
    pi = outputs["product_information"]
    assert isinstance(pi, dict), "product_information must be a dict"
    assert "product_name" in pi and isinstance(pi["product_name"], str)
    assert "product_category" in pi and isinstance(pi["product_category"], str)
    assert "product_description" in pi and isinstance(pi["product_description"], str)
    assert "warranty_status" in pi and isinstance(pi["warranty_status"], str)

    # 5. response_generation
    assert "response_generation" in outputs, "Missing 'response_generation' section in agent_outputs"
    rg = outputs["response_generation"]
    assert isinstance(rg, dict), "response_generation must be a dict"
    assert "suggested_response" in rg and isinstance(rg["suggested_response"], str)

    # 6. evaluation_and_coaching
    assert "evaluation_and_coaching" in outputs, "Missing 'evaluation_and_coaching' section in agent_outputs"
    ec = outputs["evaluation_and_coaching"]
    assert isinstance(ec, dict), "evaluation_and_coaching must be a dict"
    assert "evaluation_score" in ec and isinstance(ec["evaluation_score"], int)
    assert 0 <= ec["evaluation_score"] <= 100, f"Score out of bounds: {ec['evaluation_score']}"
    assert "tips" in ec and isinstance(ec["tips"], list)


def assert_valid_coaching_report(report: Dict[str, Any], expected_session_id: Optional[str] = None) -> None:
    """Assert that a coaching report adheres to CoachingReportResponse schema."""
    assert isinstance(report, dict), f"Expected dict, got {type(report)}"
    assert "report_id" in report, "Missing report_id"
    assert isinstance(report["report_id"], str) and report["report_id"].startswith("REP-"), (
        f"Invalid report_id format: {report.get('report_id')}"
    )
    assert "session_id" in report, "Missing session_id"
    if expected_session_id:
        assert report["session_id"] == expected_session_id, (
            f"Expected session_id {expected_session_id}, got {report.get('session_id')}"
        )
    assert "conversation_summary" in report and isinstance(report["conversation_summary"], str)
    assert "customer_sentiment" in report and isinstance(report["customer_sentiment"], str)
    assert "evaluation_score" in report and isinstance(report["evaluation_score"], int)
    assert 0 <= report["evaluation_score"] <= 100, f"Score out of bounds: {report['evaluation_score']}"
    assert "employee_evaluation" in report and isinstance(report["employee_evaluation"], str)

    # 4 array fields
    assert "strengths" in report and isinstance(report["strengths"], list), "strengths must be a list"
    assert "areas_for_improvement" in report and isinstance(report["areas_for_improvement"], list), (
        "areas_for_improvement must be a list"
    )
    assert "recommendations" in report and isinstance(report["recommendations"], list), (
        "recommendations must be a list"
    )
    assert "recommended_replies" in report and isinstance(report["recommended_replies"], list), (
        "recommended_replies must be a list"
    )


def assert_valid_knowledge_document(doc: Dict[str, Any]) -> None:
    """Assert that a knowledge document adheres to KnowledgeDocumentResponse schema."""
    assert isinstance(doc, dict), f"Expected dict, got {type(doc)}"
    assert "document_id" in doc, "Missing document_id"
    assert isinstance(doc["document_id"], str) and doc["document_id"].startswith("DOC-"), (
        f"Invalid document_id format: {doc.get('document_id')}"
    )
    assert "filename" in doc and isinstance(doc["filename"], str)
    assert "file_type" in doc and isinstance(doc["file_type"], str)
    assert doc["file_type"].upper() in ("PDF", "TXT", "JSON"), f"Unexpected file_type: {doc['file_type']}"
    assert "upload_time" in doc and isinstance(doc["upload_time"], str)
    assert "processing_status" in doc and doc["processing_status"] in (
        "pending",
        "processing",
        "indexed",
        "failed",
    ), f"Invalid processing_status: {doc.get('processing_status')}"


def create_test_session(
    client,
    interaction_mode: str = "simulator",
    product_name: str = "AeroSound Pro ANC Headphones",
    product_context: str = "Purchased 3 months ago",
    customer_scenario: str = "Audio defect with buzzing sound in right ear cup.",
    persona: str = "Patient",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Helper to create a session and return the JSON response."""
    payload = {
        "interaction_mode": interaction_mode,
        "product_name": product_name,
        "product_context": product_context,
        "customer_scenario": customer_scenario,
        "persona": persona,
        **kwargs,
    }
    response = client.post("/api/sessions", json=payload)
    assert response.status_code in (200, 201), f"Session creation failed: {response.text}"
    return response.json()


def send_test_message(
    client,
    session_id: str,
    message_text: str,
    sender: str = "employee",
) -> Dict[str, Any]:
    """Helper to send a message to a session and return the JSON response."""
    payload = {"sender": sender, "message_text": message_text}
    response = client.post(f"/api/sessions/{session_id}/messages", json=payload)
    assert response.status_code in (200, 201), f"Sending message failed: {response.text}"
    return response.json()


def upload_test_document(
    client,
    filename: str = "troubleshooting.txt",
    content: bytes = b"Sample troubleshooting document content.",
    content_type: str = "text/plain",
) -> Dict[str, Any]:
    """Helper to upload a knowledge document and return the JSON response."""
    files = {"file": (filename, content, content_type)}
    response = client.post("/api/knowledge/upload", files=files)
    assert response.status_code in (200, 201), f"Knowledge upload failed: {response.text}"
    return response.json()
