from .sessions import router as sessions_router
from .messages import router as messages_router
from .knowledge import router as knowledge_router
from .coaching_reports import router as coaching_reports_router
from .products import router as products_router
from .streaming import router as streaming_router
from .multimodal import router as multimodal_router
from .analytics import router as analytics_router
from .screens import router as screens_router

__all__ = [
    "sessions_router",
    "messages_router",
    "knowledge_router",
    "coaching_reports_router",
    "products_router",
    "streaming_router",
    "multimodal_router",
    "analytics_router",
    "screens_router",
]
