# AI Customer Support Coaching Assistant

A SaaS-style web application designed to help customer support employees analyze customer complaints, retrieve relevant product and knowledge-base context via RAG, receive AI-suggested responses, and review automated coaching evaluations.

## Architecture Overview
- **Frontend (HTML5, CSS3, Vanilla JS):** Communicates strictly via REST APIs.
- **Backend (Python Team):** REST API, SQL Database integration, RAG Pipeline.
- **Multi-Agent Hybrid Pattern (AI Team):**
  1. **Supervisor Agent** (Orchestration: Sequential + Parallel coordination)
  2. **Query Analysis Agent** (Intent, sentiment, issue extraction)
  3. **Knowledge Retrieval Agent** (RAG articles, troubleshooting)
  4. **Product Information Agent** (Product specs & warranty context)
  5. **Response Generation Agent** (Drafted professional response)
  6. **Evaluation & Coaching Agent** (Response quality score & coaching tips)

## Folder Structure
- `frontend/` — Complete responsive UI (`index.html`, module pages, `css/`, `js/`)
- `backend-integration/` — `API_DOCUMENTATION.md` & `DATABASE_SCHEMA.md`

## Quick Start (Frontend)
1. Serve `frontend/` on a local web server:
   `python -m http.server 5500 --directory frontend`
2. Open `http://localhost:5500`.
3. By default, **Mock Mode** is enabled using labelled mock data.
4. To connect to the Python backend, click **Switch to Live API** in the sidebar footer (or update `API_BASE_URL` and `USE_MOCK` in `frontend/js/api.js`).

## Team Integration Rules
- Never connect the browser directly to SQL.
- Backend developers must follow the JSON contracts in `backend-integration/API_DOCUMENTATION.md`.
- Frontend developers should keep all HTTP requests inside `frontend/js/api.js`.