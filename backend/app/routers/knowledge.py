from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status

try:
    from backend.app.schemas.knowledge import (
        KnowledgeDocDeleteResponse,
        KnowledgeDocResponse,
    )
    from backend.app.services.knowledge_service import KnowledgeService
except ImportError:
    from app.schemas.knowledge import (
        KnowledgeDocDeleteResponse,
        KnowledgeDocResponse,
    )
    from app.services.knowledge_service import KnowledgeService

router = APIRouter(tags=["Knowledge Base"])


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService()


@router.post(
    "/knowledge/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=KnowledgeDocResponse,
    summary="Upload a knowledge document",
)
@router.post(
    "/knowledge/upload/",
    status_code=status.HTTP_201_CREATED,
    response_model=KnowledgeDocResponse,
    include_in_schema=False,
)
async def upload_document(
    file: UploadFile = File(...),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocResponse:
    return await service.upload_document(file)


@router.get(
    "/knowledge/documents",
    status_code=status.HTTP_200_OK,
    response_model=List[KnowledgeDocResponse],
    summary="List uploaded knowledge documents",
)
@router.get(
    "/knowledge/documents/",
    status_code=status.HTTP_200_OK,
    response_model=List[KnowledgeDocResponse],
    include_in_schema=False,
)
def list_documents(
    limit: int = 100,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> List[KnowledgeDocResponse]:
    return service.list_documents(limit=limit)


@router.delete(
    "/knowledge/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=KnowledgeDocDeleteResponse,
    summary="Delete a knowledge document",
)
@router.delete(
    "/knowledge/documents/{document_id}/",
    status_code=status.HTTP_200_OK,
    response_model=KnowledgeDocDeleteResponse,
    include_in_schema=False,
)
def delete_document(
    document_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocDeleteResponse:
    return service.delete_document(document_id)
