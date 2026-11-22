"""
Retrieval module: Sparse BM25, Pinecone Hybrid Search, and LangChain Retriever adapter.
"""

from .bm25_sparse import BM25SparseEncoder
from .hybrid_retriever import PineconeHybridRetriever, HybridSearchResult

__all__ = ["BM25SparseEncoder", "PineconeHybridRetriever", "HybridSearchResult"]
