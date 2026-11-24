from typing import Literal, Optional
from pydantic import BaseModel, Field

ProcessingStatus = Literal["pending", "processing", "indexed", "failed"]


class KnowledgeDocCreate(BaseModel):
    filename: str = Field(min_length=1)
    file_type: str = Field(min_length=1)
    storage_path: Optional[str] = None
    processing_status: ProcessingStatus = "pending"


class KnowledgeDocResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    upload_time: str
    processing_status: str
    storage_path: Optional[str] = None


class KnowledgeDocDeleteResponse(BaseModel):
    deleted: bool = True
    document_id: str
