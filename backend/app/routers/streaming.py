import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import StreamingResponse

try:
    from backend.app.services.session_service import SessionService
    from backend.app.services.message_service import MessageService
    from backend.app.llm.fallback_service import FallbackLLMService
except ImportError:
    from app.services.session_service import SessionService
    from app.services.message_service import MessageService
    from app.llm.fallback_service import FallbackLLMService

logger = logging.getLogger("backend.app.routers.streaming")
router = APIRouter(tags=["Real-time Streaming & WebSockets"])


# Connection manager for active WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        logger.info(f"Client connected to session {session_id} WebSocket")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"Client disconnected from session {session_id} WebSocket")

    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            dead_sockets = set()
            payload = json.dumps(message)
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    dead_sockets.add(connection)
            for dead in dead_sockets:
                self.active_connections[session_id].discard(dead)


manager = ConnectionManager()


@router.get(
    "/sessions/{session_id}/stream",
    summary="Server-Sent Events (SSE) token stream for suggested replies and simulator",
)
async def stream_session_response(session_id: str):
    """
    Stream word-by-word token generation via SSE for real-time response generation
    and simulation typing indicators.
    """
    session_service = SessionService()
    try:
        session = await session_service.get_session(session_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        # 1. Typing indicator start
        yield f"event: typing\ndata: {json.dumps({'status': 'typing', 'sender': 'customer'})}\n\n"
        await asyncio.sleep(0.3)

        # 2. Extract suggested response text to stream
        suggested = ""
        if session.agent_outputs and session.agent_outputs.response_generation:
            suggested = session.agent_outputs.response_generation.suggested_response
        if not suggested:
            suggested = "I understand your concern and I am here to help resolve your issue."

        # 3. Tokenize by words and stream with slight jitter
        words = suggested.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"token": token, "index": i, "is_final": i == len(words) - 1})
            yield f"event: token\ndata: {payload}\n\n"
            await asyncio.sleep(0.04)

        # 4. Typing indicator complete
        yield f"event: typing\ndata: {json.dumps({'status': 'idle', 'sender': 'customer'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/sessions/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    Bi-directional WebSocket for real-time typing indicators, messaging,
    and supervisor coaching synchronization.
    """
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                event = {"type": "raw", "data": data}

            event_type = event.get("type", "message")
            if event_type == "typing":
                # Broadcast typing status to peers (e.g. employee or observer)
                await manager.broadcast(
                    session_id,
                    {
                        "type": "typing_indicator",
                        "sender": event.get("sender", "customer"),
                        "is_typing": event.get("is_typing", True),
                    },
                )
            elif event_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                # Echo / broadcast session event
                await manager.broadcast(
                    session_id,
                    {
                        "type": "session_event",
                        "session_id": session_id,
                        "payload": event,
                    },
                )
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
