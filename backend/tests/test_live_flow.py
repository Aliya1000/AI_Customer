import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app as backend_app
from rag_service.api.app import app as rag_app


@pytest.mark.anyio
async def test_clean_url_redirect_live_console():
    """Verify that accessing /live-console.html redirects to /live-console."""
    async with AsyncClient(transport=ASGITransport(app=backend_app), base_url="http://test") as client:
        # Request legacy .html URL without following redirects
        res = await client.get("/live-console.html", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == "/live-console"

        # Request clean URL
        clean_res = await client.get("/live-console")
        assert clean_res.status_code == 200
        assert "Live Support Console" in clean_res.text


@pytest.mark.anyio
async def test_session_lifecycle_and_rag_verification():
    """Verify backend session creation and verification endpoint used by RAG service."""
    async with AsyncClient(transport=ASGITransport(app=backend_app), base_url="http://test") as backend_client:
        # 1. Create a new support session
        session_payload = {
            "interaction_mode": "simulator",
            "product_name": "AeroSound Pro ANC Headphones",
            "customer_scenario": "Customer complaint regarding crackling audio",
            "persona": "Frustrated",
        }
        res = await backend_client.post("/api/sessions", json=session_payload)
        assert res.status_code == 201
        session_data = res.json()
        session_id = session_data["session_id"]
        assert session_id.startswith("SES-")

        # 2. Verify session verification endpoint (which RAG calls)
        verify_res = await backend_client.get(f"/api/sessions/{session_id}/verify")
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["valid"] is True
        assert verify_data["session_id"] == session_id
        assert verify_data["product_name"] == "AeroSound Pro ANC Headphones"

        # 3. Test sending a message to the backend
        msg_payload = {
            "sender": "employee",
            "message_text": "Hello, thank you for contacting support. How can I help you today?",
        }
        msg_res = await backend_client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert msg_res.status_code == 201
        msg_data = msg_res.json()
        assert "agent_outputs" in msg_data
        assert msg_data["agent_outputs"]["supervisor"]["status"] == "Completed"


@pytest.mark.anyio
async def test_rag_service_with_backend_session_verification():
    """Verify RAG service /documents/retrieve requires valid session verified with backend."""
    # 1. Without session ID -> 401 Unauthorized
    async with AsyncClient(transport=ASGITransport(app=rag_app), base_url="http://test") as rag_client:
        res_no_sess = await rag_client.post(
            "/api/v1/documents/retrieve",
            json={"query": "warranty", "top_k": 2},
        )
        assert res_no_sess.status_code == 401

        # 2. With SYSTEM internal secret -> 200 OK
        res_system = await rag_client.post(
            "/api/v1/documents/retrieve",
            headers={"X-Session-ID": "SYSTEM", "X-Internal-Secret": "rag-backend-secret-key-2026"},
            json={"query": "warranty", "session_id": "SYSTEM", "top_k": 2},
        )
        assert res_system.status_code == 200
        assert res_system.json()["session_id"] == "SYSTEM"
