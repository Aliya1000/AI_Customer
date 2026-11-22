"""
Tests for BM25 Sparse Encoder, Hybrid Vector Scaling, and Retrieval.
"""

import pytest
from pathlib import Path
from rag_service.config import settings
from rag_service.retrieval.bm25_sparse import BM25SparseEncoder
from rag_service.retrieval.hybrid_retriever import (
    scale_hybrid_vectors,
    PineconeHybridRetriever,
    InMemoryVectorStore,
)
from rag_service.pipeline import HybridRAGPipeline


def test_bm25_sparse_encoder(tmp_path: Path):
    corpus = [
        "Pinecone is a managed vector database built for high performance search.",
        "BM25 is a term frequency-based sparse retrieval algorithm.",
        "Hybrid search merges dense semantic vectors with BM25 sparse vectors.",
    ]

    params_file = tmp_path / "test_bm25.json"
    encoder = BM25SparseEncoder(params_path=str(params_file))
    encoder.fit(corpus)
    encoder.save()
    assert params_file.exists()

    # Query encoding
    q_sparse = encoder.encode_queries("BM25 sparse")
    assert "indices" in q_sparse
    assert "values" in q_sparse
    assert len(q_sparse["indices"]) > 0
    assert len(q_sparse["indices"]) == len(q_sparse["values"])

    # Reload encoder from disk
    loaded_encoder = BM25SparseEncoder(params_path=str(params_file))
    reloaded_sparse = loaded_encoder.encode_queries("BM25 sparse")
    assert reloaded_sparse["indices"] == q_sparse["indices"]


def test_scale_hybrid_vectors():
    dense = [1.0, 2.0, 3.0]
    sparse = {"indices": [10, 20], "values": [0.5, 0.8]}

    # Pure dense: alpha = 1.0
    s_dense, s_sparse = scale_hybrid_vectors(dense, sparse, alpha=1.0)
    assert s_dense == [1.0, 2.0, 3.0]
    assert s_sparse["values"] == [0.0, 0.0]

    # Pure sparse: alpha = 0.0
    s_dense, s_sparse = scale_hybrid_vectors(dense, sparse, alpha=0.0)
    assert s_dense == [0.0, 0.0, 0.0]
    assert s_sparse["values"] == [0.5, 0.8]

    # Balanced hybrid: alpha = 0.5
    s_dense, s_sparse = scale_hybrid_vectors(dense, sparse, alpha=0.5)
    assert s_dense == [0.5, 1.0, 1.5]
    assert s_sparse["values"] == [0.25, 0.4]

    # Invalid alpha raises ValueError
    with pytest.raises(ValueError):
        scale_hybrid_vectors(dense, sparse, alpha=1.5)


def test_in_memory_hybrid_vector_store():
    store = InMemoryVectorStore()
    store.upsert([
        {
            "id": "doc1",
            "values": [1.0, 0.0],
            "sparse_values": {"indices": [1], "values": [1.0]},
            "metadata": {"text": "Document 1"},
        },
        {
            "id": "doc2",
            "values": [0.0, 1.0],
            "sparse_values": {"indices": [2], "values": [1.0]},
            "metadata": {"text": "Document 2"},
        },
    ])

    # Query matching doc1 on dense, doc2 on sparse
    query_dense = [1.0, 0.0]
    query_sparse = {"indices": [2], "values": [1.0]}

    # Dense dominated (alpha=0.9)
    res_dense = store.query(
        vector=[v * 0.9 for v in query_dense],
        sparse_vector={"indices": [2], "values": [0.1]},
        top_k=2,
    )
    assert res_dense["matches"][0]["id"] == "doc1"

    # Sparse dominated (alpha=0.1)
    res_sparse = store.query(
        vector=[v * 0.1 for v in query_dense],
        sparse_vector={"indices": [2], "values": [0.9]},
        top_k=2,
    )
    assert res_sparse["matches"][0]["id"] == "doc2"


def test_end_to_end_mock_pipeline():
    pipeline = HybridRAGPipeline(mock_mode=True)
    sample_dir = settings.sample_docs_dir if settings.sample_docs_dir.exists() else Path("sample_docs")
    count = pipeline.ingest_files(sample_dir)
    assert count > 0

    # Search
    search_results = pipeline.search("Pinecone hybrid search", alpha=0.5, top_k=3)
    assert len(search_results) > 0
    assert search_results[0].score > 0

    # RAG Query
    rag_out = pipeline.query("How does Pinecone hybrid search work?", alpha=0.5, structured=True)
    assert "response" in rag_out
    assert "retrieved_chunks" in rag_out
    assert len(rag_out["retrieved_chunks"]) > 0
