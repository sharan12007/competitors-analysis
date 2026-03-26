"""
routers/stream.py — GET /stream/{session_id}
SSE endpoint. Client connects here and receives all real-time events
for the given session until a 'complete' or 'error' event is received.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sse import subscribe, unsubscribe, event_generator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream/{session_id}")
async def stream(session_id: str) -> StreamingResponse:
    """
    Returns a Server-Sent Events stream for the given session.
    The client should keep this connection open until it receives
    a 'complete' or 'error' event, after which it will auto-close.
    """
    async def event_stream():
        queue = subscribe(session_id)
        logger.info(f"SSE client connected: session_id={session_id}")
        try:
            async for chunk in event_generator(session_id, queue):
                yield chunk
        finally:
            unsubscribe(session_id, queue)
            logger.info(f"SSE client disconnected: session_id={session_id}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",      # Prevents Nginx from buffering SSE
            "Connection": "keep-alive",
        },
    )