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
