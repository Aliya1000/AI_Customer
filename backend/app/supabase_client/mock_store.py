import copy
import threading
from typing import Any, Dict, List, Optional, Union


class MockQueryResult:
    def __init__(self, data: Any, count: Optional[int] = None):
        self.data = data
        self.count = count if count is not None else (len(data) if isinstance(data, list) else 1)


class MockTableQueryBuilder:
    def __init__(self, store: "MockStore", table_name: str):
        self.store = store
        self.table_name = table_name
        self.filters: List[tuple] = []
        self._order_by: Optional[str] = None
        self._desc: bool = False
        self._limit: Optional[int] = None
        self._action: str = "select"
        self._payload: Any = None

    def select(self, columns: str = "*"):
        self._action = "select"
        return self

    def insert(self, values: Union[Dict[str, Any], List[Dict[str, Any]]]):
        self._action = "insert"
        self._payload = values
        return self

    def update(self, values: Dict[str, Any]):
        self._action = "update"
        self._payload = values
        return self

    def delete(self):
        self._action = "delete"
        return self

    def eq(self, column: str, value: Any):
        self.filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any):
        self.filters.append(("neq", column, value))
        return self

    def in_(self, column: str, values: List[Any]):
        self.filters.append(("in", column, values))
        return self

    def order(self, column: str, desc: bool = False):
        self._order_by = column
        self._desc = desc
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def execute(self) -> MockQueryResult:
        return self.store.execute_query(self)


class MockStorageBucket:
    def __init__(self, store: "MockStore", bucket_name: str):
        self.store = store
        self.bucket_name = bucket_name

    def upload(self, path: str, file: bytes, file_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.store.storage_upload(self.bucket_name, path, file, file_options)

    def download(self, path: str) -> bytes:
        return self.store.storage_download(self.bucket_name, path)

    def remove(self, paths: List[str]) -> List[Dict[str, Any]]:
        return self.store.storage_remove(self.bucket_name, paths)

    def list(self, path: str = "") -> List[Dict[str, Any]]:
        return self.store.storage_list(self.bucket_name, path)

    def create_signed_url(self, path: str, expires_in: int = 3600) -> Dict[str, Any]:
        return {
            "signedURL": f"https://mock-supabase.local/storage/v1/object/sign/{self.bucket_name}/{path}?expires_in={expires_in}"
        }


class MockStorageClient:
    def __init__(self, store: "MockStore"):
        self.store = store

    def from_(self, bucket_name: str) -> MockStorageBucket:
        return MockStorageBucket(self.store, bucket_name)


class MockStore:
    """
    Thread-safe in-memory database and storage mock for PostgREST & Supabase Storage emulation.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "products": [],
            "sessions": [],
            "messages": [],
            "knowledge_documents": [],
            "coaching_reports": [],
        }
        self.storage: Dict[str, Dict[str, bytes]] = {
            "knowledge-docs": {}
        }
        self.storage_meta: Dict[str, Dict[str, Dict[str, Any]]] = {
            "knowledge-docs": {}
        }
        self.seed_defaults()

    def seed_defaults(self):
        with self._lock:
            self.tables = {
                "products": [
                    {
                        "product_id": "PRD-01",
                        "product_name": "AeroSound Pro ANC Headphones",
                        "product_description": "Wireless Bluetooth 5.3 over-ear headphones with Hybrid Active Noise Cancellation and 1-year hardware warranty.",
                        "product_category": "Audio Hardware",
                    },
                    {
                        "product_id": "PRD-02",
                        "product_name": "PulseWatch S4 Smartwatch",
                        "product_description": "AMOLED fitness smartwatch with 5ATM water resistance and 10-day battery life.",
                        "product_category": "Wearables",
                    },
                    {
                        "product_id": "PRD-03",
                        "product_name": "CloudDesk CRM Pro Subscription",
                        "product_description": "Enterprise multi-seat SaaS subscription with SSO, API access, and 99.9% SLA.",
                        "product_category": "SaaS Software",
                    },
                ],
                "sessions": [],
                "messages": [],
                "knowledge_documents": [],
                "coaching_reports": [],
            }

            self.storage = {
                "knowledge-docs": {}
            }
            self.storage_meta = {
                "knowledge-docs": {}
            }

    def reset(self):
        self.seed_defaults()

    def _matches_filters(self, record: Dict[str, Any], filters: List[tuple]) -> bool:
        for op, col, val in filters:
            rec_val = record.get(col)
            if op == "eq" and rec_val != val:
                return False
            elif op == "neq" and rec_val == val:
                return False
            elif op == "in" and rec_val not in val:
                return False
        return True

    def execute_query(self, builder: MockTableQueryBuilder) -> MockQueryResult:
        with self._lock:
            table = self.tables.get(builder.table_name)
            if table is None:
                self.tables[builder.table_name] = []
                table = self.tables[builder.table_name]

            if builder._action == "select":
                matching = [copy.deepcopy(r) for r in table if self._matches_filters(r, builder.filters)]
                if builder._order_by:
                    key = builder._order_by

                    def _get_sort_val(x):
                        v = x.get(key)
                        if v is None:
                            return (0, "")
                        if isinstance(v, (int, float)):
                            return (1, v)
                        return (2, str(v))

                    matching.sort(key=_get_sort_val, reverse=builder._desc)
                if builder._limit is not None:
                    matching = matching[: builder._limit]
                return MockQueryResult(matching)

            elif builder._action == "insert":
                payload = builder._payload
                items = copy.deepcopy(payload if isinstance(payload, list) else [payload])
                for item in items:
                    table.append(item)
                return MockQueryResult(copy.deepcopy(items))

            elif builder._action == "update":
                updated = []
                for r in table:
                    if self._matches_filters(r, builder.filters):
                        r.update(copy.deepcopy(builder._payload))
                        updated.append(copy.deepcopy(r))
                return MockQueryResult(updated)

            elif builder._action == "delete":
                remaining = []
                deleted = []
                deleted_ids = []
                for r in table:
                    if self._matches_filters(r, builder.filters):
                        deleted.append(copy.deepcopy(r))
                        if builder.table_name == "sessions":
                            deleted_ids.append(r.get("session_id"))
                    else:
                        remaining.append(r)
                self.tables[builder.table_name] = remaining

                # Cascade delete for sessions -> messages and coaching_reports
                if builder.table_name == "sessions" and deleted_ids:
                    self.tables["messages"] = [
                        m for m in self.tables.get("messages", []) if m.get("session_id") not in deleted_ids
                    ]
                    self.tables["coaching_reports"] = [
                        cr for cr in self.tables.get("coaching_reports", []) if cr.get("session_id") not in deleted_ids
                    ]

                return MockQueryResult(deleted)

            raise ValueError(f"Unsupported query action: {builder._action}")

    # Storage methods
    def storage_upload(
        self, bucket: str, path: str, file_data: bytes, file_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if bucket not in self.storage:
                self.storage[bucket] = {}
                self.storage_meta[bucket] = {}

            self.storage[bucket][path] = bytes(file_data)
            content_type = (file_options or {}).get("content-type", "application/octet-stream")
            self.storage_meta[bucket][path] = {
                "name": path.split("/")[-1],
                "content-type": content_type,
                "size": len(file_data),
            }
            return {"Key": f"{bucket}/{path}"}

    def storage_download(self, bucket: str, path: str) -> bytes:
        with self._lock:
            bucket_store = self.storage.get(bucket, {})
            if path not in bucket_store:
                raise FileNotFoundError(f"File {path} not found in bucket {bucket}")
            return bucket_store[path]

    def storage_remove(self, bucket: str, paths: List[str]) -> List[Dict[str, Any]]:
        with self._lock:
            removed = []
            bucket_store = self.storage.get(bucket, {})
            bucket_meta = self.storage_meta.get(bucket, {})
            for p in paths:
                if p in bucket_store:
                    del bucket_store[p]
                    if p in bucket_meta:
                        del bucket_meta[p]
                    removed.append({"name": p})
            return removed

    def storage_list(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            bucket_meta = self.storage_meta.get(bucket, {})
            results = []
            for path, meta in bucket_meta.items():
                if path.startswith(prefix):
                    results.append({"name": meta.get("name", path), "path": path, **meta})
            return results
