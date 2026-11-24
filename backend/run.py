#!/usr/bin/env python3
"""
Entrypoint runner for the Backend API on Port 8000.
Can be executed from repository root or from inside backend/ directory:
    python backend/run.py
    cd backend && python run.py
"""
import os
import sys
from pathlib import Path

# Add project root and backend to sys.path so modules can be imported from anywhere
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
    from backend.app.config import settings
except ImportError:
    from app.config import settings

if __name__ == "__main__":
    print(f"Starting Backend API on http://{settings.host}:{settings.port}")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
