"""Global fixtures and configuration for hermetic offline E2E tests."""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# 1. Force Hermetic Offline Environment Variables
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["PINECONE_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "mock"

# 2. Add Paths to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
for p in [str(REPO_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session")
def app_instance():
    """Provides the FastAPI application instance with fallback for early collection."""
    try:
        from app.main import app
        return app
    except (ImportError, ModuleNotFoundError):
        from fastapi import FastAPI
        return FastAPI(title="AI Customer Support Coaching Assistant (Mock Test Harness)")


@pytest.fixture
def client(app_instance):
    """Provides a fresh TestClient for each test."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_mock_state():
    """Resets mock database tables and mock storage before every test."""
    try:
        from app.supabase_client.client import reset_mock_store
        reset_mock_store()
    except (ImportError, AttributeError, ModuleNotFoundError):
        pass
    yield


@pytest.fixture
def sample_session_payload():
    return {
        "interaction_mode": "simulator",
        "product_name": "AeroSound Pro ANC Headphones",
        "product_context": "Purchased 3 months ago, firmware v2.1 installed",
        "customer_scenario": "The right ear cup has an annoying buzzing noise whenever ANC is enabled.",
        "persona": "Patient",
        "emotional_progression": "escalating_to_calm",
        "replay_transcript": None,
    }


@pytest.fixture
def sample_manual_session_payload():
    return {
        "interaction_mode": "manual",
        "product_name": "PulseWatch S4 Smartwatch",
        "product_context": "Purchased last week",
        "customer_scenario": "Screen went blank while running.",
        "persona": "Standard",
        "emotional_progression": None,
        "replay_transcript": None,
    }


@pytest.fixture
def sample_txt_file():
    content = (
        b"Troubleshooting Guide:\n"
        b"1. Reset headphones by holding power button for 10s.\n"
        b"2. Ensure ANC mode is calibrated in the app."
    )
    return ("audio_troubleshooting.txt", content, "text/plain")


@pytest.fixture
def sample_pdf_file():
    # Minimal valid PDF header/trailer bytes
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n140\n%%EOF"
    )
    return ("pulsewatch_manual.pdf", content, "application/pdf")


@pytest.fixture
def sample_json_file():
    content = b'{"troubleshooting": [{"issue": "buzzing", "solution": "factory reset"}]}'
    return ("knowledge_base.json", content, "application/json")
