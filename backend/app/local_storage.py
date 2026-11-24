
import os
from pathlib import Path


class DocumentStorage:
    def __init__(self):
        default_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge_documents"
        self.storage_dir = Path(
            os.getenv("KNOWLEDGE_STORAGE_DIR", str(default_dir))
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, storage_path: str) -> Path:
        file_path = (self.storage_dir / storage_path).resolve()

        # Prevent paths from escaping the storage directory.
        if not file_path.is_relative_to(self.storage_dir.resolve()):
            raise ValueError("Invalid storage path")

        return file_path

    def upload_file(self, storage_path: str, data: bytes, content_type=None):
        file_path = self._get_file_path(storage_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return str(file_path)

    def delete_file(self, storage_path: str):
        file_path = self._get_file_path(storage_path)

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True

        return False
