from typing import List
from fastapi import APIRouter, Depends, status

try:
    from backend.app.schemas.message import MessageCreate, MessageResponse, SendMessageResponse
    from backend.app.services.message_service import MessageService
except ImportError:
    from app.schemas.message import MessageCreate, MessageResponse, SendMessageResponse
    from app.services.message_service import MessageService

router = APIRouter(tags=["Messages"])


def get_message_service() -> MessageService:
    return MessageService()


@router.post(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=SendMessageResponse,
    summary="Send a message in a session",
)
@router.post(
    "/sessions/{session_id}/messages/",
    status_code=status.HTTP_201_CREATED,
    response_model=SendMessageResponse,
    include_in_schema=False,
)
async def send_message(
    session_id: str,
    payload: MessageCreate,
    service: MessageService = Depends(get_message_service),
) -> SendMessageResponse:
    return await service.send_message(session_id, payload)


@router.get(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=List[MessageResponse],
    summary="List conversation messages for a session",
)
@router.get(
    "/sessions/{session_id}/messages/",
    status_code=status.HTTP_200_OK,
    response_model=List[MessageResponse],
    include_in_schema=False,
)
def list_messages(
    session_id: str,
    service: MessageService = Depends(get_message_service),
) -> List[MessageResponse]:
    return service.get_messages(session_id)
