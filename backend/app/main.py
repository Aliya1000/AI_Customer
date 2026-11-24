import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from backend.app.config import settings
    from backend.app.routers import (
        sessions_router,
        messages_router,
        knowledge_router,
        coaching_reports_router,
        products_router,
        streaming_router,
        multimodal_router,
        analytics_router,
        screens_router,
    )
    from backend.app.services.session_service import SessionService
except ImportError:
    from app.config import settings
    from app.routers import (
        sessions_router,
        messages_router,
        knowledge_router,
        coaching_reports_router,
        products_router,
        streaming_router,
        multimodal_router,
        analytics_router,
        screens_router,
    )
    from app.services.session_service import SessionService

logger = logging.getLogger("backend.app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown actions."""
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    yield
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.app_name,
        description="Backend API for AI Customer Support Coaching Assistant",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1.1 Cache Control Middleware (prevents stale cached JS/CSS in development)
    @app.middleware("http")
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".js", ".css", ".html")) or "/api" in request.url.path:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # 2. Global Exception Handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # 3. Mount all modular routers under /api prefix
    api_prefix = settings.api_prefix.rstrip("/")
    app.include_router(products_router, prefix=api_prefix)
    app.include_router(sessions_router, prefix=api_prefix)
    app.include_router(messages_router, prefix=api_prefix)
    app.include_router(knowledge_router, prefix=api_prefix)
    app.include_router(coaching_reports_router, prefix=api_prefix)
    app.include_router(streaming_router, prefix=api_prefix)
    app.include_router(multimodal_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)

    # 4. Health and root diagnostic endpoints
    @app.get(f"{api_prefix}", tags=["Health"])
    def api_root():
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "status": "online",
            "environment": settings.environment,
        }

    @app.get("/health", tags=["Health"])
    @app.get(f"{api_prefix}/health", tags=["Health"])
    def health():
        return {"status": "healthy"}

    # 5. Static frontend assets & UI Screen routes
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_dir.exists():
        css_dir = frontend_dir / "css"
        js_dir = frontend_dir / "js"
        if css_dir.is_dir():
            app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
        if js_dir.is_dir():
            app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
        app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_app")

    # 6. Mount HTML screen router
    app.include_router(screens_router)

    return app


app = create_app()
