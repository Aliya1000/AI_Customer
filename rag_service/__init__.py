"""
RAG Service with Pinecone Hybrid Search and LangChain Parsers.

A self-contained microservice providing multimodal document ingestion,
NVIDIA/Groq multimodal parsing, Pinecone hybrid retrieval (dense + BM25),
conversational query rewriting, and FastAPI endpoints.
"""

from .config import settings
from .service import RAGService
from .pipeline import HybridRAGPipeline
from .api.routes import router
from .api.app import app, create_app

__all__ = [
    "settings",
    "RAGService",
    "HybridRAGPipeline",
    "router",
    "app",
    "create_app",
]
