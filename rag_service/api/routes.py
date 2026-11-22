"""
FastAPI Routes for Document Ingestion and Hybrid Information Retrieval.
"""

from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status

from .schemas import (
    UploadResponse,
    RetrieveRequest,
    RetrieveResponse,
    HealthResponse,
    StatsResponse,
)
from ..service import RAGService


# Global singleton instance of RAGService
_rag_service_instance: RAGService | None = None


def get_rag_service() -> RAGService:
    """Dependency provider for RAGService."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance


router = APIRouter(prefix="/api/v1", tags=["RAG Knowledge Base & Hybrid Retrieval"])


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple documents to Pinecone Knowledge Base",
    description=(
        "Concurrently ingests multiple files (PDF, Word .docx/.doc, Images via VLM, Markdown, TXT, JSON), "
        "extracts text with LangChain loaders & Vision-Language Model, applies RecursiveCharacterTextSplitter chunking, "
        "computes dense and BM25 sparse vector embeddings, and stores them in Pinecone."
    ),
)
async def upload_documents(
    files: List[UploadFile] = File(
        ...,
        description="List of document files (.pdf, .docx, .png, .jpg, .md, .txt, .json) to ingest"
    ),
    service: RAGService = Depends(get_rag_service),
) -> UploadResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided for upload.",
        )

    # Concurrently read uploaded file bytes
    file_payloads = []
    for file in files:
        content = await file.read()
        file_payloads.append((file.filename or "unknown_file", content))

    # Process and index asynchronously without blocking the FastAPI event loop
    response = await service.ingest_uploaded_files(file_payloads)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=response.message,
        )

    return response


@router.post(
    "/documents/retrieve",
    response_model=RetrieveResponse,
    summary="Retrieve relevant document chunks using Pinecone Hybrid Search",
    description=(
        "Based on the input query, optionally rewrites the question to improve Pinecone relevance, "
        "generates dense semantic embeddings and BM25 sparse keyword vectors, "
        "and retrieves the top-k most relevant passages. Does NOT invoke an LLM generation step."
    ),
)
async def retrieve_relevant_information(
    request: RetrieveRequest,
    service: RAGService = Depends(get_rag_service),
) -> RetrieveResponse:
    try:
        response = await service.retrieve_relevant_information(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval error: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check(
    service: RAGService = Depends(get_rag_service),
) -> HealthResponse:
    return await service.get_health()


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Knowledge base statistics",
)
async def get_stats(
    service: RAGService = Depends(get_rag_service),
) -> StatsResponse:
    return await service.get_stats()
