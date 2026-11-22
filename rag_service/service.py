"""
Asynchronous Service layer for the RAG Microservice.

Handles multi-document ingestion, text extraction, chunking,
dense + BM25 embedding, Pinecone indexing, query rewriting,
and hybrid search retrieval without blocking the FastAPI event loop.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from langchain_core.documents import Document

from .config import settings
from .parsers.document_parsers import DocumentIngestionPipeline
from .retrieval.bm25_sparse import BM25SparseEncoder
from .retrieval.hybrid_retriever import PineconeHybridRetriever, HybridSearchResult
from .retrieval.query_rewriter import QueryRewriter, RewrittenQuery
from .indexing.indexer import PineconeHybridIndexer
from .api.schemas import (
    UploadResponse,
    UploadFileMetadata,
    RetrieveRequest,
    RetrieveResponse,
    RetrievedChunk,
    HealthResponse,
    StatsResponse,
)


class RAGService:
    """Core RAG service orchestrating multi-document knowledge base ingestion

    and Pinecone hybrid search retrieval for FastAPI.
    """

    def __init__(self, mock_mode: Optional[bool] = None):
        self.mock_mode = mock_mode if mock_mode is not None else not bool(settings.pinecone_api_key)

        # 1. Document Ingestion Pipeline
        self.ingestion = DocumentIngestionPipeline()

        # 2. BM25 Sparse Model
        self.bm25_encoder = BM25SparseEncoder()

        # 3. Pinecone Hybrid Indexer
        self.indexer = PineconeHybridIndexer(
            bm25_encoder=self.bm25_encoder,
            mock_mode=self.mock_mode,
        )

        # 4. Pinecone Hybrid Retriever
        self.retriever = PineconeHybridRetriever(
            pinecone_index=self.indexer.index,
            bm25_encoder=self.bm25_encoder,
            alpha=settings.hybrid_alpha,
            top_k=settings.top_k,
            mock_mode=self.mock_mode,
        )

        # Link mock stores if in mock mode
        if self.mock_mode and self.indexer.mock_store is not None:
            self.retriever._mock_store = self.indexer.mock_store

        # 5. Query Rewriter Engine
        self.query_rewriter = QueryRewriter(use_llm_if_available=True)

    # -------------------------------------------------------------------------
    # Concurrency-safe Multi-Document Ingestion
    # -------------------------------------------------------------------------

    async def ingest_uploaded_files(self, file_data: List[Tuple[str, bytes]]) -> UploadResponse:
        """Processes multiple uploaded files asynchronously without blocking the event loop.

        file_data is a list of (filename, file_bytes) tuples.
        """
        # Run CPU/IO heavy document extraction & embedding in a worker thread
        return await asyncio.to_thread(self._sync_ingest_files, file_data)

    def _sync_ingest_files(self, file_data: List[Tuple[str, bytes]]) -> UploadResponse:
        """Synchronous implementation executed within asyncio threadpool."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            files_meta: List[UploadFileMetadata] = []
            all_chunks: List[Document] = []

            for filename, content_bytes in file_data:
                # Save bytes to temporary file for parser loaders
                safe_name = Path(filename).name
                dest_path = tmp_path / safe_name
                dest_path.write_bytes(content_bytes)

                # Parse and chunk using LangChain parsers
                try:
                    file_chunks = self.ingestion.process_file(dest_path)
                    all_chunks.extend(file_chunks)

                    total_chars = sum(len(c.page_content) for c in file_chunks)
                    files_meta.append(
                        UploadFileMetadata(
                            filename=safe_name,
                            file_type=dest_path.suffix.lstrip("."),
                            chunks_count=len(file_chunks),
                            total_characters=total_chars,
                        )
                    )
                except Exception as e:
                    print(f"Error parsing file '{filename}': {e}")
                    files_meta.append(
                        UploadFileMetadata(
                            filename=safe_name,
                            file_type=dest_path.suffix.lstrip("."),
                            chunks_count=0,
                            total_characters=0,
                        )
                    )

            if not all_chunks:
                return UploadResponse(
                    success=False,
                    message="No readable text chunks could be extracted from uploaded files.",
                    documents_processed=0,
                    total_chunks_indexed=0,
                    files=files_meta,
                )

            # Fit BM25 and upsert to Pinecone
            total_upserted = self.indexer.index_documents(all_chunks, fit_bm25=True)

            return UploadResponse(
                success=True,
                message=f"Successfully indexed {total_upserted} chunks from {len(file_data)} files into Pinecone knowledge base.",
                documents_processed=len(file_data),
                total_chunks_indexed=total_upserted,
                files=files_meta,
            )

    # -------------------------------------------------------------------------
    # Concurrency-safe Query Rewriting & Hybrid Retrieval
    # -------------------------------------------------------------------------

    async def retrieve_relevant_information(self, request: RetrieveRequest) -> RetrieveResponse:
        """Rewrites the query for optimal retrieval and executes Pinecone hybrid search

        without blocking the event loop.
        """
        return await asyncio.to_thread(self._sync_retrieve, request)

    def _sync_retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Synchronous retrieval logic executed within asyncio threadpool."""
        original_query = request.query
        alpha = request.alpha if request.alpha is not None else settings.hybrid_alpha
        top_k = request.top_k if request.top_k is not None else settings.top_k

        # 1. Rewrite the query to improve Pinecone relevance if enabled
        if request.rewrite_query:
            rewritten_obj: RewrittenQuery = self.query_rewriter.rewrite(original_query)
            search_query = rewritten_obj.rewritten_query or original_query
        else:
            search_query = original_query

        # 2. Execute Hybrid Search in Pinecone
        results: List[HybridSearchResult] = self.retriever.hybrid_search(
            query=search_query,
            alpha=alpha,
            top_k=top_k,
            filter_dict=request.filter,
        )

        # 3. Format into Pydantic models (Note: LLM is NOT called, as requested)
        retrieved_chunks = [
            RetrievedChunk(
                id=r.id,
                score=r.score,
                content=r.content,
                source=str(r.metadata.get("source", "unknown")),
                metadata=r.metadata,
            )
            for r in results
        ]

        return RetrieveResponse(
            original_query=original_query,
            rewritten_query=search_query,
            alpha_used=alpha,
            top_k=top_k,
            total_retrieved=len(retrieved_chunks),
            chunks=retrieved_chunks,
        )

    # -------------------------------------------------------------------------
    # Health & Stats
    # -------------------------------------------------------------------------

    async def get_health(self) -> HealthResponse:
        """Checks connection status to Pinecone."""
        connected = (not self.mock_mode) and (self.indexer.index is not None)
        return HealthResponse(
            status="healthy",
            pinecone_connected=connected,
            index_name=settings.pinecone_index_name,
            metric="dotproduct",
            mock_mode=self.mock_mode,
        )

    async def get_stats(self) -> StatsResponse:
        """Returns knowledge base stats."""
        return StatsResponse(
            index_name=settings.pinecone_index_name,
            dimension=settings.embedding_dimension,
            metric="dotproduct",
            mock_mode=self.mock_mode,
            bm25_fitted=self.bm25_encoder.is_fitted,
        )
