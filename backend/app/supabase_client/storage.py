from typing import Any, Dict, List, Optional
from backend.app.config import get_settings
from backend.app.supabase_client.client import get_supabase_client


class DocumentStorage:
    """
    Storage service targeting the Supabase Storage bucket for knowledge documents.
    """

    def __init__(self, client: Optional[Any] = None, bucket_name: Optional[str] = None):
        self.client = client or get_supabase_client()
        self.bucket_name = bucket_name or get_settings().supabase_storage_bucket

    def upload_file(
        self,
        storage_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload raw file bytes to the bucket at the given storage path.
        """
        self.client.storage.from_(self.bucket_name).upload(
            storage_path,
            data,
            {"content-type": content_type},
        )
        return storage_path

    def download_file(self, storage_path: str) -> bytes:
        """
        Retrieve raw file bytes from the bucket. Raises FileNotFoundError if absent.
        """
        data = self.client.storage.from_(self.bucket_name).download(storage_path)
        if data is None:
            raise FileNotFoundError(
                f"File '{storage_path}' not found in bucket '{self.bucket_name}'"
            )
        return data

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from the bucket.
        """
        self.client.storage.from_(self.bucket_name).remove([storage_path])
        return True

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List files in the bucket matching the optional prefix.
        """
        return self.client.storage.from_(self.bucket_name).list(prefix)

    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Generate a signed/presigned URL for secure downloading and viewing of knowledge base attachments.
        """
        res = self.client.storage.from_(self.bucket_name).create_signed_url(storage_path, expires_in)
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl") or str(res)
        return str(res)
