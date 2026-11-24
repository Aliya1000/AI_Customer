from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid
from backend.app.schemas.knowledge import KnowledgeDocCreate
from backend.app.supabase_client.client import get_supabase_client


class KnowledgeRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def create_document(
        self,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        file_type: Optional[str] = None,
        storage_path: Optional[str] = None,
        processing_status: str = "pending",
        upload_time: Optional[str] = None,
        data: Optional[Union[Dict[str, Any], KnowledgeDocCreate]] = None,
    ) -> Dict[str, Any]:
        if data is not None:
            if isinstance(data, KnowledgeDocCreate):
                rec = data.model_dump(exclude_none=True)
            else:
                rec = dict(data)
            document_id = document_id or rec.get("document_id")
            filename = filename or rec.get("filename")
            file_type = file_type or rec.get("file_type")
            storage_path = storage_path or rec.get("storage_path")
            processing_status = rec.get("processing_status", processing_status)
            upload_time = upload_time or rec.get("upload_time")

        if not document_id:
            ts_suffix = str(int(datetime.now(timezone.utc).timestamp() * 1000))[-4:]
            document_id = f"DOC-{ts_suffix}-{uuid.uuid4().hex[:3].upper()}"

        if not upload_time:
            upload_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if not storage_path and filename:
            storage_path = f"{document_id}/{filename}"

        record = {
            "document_id": document_id,
            "filename": filename or "unknown_file",
            "file_type": file_type or "TXT",
            "storage_path": storage_path,
            "processing_status": processing_status,
            "upload_time": upload_time,
        }

        res = self.client.table("knowledge_documents").insert(record).execute()
        return res.data[0] if res.data else record

    def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        res = (
            self.client.table("knowledge_documents")
            .select("*")
            .order("upload_time", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("knowledge_documents")
            .select("*")
            .eq("document_id", document_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def update_document_status(
        self, document_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("knowledge_documents")
            .update({"processing_status": status})
            .eq("document_id", document_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def delete_document(self, document_id: str) -> bool:
        res = (
            self.client.table("knowledge_documents")
            .delete()
            .eq("document_id", document_id)
            .execute()
        )
        return bool(res.data)


knowledge_repo = KnowledgeRepository()
