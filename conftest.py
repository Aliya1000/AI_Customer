import os
import sys
from pathlib import Path

# Set test environment flags so unit test suites use isolated test harness
os.environ["ENVIRONMENT"] = "test"
os.environ["FORCE_MOCK_SUPABASE"] = "true"

# Ensure root is in sys.path
root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Ensure SQLite tables exist for tests that use ASGITransport without lifespan
try:
    from database.db_config import init_db
    init_db()
except Exception:
    pass
