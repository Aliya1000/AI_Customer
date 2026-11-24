import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from backend.app.services.rag_client import RAGServiceClient


@pytest.mark.anyio
async def test_rag_client_headers_contain_session_and_secret():
    client = RAGServiceClient(base_url="http://localhost:8001", internal_secret="test-secret")
    headers = client._headers("SES-12345")
    assert headers["X-Session-ID"] == "SES-12345"
    assert headers["X-Internal-Secret"] == "test-secret"


@pytest.mark.anyio
async def test_rag_client_retrieve_success():
    client = RAGServiceClient(base_url="http://localhost:8001")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "session_id": "SES-TEST",
        "chunks": [{"id": "chunk-1", "score": 0.88, "content": "Warranty info"}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        chunks = await client.retrieve_relevant_information(
            query="broken earcup",
            session_id="SES-TEST",
            top_k=2
        )
        assert len(chunks) == 1
        assert chunks[0]["id"] == "chunk-1"


@pytest.mark.anyio
async def test_rag_client_retrieve_graceful_fallback_when_offline():
    client = RAGServiceClient(base_url="http://unreachable-rag-host:9999")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        chunks = await client.retrieve_relevant_information(
            query="broken earcup",
            session_id="SES-OFFLINE",
            top_k=2
        )
        # Graceful fallback returns empty list without raising exception
        assert chunks == []


@pytest.mark.anyio
async def test_rag_client_diagnose_image_fallback():
    client = RAGServiceClient(base_url="http://unreachable-rag-host:9999")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        result = await client.diagnose_image(
            file_bytes=b"dummy-image",
            filename="photo.jpg",
            session_id="SES-TEST",
            notes="Cracked headphone",
        )
        assert result["session_id"] == "SES-TEST"
        assert result["status"] == "diagnosed_fallback"
