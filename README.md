# SupportCoach AI — Multi-Agent Customer Support Coaching Suite

An enterprise-grade, microservice-based AI coaching platform designed to elevate customer support operations. SupportCoach AI assists support agents during live conversations by analyzing customer sentiment and intent, retrieving grounding knowledge via hybrid dense + sparse vector search (Pinecone & NVIDIA NIM), generating context-aware response suggestions, and evaluating agent performance in real time using a 6-Agent Hybrid Orchestration pipeline.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |            Browser Client (UI)              |
                                      |     http://localhost:8000/live-console      |
                                      +---------------------------------------------+
                                                             |
                                           REST API & Clean URLs (No .html)
                                                             v
+-----------------------------------------------------------------------------------------------------------------------+
|                                              BACKEND MICROSERVICE (:8000)                                             |
|                                                                                                                       |
|  * FastAPI ASGI Application & Static Screen Routing (/dashboard, /live-console, /session-config, etc.)                 |
|  * 6-Agent Hybrid Coaching Pipeline (Supervisor, Query Analysis, RAG, Product Info, Response Gen, Coaching)          |
|  * LLM Provider Cascade: Groq (qwen/qwen3.8-27b) -> OpenAI -> Anthropic -> Gemini                                     |
|  * Supabase Client: PostgreSQL Relational Repositories & S3 Storage                                                   |
|  * Session Verification Authority (GET /api/sessions/{session_id}/verify)                                            |
+-----------------------------------------------------------------------------------------------------------------------+
                                        |                                        |
                     HTTP Client (X-Session-ID + Secret)                         | Live PostgREST Queries
                                        v                                        v
+-------------------------------------------------------------+  +------------------------------------------------------+
|                 RAG MICROSERVICE (:8001)                    |  |                 SUPABASE CLOUD                       |
|                                                             |  |                                                      |
|  * FastAPI Microservice with Session Auth Dependency        |  |  * PostgreSQL Database (sessions, messages,          |
|  * Pinecone Serverless Hybrid Index (1024d dotproduct)      |  |    products, coaching_reports, knowledge_documents)  |
|  * NVIDIA NIM Embeddings (nvidia/nemotron-3.5-embed-1b)     |  |  * Storage Bucket: knowledge-docs                    |
|  * BM25 Sparse Keyword Vectorizer                           |  |  * Row-Level Security (RLS) & Audit Triggers         |
|  * Groq Vision-Language Model (VLM Image Defect Parser)     |  +------------------------------------------------------+
|  * LangChain Query Rewriting & Pydantic Output Parsing      |
+-------------------------------------------------------------+
```

---

## Key Features

1. **Decoupled Dual-Microservice Architecture**:
   * **Backend Service (`:8000`)**: Handles user authentication, session lifecycle, message streams, product catalog queries, coaching evaluation reports, and UI screen delivery.
   * **RAG Microservice (`:8001`)**: Independent vector search and document ingestion engine isolating heavy vector computation and multimodal processing from web serving.
2. **Session Verification Protocol**:
   * Every backend-to-RAG request transmits an `X-Session-ID: SES-...` header and internal shared secret. The RAG service actively validates the session against the backend's verification endpoint before returning knowledge context.
3. **Pinecone Hybrid Search & NVIDIA NIM**:
   * Combines dense semantic vector retrieval via NVIDIA NIM (`nvidia/nemotron-3.5-embed-1b`, 1024 dimensions) with sparse keyword retrieval via BM25, dynamically scaled by alpha weighting (`alpha=0.5`).
4. **Live LLM Inference (Zero Mock Data)**:
   * Powered by Groq's low-latency inference using `qwen/qwen3.8-27b`. In production mode, mock fallbacks are completely disabled.
5. **Multimodal Defect Diagnosis**:
   * Analyzes customer-uploaded hardware defect photos using Groq VLM (`qwen/qwen3.8-27b`) and indexes visual descriptions for instant troubleshooting retrieval.
6. **Clean URL & Stale Cache Prevention**:
   * All frontend pages use clean RESTful URLs (`/live-console`, `/dashboard`, etc.) with automatic HTTP 307 redirects for legacy `.html` requests, combined with `Cache-Control: no-cache, no-store, must-revalidate` headers.

---

## File Structure

```text
AI_customer/
├── backend/                                # Backend Microservice (Port 8000)
│   ├── .env                                # Backend production environment config
│   ├── .env.example                        # Example backend environment template
│   ├── Dockerfile                          # Backend container definition
│   ├── requirements.txt                    # Backend Python dependencies
│   ├── run.py                              # Standalone Python entrypoint for backend
│   ├── app/
│   │   ├── config.py                       # Pydantic Settings & environment parsing
│   │   ├── main.py                         # FastAPI application factory & router registration
│   │   ├── llm/
│   │   │   ├── coaching.py                 # Evaluation & coaching agent logic
│   │   │   ├── fallback_service.py         # Cascading LLM caller (Groq -> OpenAI -> etc.)
│   │   │   ├── mock_generator.py           # Offline unit-testing fixtures
│   │   │   ├── prompts.py                  # System prompts & output parser definitions
│   │   │   └── simulator.py                # Customer persona response simulator
│   │   ├── middleware/                     # Custom HTTP middlewares (Cache-Control, CORS)
│   │   ├── routers/
│   │   │   ├── analytics.py                # Performance KPIs & metrics endpoints
│   │   │   ├── coaching_reports.py         # Coaching evaluation report endpoints
│   │   │   ├── knowledge.py                # Knowledge document management endpoints
│   │   │   ├── messages.py                 # Chat message & agent execution endpoints
│   │   │   ├── multimodal.py               # Image upload & defect diagnosis endpoints
│   │   │   ├── products.py                 # Product catalog endpoints
│   │   │   ├── screens.py                  # HTML template routers & clean 307 redirects
│   │   │   ├── sessions.py                 # Support session lifecycle & verification endpoint
│   │   │   └── streaming.py                # Real-time SSE/Streaming agent endpoints
│   │   ├── schemas/                        # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── dataset_service.py          # Session analytics & report aggregation
│   │   │   ├── knowledge_service.py        # Knowledge base coordination
│   │   │   ├── message_service.py          # Conversation processing & agent coordination
│   │   │   ├── product_service.py          # Product catalog operations
│   │   │   ├── rag_client.py               # HTTP client calling standalone RAG service
│   │   │   ├── report_service.py           # Coaching report generation & persistence
│   │   │   └── session_service.py          # Session management & status updates
│   │   ├── supabase_client/
│   │   │   ├── client.py                   # Supabase Client factory (PyPI supabase library)
│   │   │   ├── knowledge_repo.py           # Knowledge document metadata repository
│   │   │   ├── message_repo.py             # Conversation messages repository
│   │   │   ├── mock_store.py               # In-memory store for offline unit tests
│   │   │   ├── product_repo.py             # Products catalog repository
│   │   │   ├── report_repo.py              # Coaching reports repository
│   │   │   ├── session_repo.py             # Support sessions repository
│   │   │   └── storage.py                  # Supabase Storage S3 client wrapper
│   │   └── utils/                          # Common date, string & logging utilities
│   └── tests/                              # Backend test suite (LLM, Schemas, Repos, Screens)
│
├── rag_service/                            # Standalone RAG Microservice (Port 8001)
│   ├── .env                                # RAG service production environment config
│   ├── Dockerfile                          # RAG service container definition
│   ├── requirements.txt                    # RAG dependencies (Pinecone, NVIDIA NIM, LangChain)
│   ├── run.py                              # Standalone Python entrypoint for RAG service
│   ├── config.py                           # Dataclass settings for RAG microservice
│   ├── pipeline.py                         # CLI indexing & retrieval orchestrator
│   ├── service.py                          # Async RAG service layer for FastAPI
│   ├── api/
│   │   ├── app.py                          # FastAPI RAG microservice application factory
│   │   ├── auth.py                         # Inter-service session verification dependency
│   │   ├── routes.py                       # Ingest, retrieve, diagnose & health endpoints
│   │   └── schemas.py                      # Request/Response models for RAG operations
│   ├── generation/
│   │   └── rag_chain.py                    # LangChain LCEL RAG chain (Groq / OpenAI + Parsers)
│   ├── indexing/
│   │   ├── indexer.py                      # Pinecone hybrid indexer & vector upsert logic
│   │   └── versioning.py                   # Document versioning & deduplication tracker
│   ├── parsers/
│   │   ├── document_parsers.py             # Multi-format ingestor (PDF, TXT, JSON)
│   │   ├── docx_parser.py                  # Microsoft Word (.docx) document loader
│   │   ├── output_parsers.py               # Pydantic structured output validation
│   │   └── vlm_image_parser.py             # Groq VLM image defect transcription engine
│   ├── retrieval/
│   │   ├── bm25_sparse.py                  # BM25 sparse vector encoder
│   │   ├── embeddings.py                   # NVIDIA NIM AI Foundation Embeddings (1024d)
│   │   ├── hybrid_retriever.py             # Pinecone hybrid search with alpha blending
│   │   ├── query_rewriter.py               # LLM query de-noising & keyword optimizer
│   │   └── reranker.py                     # Cross-encoder semantic re-ranking
│   ├── sample_docs/                        # Sample hardware & software support manuals
│   └── tests/                              # RAG test suite (Hybrid, Embeddings, Ingestion)
│
├── frontend/                               # Frontend Web Client
│   ├── index.html                          # Root entrypoint (redirects to /dashboard)
│   ├── dashboard.html                      # Executive KPI metrics & overview
│   ├── live-console.html                   # Real-time interactive 6-Agent coaching console
│   ├── session-config.html                 # Simulator & manual session configuration screen
│   ├── session-history.html                # Searchable conversation log & filter screen
│   ├── knowledge-base.html                 # RAG document management & ingestion screen
│   ├── coaching-report.html                # Post-session performance evaluation review
│   ├── css/                                # Modern dark/light glassmorphic stylesheets
│   └── js/                                 # Pure Vanilla ES6 JavaScript modules
│       ├── api.js                          # Centralized REST client with error handling
│       ├── console.js                      # Live conversation & multi-agent card renderer
│       ├── dashboard.js                    # Analytics charts & KPI counter updater
│       ├── history.js                      # Session history tables & status filters
│       ├── main.js                         # Global navigation, sidebar & toast utilities
│       └── session.js                      # Session launcher & simulator trigger
│
├── supabase/                               # Database Schemas & Migrations
│   └── migrations/
│       ├── 20261123_01_initial_schema.sql  # Products, sessions, messages, reports tables
│       ├── 20261123_02_rls_policies.sql    # Row-Level Security policies
│       ├── 20261123_03_soft_deletes.sql    # Soft delete triggers & audit timestamps
│       └── 20261124_04_grant_permissions.sql # PostgreSQL schema & table permission grants
│
├── Docs/                                   # Architectural & API Specifications
│   ├── API_DOCUMENTATION.md                # Comprehensive REST endpoint specifications
│   └── DATABASE_SCHEMA.md                  # Supabase PostgreSQL relational data dictionary
│
├── conftest.py                             # Root pytest configuration & test isolation hook
├── docker-compose.yml                      # Multi-container orchestration (Backend + RAG)
└── pytest.ini                              # Global test runner settings
```

---

## Environment Setup & Configuration

Both microservices maintain independent configuration files.

### 1. Backend Configuration (`backend/.env`)

Create or update `backend/.env`:
```env
# Server
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
APP_NAME="AI Customer Coaching Assistant"
API_PREFIX=/api
LOG_LEVEL=INFO

# Standalone RAG Microservice URL & Shared Secret
RAG_SERVICE_URL=http://localhost:8001
RAG_INTERNAL_SECRET=rag-backend-secret-key-2026

# Supabase PostgreSQL & Storage Credentials
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_KEY=<your-anon-jwt-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-secret-or-pat>
SUPABASE_STORAGE_BUCKET=knowledge-docs
FORCE_MOCK_SUPABASE=false

# LLM Providers (Active Model: Qwen 3.8 on Groq)
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=qwen/qwen3.8-27b
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Allowed CORS Origins
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://0.0.0.0:8000,http://localhost:8001
```

### 2. RAG Microservice Configuration (`rag_service/.env`)

Create or update `rag_service/.env`:
```env
# Server
ENVIRONMENT=production
PORT=8001
HOST=0.0.0.0
BACKEND_URL=http://localhost:8000
RAG_INTERNAL_SECRET=rag-backend-secret-key-2026
VERIFY_SESSIONS_WITH_BACKEND=true

# Pinecone Serverless Hybrid Search
PINECONE_API_KEY=<your-pinecone-api-key>
PINECONE_INDEX_NAME=rag-hybrid-search
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# NVIDIA NIM AI Foundation Inference (Embeddings)
NVIDIA_API_KEY=<your-nvidia-api-key>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3.5-embed-1b
EMBEDDING_DIMENSION=1024

# Groq Vision-Language Model (VLM & Generation)
GROQ_API_KEY=<your-groq-api-key>
GROQ_VLM_MODEL=qwen/qwen3.8-27b
VLM_MAX_TOKENS=1024

# Retrieval Parameters
HYBRID_ALPHA=0.5
TOP_K=5
CHUNK_SIZE=800
CHUNK_OVERLAP=150
```

### 3. Supabase One-Time Database Setup

If you created your Supabase tables manually or via migrations, execute the following SQL in your **[Supabase SQL Editor](https://supabase.com/dashboard)** to grant proper permissions to `service_role` and `anon`:

```sql
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
```
*(Also available in `supabase/migrations/20261124_04_grant_permissions.sql`)*.

---

## How to Run the Project

### Method 1: Using `uv run uvicorn` (Recommended)

You can run both servers using `uv run` from any terminal location:

#### Terminal 1 — Backend Service (Port 8000)
```bash
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2 — RAG Microservice (Port 8001)
```bash
uv run uvicorn rag_service.api.app:app --host 0.0.0.0 --port 8001 --reload
```

---

### Method 2: Using Python Directly

Activate your virtual environment and launch each microservice runner:

#### Terminal 1 — Backend Service (Port 8000)
```bash
source .venv/bin/activate
python backend/run.py
```

#### Terminal 2 — RAG Microservice (Port 8001)
```bash
source .venv/bin/activate
python rag_service/run.py
```

---

### Method 3: Containerized with Docker Compose

Run both services with automatic health checks in Docker:

```bash
docker compose up --build
```

---

## Verifying the Deployment

Once both servers are running:

| Service / Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Live Support Console** | [http://0.0.0.0:8000/live-console](http://0.0.0.0:8000/live-console) | Real-time chat & 6-Agent AI coaching UI |
| **Executive Dashboard** | [http://0.0.0.0:8000/dashboard](http://0.0.0.0:8000/dashboard) | Conversation metrics, resolution rates, CSAT |
| **Session Configurator** | [http://0.0.0.0:8000/session-config](http://0.0.0.0:8000/session-config) | Launch simulator scenarios & personas |
| **Knowledge Base (RAG)** | [http://0.0.0.0:8000/knowledge-base](http://0.0.0.0:8000/knowledge-base) | Upload support PDFs, manuals & images |
| **Backend API Docs** | [http://0.0.0.0:8000/docs](http://0.0.0.0:8000/docs) | Interactive Swagger UI for Backend |
| **RAG Service API Docs** | [http://0.0.0.0:8001/docs](http://0.0.0.0:8001/docs) | Interactive Swagger UI for RAG Microservice |
| **Backend Health** | [http://0.0.0.0:8000/health](http://0.0.0.0:8000/health) | Backend healthcheck JSON |
| **RAG Service Health** | [http://0.0.0.0:8001/health](http://0.0.0.0:8001/health) | Vector index & embedder healthcheck JSON |

---

## Testing & Quality Assurance

The repository includes a comprehensive test suite of **115 automated tests** covering unit behavior, schema contracts, screen routers, LLM fallbacks, and inter-service session verification.

Run all tests:
```bash
uv run pytest
```
*Or using the virtualenv runner:*
```bash
.venv/bin/pytest backend/tests/ rag_service/tests/ -v
```

### Key Test Coverage:
* **`rag_service/tests/test_session_verification.py`**: Verifies that requests without `X-Session-ID` or with invalid backend tokens receive `401 Unauthorized`.
* **`backend/tests/test_rag_client.py`**: Validates that `RAGServiceClient` correctly constructs headers and handles graceful fallback when network limits are reached.
* **`backend/tests/test_screens.py`**: Ensures all 7 frontend screens serve clean HTML and redirect legacy `.html` requests via HTTP 307.
* **`backend/tests/test_live_flow.py`**: End-to-end integration test validating session generation, RAG verification, and real-time coaching pipeline execution.

---

## Inter-Service Communication Flow

```
[Customer / Employee]
         |
         | 1. POST /api/sessions/{session_id}/messages
         v
[Backend Service:8000]
         |
         | 2. POST /api/v1/documents/retrieve
         |    Headers: { X-Session-ID: "SES-...", X-Internal-Secret: "..." }
         v
[RAG Service:8001]
         |
         | 3. GET /api/sessions/{session_id}/verify (Auth Validation)
         v
[Backend Service:8000] ---> Confirms session is active (200 OK)
         |
         v
[RAG Service:8001]
         | 4. Hybrid Search: NVIDIA Dense (1024d) + BM25 Sparse -> Pinecone
         | 5. Synthesize grounded context using Groq LLM
         v
[Backend Service:8000]
         | 6. Executes 6-Agent Coaching Pipeline (Groq Qwen 3.8)
         | 7. Persists messages & coaching metrics to Supabase
         v
[Browser Client]
         | 8. Renders updated chat bubble, agent cards & suggested response
```

---

## License & Attribution
Developed for Enterprise AI Customer Support Operations. Built with FastAPI, LangChain, Pinecone, NVIDIA NIM, Groq, and Supabase.
