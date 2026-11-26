import logging
from typing import Any, Optional
from backend.app.config import get_settings
from backend.app.supabase_client.mock_store import (
    MockStore,
    MockStorageClient,
    MockTableQueryBuilder,
)

import sys

logger = logging.getLogger(__name__)

_mock_store_instance: Optional[MockStore] = None


def get_mock_store() -> MockStore:
    global _mock_store_instance
    for mod_name in ("backend.app.supabase_client.client", "app.supabase_client.client"):
        if mod_name in sys.modules:
            inst = getattr(sys.modules[mod_name], "_mock_store_instance", None)
            if inst is not None:
                _mock_store_instance = inst
                return _mock_store_instance
    if _mock_store_instance is None:
        _mock_store_instance = MockStore()
        for mod_name in ("backend.app.supabase_client.client", "app.supabase_client.client"):
            if mod_name in sys.modules:
                setattr(sys.modules[mod_name], "_mock_store_instance", _mock_store_instance)
    return _mock_store_instance


def reset_mock_store() -> None:
    store = get_mock_store()
    store.reset()


class MockSupabaseClient:
    """
    Mock client that provides standard Supabase table() and storage interfaces.
    """

    def __init__(self, store: MockStore):
        self.store = store
        self.storage = MockStorageClient(store)

    def table(self, table_name: str) -> MockTableQueryBuilder:
        return MockTableQueryBuilder(self.store, table_name)


def get_supabase_client(force_mock: bool = False) -> Any:
    """
    Factory providing a live Supabase client if credentials are configured and the
    package is present, otherwise falling back transparently to MockSupabaseClient.
    Prioritizes SUPABASE_SERVICE_ROLE_KEY for server operations, falling back to SUPABASE_KEY.
    """
    settings = get_settings()
    supabase_url = (settings.supabase_url or "").strip().strip('"').strip("'")
    raw_key = settings.supabase_service_role_key or settings.supabase_key or ""
    active_key = raw_key.strip().strip('"').strip("'")

    if (
        force_mock
        or settings.force_mock_supabase
        or not supabase_url
        or not active_key
    ):
        return MockSupabaseClient(get_mock_store())

    try:
        # Filter out local project root so local 'supabase/' folder doesn't shadow PyPI package
        from pathlib import Path
        repo_root = str(Path(__file__).resolve().parents[3])
        orig_sys_path = list(sys.path)
        sys.path = [p for p in sys.path if p not in (repo_root, "", ".")]
        try:
            from supabase import Client, create_client
        finally:
            sys.path = orig_sys_path

        client: Client = create_client(supabase_url, active_key)
        return client
    except ImportError:
        logger.info(
            "Supabase library not installed in environment. Falling back to MockSupabaseClient."
        )
        return MockSupabaseClient(get_mock_store())
    except Exception as e:
        logger.warning(
            f"Failed to initialize live Supabase client: {e}. Falling back to MockSupabaseClient."
        )
        return MockSupabaseClient(get_mock_store())
