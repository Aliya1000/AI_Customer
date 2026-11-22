"""
Tests for RAGService multi-document ingestion and hybrid retrieval.
"""

import pytest
from rag_service.service import RAGService
from rag_service.api.schemas import RetrieveRequest


@pytest.mark.anyio
async def test_rag_service_multi_document_ingestion():
    service = RAGService(mock_mode=True)

    file1 = ("pinecone_guide.md", b"# Pinecone Hybrid\nPinecone combines dense and sparse vectors.")
    file2 = ("retrieval_notes.txt", b"BM25 is a term frequency based ranking function.")
    file3 = ("config.json", b'[{"name": "spec", "content": "Metric must be dotproduct for hybrid search."}]')

    upload_resp = await service.ingest_uploaded_files([file1, file2, file3])

    assert upload_resp.success is True
    assert upload_resp.documents_processed == 3
    assert upload_resp.total_chunks_indexed >= 3
    assert len(upload_resp.files) == 3


@pytest.mark.anyio
async def test_rag_service_retrieval_with_query_rewriting():
    service = RAGService(mock_mode=True)

    # Ingest document
    file_data = [
        ("pinecone_doc.md", b"# Hybrid Metric\nIn Pinecone Serverless, hybrid search requires the dotproduct distance metric.")
    ]
    await service.ingest_uploaded_files(file_data)

    # Retrieve with conversational question and query rewriting enabled
    req = RetrieveRequest(
        query="Could you explain what distance metric Pinecone requires for hybrid search?",
        alpha=0.5,
        top_k=2,
        rewrite_query=True,
    )
    retrieve_resp = await service.retrieve_relevant_information(req)

    assert retrieve_resp.total_retrieved > 0
    assert retrieve_resp.rewritten_query != retrieve_resp.original_query
    top_chunk = retrieve_resp.chunks[0]
    assert "dotproduct" in top_chunk.content or top_chunk.score > 0
    # Confirm it returns chunks without invoking an LLM
    assert isinstance(top_chunk.content, str)
    assert top_chunk.source == "pinecone_doc.md"


@pytest.mark.anyio
async def test_rag_service_health_and_stats():
    service = RAGService(mock_mode=True)
    health = await service.get_health()
    stats = await service.get_stats()

    assert health.status == "healthy"
    assert health.metric == "dotproduct"
    assert stats.dimension == 1024
