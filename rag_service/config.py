import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Base directory for the self-contained RAG service
_PKG_DIR = Path(__file__).resolve().parent

# Load environment variables: check current dir, package dir, or workspace root
_env_candidates = [
    Path.cwd() / ".env",
    _PKG_DIR / ".env",
    _PKG_DIR.parent / ".env",
]
for _env_path in _env_candidates:
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()


@dataclass
class Settings:
    # Directory paths
    base_dir: Path = _PKG_DIR
    data_dir: Path = _PKG_DIR / "data"
    sample_docs_dir: Path = _PKG_DIR / "sample_docs"

    # Pinecone
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "rag-hybrid-search")
    pinecone_cloud: str = os.getenv("PINECONE_CLOUD", "aws")
    pinecone_region: str = os.getenv("PINECONE_REGION", "us-east-1")

    # NVIDIA Inference Configuration (Dense Embeddings)
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_base_url: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_embedding_model: str = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3.5-embed-1b")

    # Groq Configuration for Vision VLM (using langchain-groq)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "") or (os.getenv("OPENAI_API_KEY", "") if os.getenv("OPENAI_API_KEY", "").startswith("gsk_") else "")
    groq_vlm_model: str = os.getenv("GROQ_VLM_MODEL", "qwen/qwen3.8-27b")

    # Vision-Language Model (VLM) for Image Text & Document Extraction
    vlm_provider: str = os.getenv("VLM_PROVIDER", "groq")  # 'groq' or 'nvidia'
    vlm_model_name: str = os.getenv("VLM_MODEL_NAME", "qwen/qwen3.8-27b")
    vlm_base_url: str = os.getenv("VLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    vlm_max_tokens: int = int(os.getenv("VLM_MAX_TOKENS", "1024"))

    # OpenAI / Fallback LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model_name: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Vector Embedding Dimension (1024 for nvidia/nv-embedqa-e5-v5, 1536 for OpenAI)
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # Hybrid Search Settings
    # alpha: 1.0 = 100% dense, 0.0 = 100% sparse (BM25), 0.5 = 50% dense + 50% sparse
    hybrid_alpha: float = float(os.getenv("HYBRID_ALPHA", "0.5"))
    top_k: int = int(os.getenv("TOP_K", "5"))

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # BM25 model path for persistence (defaults to data/bm25_params.json inside package)
    bm25_params_path: str = os.getenv(
        "BM25_PARAMS_PATH",
        str((_PKG_DIR / "data" / "bm25_params.json") if (_PKG_DIR / "data" / "bm25_params.json").exists() else (_PKG_DIR / "bm25_params.json"))
    )


settings = Settings()
