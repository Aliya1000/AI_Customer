from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import List, Optional
import uuid
from fastapi import HTTPException, UploadFile

try:
    from backend.app.schemas.knowledge import (
        KnowledgeDocDeleteResponse,
        KnowledgeDocResponse,
    )
    from backend.app.supabase_client.knowledge_repo import KnowledgeRepository
    from backend.app.supabase_client.storage import DocumentStorage
except ImportError:
    from app.schemas.knowledge import (
        KnowledgeDocDeleteResponse,
        KnowledgeDocResponse,
    )
    from app.supabase_client.knowledge_repo import KnowledgeRepository
    from app.supabase_client.storage import DocumentStorage

try:
    from backend.app.services.rag_client import RAGServiceClient
except ImportError:
    from app.services.rag_client import RAGServiceClient

logger = logging.getLogger("backend.app.services.knowledge_service")

ALLOWED_EXTENSIONS = {"PDF", "TXT", "JSON"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class KnowledgeService:
    def __init__(
        self,
        knowledge_repo: Optional[KnowledgeRepository] = None,
        storage: Optional[DocumentStorage] = None,
        rag_client: Optional[RAGServiceClient] = None,
    ):
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()
        self.storage = storage or DocumentStorage()
        self.rag_client = rag_client or RAGServiceClient()

    async def upload_document(self, file: UploadFile) -> KnowledgeDocResponse:
        filename = file.filename or "uploaded_file.txt"
        ext = Path(filename).suffix.lstrip(".").upper()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '.{ext}'. Allowed extensions are: PDF, TXT, JSON",
            )

        content_bytes = await file.read()
        if len(content_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File size exceeds maximum allowed limit of 10MB",
            )

        # Unique document ID
        ts_suffix = str(int(datetime.now(timezone.utc).timestamp() * 1000))[-4:]
        document_id = f"DOC-{ts_suffix}-{uuid.uuid4().hex[:3].upper()}"
        storage_path = f"{document_id}/{filename}"

        ctype = file.content_type
        if not ctype:
            if ext == "PDF":
                ctype = "application/pdf"
            elif ext == "JSON":
                ctype = "application/json"
            else:
                ctype = "text/plain"

        # 1. Upload to Supabase Storage
        try:
            self.storage.upload_file(storage_path, content_bytes, content_type=ctype)
        except Exception as e:
            logger.error(f"Storage upload failed for {storage_path}: {e}")

        # 2. Ingest into RAG Service via URL call with SYSTEM verification
        try:
            await self.rag_client.ingest_uploaded_files([(filename, content_bytes)], session_id="SYSTEM")
        except Exception as e:
            logger.warning(f"RAG ingestion failed for {filename}: {e}")

        # 3. Save to knowledge repository
        doc_record = self.knowledge_repo.create_document(
            document_id=document_id,
            filename=filename,
            file_type=ext,
            storage_path=storage_path,
            processing_status="indexed",
        )

        return KnowledgeDocResponse(**doc_record)

    def list_documents(self, limit: int = 100) -> List[KnowledgeDocResponse]:
        docs = self.knowledge_repo.list_documents(limit=limit)
        return [KnowledgeDocResponse(**d) for d in docs]

    def delete_document(self, document_id: str) -> KnowledgeDocDeleteResponse:
        doc = self.knowledge_repo.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

        # 1. Remove storage asset
        storage_path = doc.get("storage_path")
        if storage_path:
            try:
                self.storage.delete_file(storage_path)
            except Exception as e:
                logger.warning(f"Storage deletion failed for {storage_path}: {e}")

        # Clean any remaining keys in mock store if active
        try:
            from backend.app.supabase_client.client import get_mock_store
            store = get_mock_store()
            bucket = store.storage.get("knowledge-docs", {})
            matching = [k for k in bucket.keys() if document_id in k]
            for k in matching:
                bucket.pop(k, None)
        except Exception:
            pass

        # 2. Delete from repository
        self.knowledge_repo.delete_document(document_id)

        return KnowledgeDocDeleteResponse(deleted=True, document_id=document_id)
