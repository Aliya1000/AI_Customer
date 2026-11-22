# Pinecone Hybrid Search RAG Microservice for FastAPI

A high-performance, asynchronous RAG microservice designed to integrate with FastAPI applications. It provides:
- **Multimodal Document Ingestion**: Concurrently ingests and parses:
  - **PDF Documents (`.pdf`)**: Page-by-page text extraction and metadata tracking via `PyPDFLoader`.
  - **Microsoft Word (`.docx`, `.doc`)**: Structured paragraph and table extraction via `DocxParser`.
  - **Images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`)**: Visual text, diagram, and table extraction powered by **Groq Vision VLM** (`qwen/qwen3.8-27b`) via **`langchain-groq`**.
  - **Text & Markdown (`.txt`, `.md`, `.markdown`)**: Native recursive text splitting preserving semantic sections.
  - **Structured JSON (`.json`)**: Automatic record splitting and key-value metadata preservation.
- **Hybrid Embeddings**: Fits BM25 sparse vectors (`pinecone-text`) and generates dense vectors using **NVIDIA Inference NIM** (`nvidia/nemotron-3.5-embed-1b`, 1024-dim MRL scaling) with automatic guardrail sanitization.
- **Pinecone Vector Database**: Upserts hybrid records with `dotproduct` metric and metadata attributes.
- **Query Rewriting Engine**: Reformulates conversational user questions to remove filler noise and isolate technical terms/entities for maximum retrieval precision.
- **Hybrid Information Retrieval**: Retrieves the top-k most relevant chunks using alpha ($\alpha$) convex combination scaling.
- **Decoupled from LLM**: Focuses exclusively on document ingestion, embedding, indexing, query rewriting, and retrieval so your downstream LLM generation service can consume the clean retrieved passages.

---

## 🔑 Environment Configuration

Add your credentials to `.env`:

```env
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=rag-hybrid-search
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# NVIDIA Inference Embeddings
NVIDIA_API_KEY=nvapi-your_nvidia_api_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3.5-embed-1b
EMBEDDING_DIMENSION=1024

# Groq Vision-Language Model (VLM) for Image Parsing (via langchain-groq)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_VLM_MODEL=qwen/qwen3.8-27b
VLM_MAX_TOKENS=1024

# Hybrid Search Parameters
HYBRID_ALPHA=0.5
TOP_K=5
```

---

## ⚡ Concurrency Architecture in FastAPI

1. **Non-blocking Event Loop**:
   - Heavy parsing, embedding, and Pinecone network requests are dispatched via `asyncio.to_thread` to background worker pools.
   - The ASGI event loop remains completely free and responsive to incoming concurrent requests.
2. **Batch Ingestion**:
   - Multiple documents uploaded in a single request are read concurrently, chunked, and upserted in batches.

---

## 🔌 Connecting with your FastAPI Application (`app`)

You can either run this microservice as a standalone FastAPI app or mount/include its routes directly into your existing FastAPI application.

### Option A: Include Router in your existing FastAPI app

```python
from fastapi import FastAPI
from rag_service.api.routes import router as rag_router

app = FastAPI(title="My Main Backend Service")

# Mount the RAG routes under your preferred prefix
app.include_router(rag_router)

# Now your app has:
# POST /api/v1/documents/upload
# POST /api/v1/documents/retrieve
# GET  /api/v1/health
# GET  /api/v1/stats
```

### Option B: Run as a standalone Microservice

```bash
# Run with uvicorn
uvicorn rag_service.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Interactive Swagger API docs are available at `http://localhost:8000/docs`.

---

## 📡 API Endpoints Specification

### 1. Upload Multiple Documents
`POST /api/v1/documents/upload` (multipart/form-data)

Uploads and indexes multiple documents into Pinecone concurrently.

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "files=@sample_docs/rag_hybrid_architecture.md" \
  -F "files=@sample_docs/pinecone_sparse_dense.txt" \
  -F "files=@sample_docs/langchain_parsers.json"
```

**JSON Response (`201 Created`):**
```json
{
  "success": true,
  "message": "Successfully indexed 8 chunks from 3 files into Pinecone knowledge base.",
  "documents_processed": 3,
  "total_chunks_indexed": 8,
  "files": [
    {
      "filename": "rag_hybrid_architecture.md",
      "file_type": "md",
      "chunks_count": 3,
      "total_characters": 1650
    },
    {
      "filename": "pinecone_sparse_dense.txt",
      "file_type": "txt",
      "chunks_count": 2,
      "total_characters": 950
    },
    {
      "filename": "langchain_parsers.json",
      "file_type": "json",
      "chunks_count": 3,
      "total_characters": 1100
    }
  ]
}
```

---

### 2. Retrieve Relevant Information
`POST /api/v1/documents/retrieve` (application/json)

Rewrites the user's question to optimize Pinecone retrieval, scales dense and sparse vectors using $\alpha$, and returns ranked chunks.

**Request Payload:**
```json
{
  "query": "Could you please tell me how does Pinecone handle the dotproduct distance metric and scaling?",
  "alpha": 0.5,
  "top_k": 3,
  "rewrite_query": true,
  "filter": null
}
```

- `alpha = 1.0`: Pure dense (semantic) retrieval.
- `alpha = 0.0`: Pure sparse (BM25 keyword) retrieval.
- `alpha = 0.5`: Balanced hybrid retrieval.
- `rewrite_query`: Automatically strips conversational noise ("Could you please tell me..."), isolates technical terms (`dotproduct`, `Pinecone`), and improves recall.

**JSON Response (`200 OK`):**
```json
{
  "original_query": "Could you please tell me how does Pinecone handle the dotproduct distance metric and scaling?",
  "rewritten_query": "Pinecone handle the dotproduct distance metric and scaling",
  "alpha_used": 0.5,
  "top_k": 3,
  "total_retrieved": 3,
  "chunks": [
    {
      "id": "rag_hybrid_architecture.md_chunk_2",
      "score": 0.3662,
      "content": "Pinecone requires the index distance metric to be set to `dotproduct` when conducting hybrid search. Under the dotproduct metric, the combined score equals the sum of the dense dot product and sparse dot product.",
      "source": "rag_hybrid_architecture.md",
      "metadata": {
        "chunk_id": "rag_hybrid_architecture.md_chunk_2",
        "file_type": "md",
        "source": "rag_hybrid_architecture.md"
      }
    }
  ]
}
```

---

### 3. Health & Knowledge Base Stats
- `GET /api/v1/health`: Checks Pinecone connection status.
- `GET /api/v1/stats`: Returns dimension (1536), metric (`dotproduct`), and BM25 status.

---

## 🧪 Testing

Run all unit and integration tests from project root or inside `rag_service`:
```bash
# From workspace root
.venv/bin/pytest -v

# Or from within rag_service
cd rag_service && ../.venv/bin/pytest -v
```
