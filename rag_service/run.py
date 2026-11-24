#!/usr/bin/env python3
"""
Entrypoint runner for the Standalone RAG Microservice on Port 8001.
Can be executed from repository root or from inside rag_service/ directory:
    python rag_service/run.py
    cd rag_service && python run.py
"""
import os
import sys
from pathlib import Path

# Add project root and rag_service to sys.path so modules can be imported from anywhere
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
for p in [str(REPO_ROOT), str(CURRENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set PYTHONPATH for uvicorn reload subprocesses
existing_pythonpath = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = f"{REPO_ROOT}:{CURRENT_DIR}:{existing_pythonpath}"

import uvicorn
try:
    from rag_service.config import settings
except ImportError:
    from config import settings

if __name__ == "__main__":
    print(f"Starting Pinecone Hybrid RAG Microservice on http://{settings.host}:{settings.port}")
    uvicorn.run(
        "rag_service.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
