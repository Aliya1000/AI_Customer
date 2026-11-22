"""
Pydantic schemas for the FastAPI Microservice RAG API.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class UploadFileMetadata(BaseModel):
    """Metadata regarding a single processed document file."""
    filename: str = Field(description="Name of the uploaded file")
    file_type: str = Field(description="Detected extension (pdf, md, txt, json)")
    chunks_count: int = Field(description="Number of chunks extracted from this file")
    total_characters: int = Field(description="Total character count across all chunks")


class UploadResponse(BaseModel):
    """Response returned after processing and indexing multiple documents."""
    success: bool = Field(default=True)
    message: str = Field(description="Status message")
    documents_processed: int = Field(description="Total count of successfully parsed documents")
    total_chunks_indexed: int = Field(description="Total chunks upserted to Pinecone hybrid index")
    files: List[UploadFileMetadata] = Field(default_factory=list, description="Per-file processing breakdown")


class RetrieveRequest(BaseModel):
    """Request payload for hybrid retrieval."""
    query: str = Field(
        ...,
        min_length=1,
        description="The question or search query",
        examples=["How does Pinecone handle the dotproduct metric for hybrid search?"]
    )
    alpha: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Hybrid weighting factor: 1.0=Dense only, 0.0=BM25 Sparse only, 0.5=Balanced"
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve"
    )
    rewrite_query: Optional[bool] = Field(
        default=True,
        description="Whether to rewrite and optimize the query for improved Pinecone relevance"
    )
    filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Pinecone metadata filter (e.g. {'file_type': 'pdf'})"
    )


class RetrievedChunk(BaseModel):
    """A single relevant document passage retrieved from Pinecone."""
    id: str = Field(description="Unique chunk identifier")
    score: float = Field(description="Hybrid search score (dense + sparse dot product)")
    content: str = Field(description="Extracted text content of the chunk")
    source: str = Field(description="Original document filename or source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata attributes")


class RetrieveResponse(BaseModel):
    """Response containing retrieved relevant document passages."""
    original_query: str = Field(description="The user's original raw question")
    rewritten_query: str = Field(description="The reformulated query optimized for Pinecone search")
    alpha_used: float = Field(description="The alpha parameter used for vector scaling")
    top_k: int = Field(description="Number of requested items")
    total_retrieved: int = Field(description="Number of chunks retrieved")
    chunks: List[RetrievedChunk] = Field(description="Ranked list of relevant passages")


class HealthResponse(BaseModel):
    """Microservice health check status."""
    status: str = Field(default="healthy")
    pinecone_connected: bool = Field(description="Whether connected to live Pinecone index")
    index_name: str = Field(description="Target Pinecone index name")
    metric: str = Field(default="dotproduct")
    mock_mode: bool = Field(description="True if running in mock/offline mode")


class StatsResponse(BaseModel):
    """Knowledge base index statistics."""
    index_name: str
    dimension: int
    metric: str
    mock_mode: bool
    bm25_fitted: bool
