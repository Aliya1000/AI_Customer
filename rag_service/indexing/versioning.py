"""
Vector Chunk Auto-Expiry and Knowledge Document Versioning for Pinecone.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any


class ChunkVersioningManager:
    def __init__(self):
        self._doc_versions: Dict[str, int] = {}

    def get_next_version(self, filename: str) -> int:
        v = self._doc_versions.get(filename, 0) + 1
        self._doc_versions[filename] = v
        return v

    def filter_active_chunks(self, chunks: List[Dict[str, Any]], max_age_days: int = 90) -> List[Dict[str, Any]]:
        """Filter out expired chunks older than max_age_days."""
        now = datetime.now(timezone.utc)
        active = []
        for c in chunks:
            ts_str = c.get("metadata", {}).get("indexed_at")
            if not ts_str:
                active.append(c)
                continue
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if (now - dt).days <= max_age_days:
                    active.append(c)
            except Exception:
                active.append(c)
        return active
