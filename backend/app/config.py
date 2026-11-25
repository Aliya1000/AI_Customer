import json
from functools import lru_cache
from typing import Any, List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Customer Coaching Assistant"
    api_prefix: str = "/api"
    port: int = 8000
    host: str = "0.0.0.0"
    log_level: str = "INFO"
    environment: str = "development"

    # Allowed CORS Origins - support comma-separated strings or list of strings
    cors_origins: Union[str, List[str]] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "*",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Standalone RAG Microservice URL & Authentication
    rag_service_url: str = "http://localhost:8001"
    rag_internal_secret: str = "rag-backend-secret-key-2026"

    # Supabase credentials (optional for offline mock mode)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_storage_bucket: str = "knowledge-docs"
    force_mock_supabase: bool = False

    # LLM API keys & Models
    groq_api_key: Optional[str] = None
    groq_model: str = "openai/gpt-oss-20b"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Pinecone / RAG settings
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = "rag-hybrid-search"

    model_config = SettingsConfigDict(
        env_file=["backend/.env", ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
