"""
FastAPI Microservice Application for Pinecone Hybrid RAG.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .routes import router, get_rag_service
from ..config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown resource management."""
    # Initialize service singleton and verify Pinecone index on startup
    service = get_rag_service()
    print(f"Starting RAG Microservice (Pinecone Index: {settings.pinecone_index_name}, Mock Mode: {service.mock_mode})")
    yield
    print("Shutting down RAG Microservice.")


def create_app() -> FastAPI:
    """Factory function to build and configure the FastAPI application instance."""
    app = FastAPI(
        title="Pinecone Hybrid Search RAG Microservice",
        description=(
            "Microservice providing concurrent multi-document ingestion (PDF, Markdown, TXT, JSON), "
            "LangChain parsing and recursive chunking, BM25 + dense hybrid vector storage in Pinecone, "
            "and query-rewriting hybrid information retrieval. (LLM generation decoupled)."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Enable CORS for cross-origin frontend or other microservices
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include RAG API router
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        """Redirects root to interactive OpenAPI Swagger documentation."""
        return RedirectResponse(url="/docs")

    return app


# Main application instance for ASGI servers (e.g. uvicorn rag_service.api.app:app)
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rag_service.api.app:app", host="0.0.0.0", port=8000, reload=True)
