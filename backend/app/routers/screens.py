import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

logger = logging.getLogger("backend.app.routers.screens")
router = APIRouter(tags=["UI Screens"], include_in_schema=False)

# Resolve repository root / frontend directory
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


def _serve_screen(filename: str) -> FileResponse:
    """Safely serves an HTML screen from the frontend directory."""
    file_path = FRONTEND_DIR / filename
    if not file_path.is_file():
        logger.warning(f"Screen file '{filename}' not found at {file_path}")
        raise HTTPException(status_code=404, detail=f"Screen '{filename}' not found")
    return FileResponse(file_path, media_type="text/html")


def _clean_redirect(target_path: str, request: Request) -> RedirectResponse:
    """Redirects legacy .html paths to clean canonical URLs, preserving query parameters."""
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"{target_path}{query_str}", status_code=307)


# 1. Root & Default Screen
@router.get("/")
def root_screen() -> FileResponse:
    """Serves the main Dashboard screen at root URL."""
    return _serve_screen("dashboard.html")


@router.get("/index.html")
def redirect_index(request: Request) -> RedirectResponse:
    return _clean_redirect("/dashboard", request)


# 2. Dashboard Screen
@router.get("/dashboard")
def dashboard_screen() -> FileResponse:
    """Dashboard KPI metrics and recent sessions view."""
    return _serve_screen("dashboard.html")


@router.get("/dashboard.html")
def redirect_dashboard(request: Request) -> RedirectResponse:
    return _clean_redirect("/dashboard", request)


# 3. Live Support Console Screen
@router.get("/live-console")
def live_console_screen() -> FileResponse:
    """Live interactive chat console with real-time AI assistance."""
    return _serve_screen("live-console.html")


@router.get("/live-console.html")
def redirect_live_console(request: Request) -> RedirectResponse:
    return _clean_redirect("/live-console", request)


# 4. Session Configuration Screen
@router.get("/session-config")
def session_config_screen() -> FileResponse:
    """Configure new simulator, manual, or replay support sessions."""
    return _serve_screen("session-config.html")


@router.get("/session-config.html")
def redirect_session_config(request: Request) -> RedirectResponse:
    return _clean_redirect("/session-config", request)


# 5. Session History Screen
@router.get("/session-history")
def session_history_screen() -> FileResponse:
    """Searchable conversation history with status filters."""
    return _serve_screen("session-history.html")


@router.get("/session-history.html")
def redirect_session_history(request: Request) -> RedirectResponse:
    return _clean_redirect("/session-history", request)


# 6. Knowledge Base Screen
@router.get("/knowledge-base")
def knowledge_base_screen() -> FileResponse:
    """Document repository, upload, and hybrid RAG indexing status."""
    return _serve_screen("knowledge-base.html")


@router.get("/knowledge-base.html")
def redirect_knowledge_base(request: Request) -> RedirectResponse:
    return _clean_redirect("/knowledge-base", request)


# 6b. Add Product Screen
@router.get("/add-product")
def add_product_screen() -> FileResponse:
    """Add new product with required RAG knowledge base documents."""
    return _serve_screen("add-product.html")


@router.get("/add-product.html")
def redirect_add_product(request: Request) -> RedirectResponse:
    return _clean_redirect("/add-product", request)


# 7. Coaching Report Screen
@router.get("/coaching-report")
def coaching_report_screen() -> FileResponse:
    """Automated evaluation scores, empathy, and coaching recommendations."""
    return _serve_screen("coaching-report.html")


@router.get("/coaching-report.html")
def redirect_coaching_report(request: Request) -> RedirectResponse:
    return _clean_redirect("/coaching-report", request)


# 8. Dynamic fallback for any additional HTML screens
@router.get("/{screen_name}.html")
def dynamic_screen(screen_name: str, request: Request) -> RedirectResponse:
    """Redirects any additional .html screen to its clean path."""
    return _clean_redirect(f"/{screen_name}", request)
