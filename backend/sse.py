"""
sse.py — Central SSE broadcaster with event replay buffer.

Architecture:
- _subscribers: active queue connections per session
- _event_buffer: stores ALL events per session so late-connecting
  clients (Postman, slow browsers) get full history on connect.

This makes client connection timing completely irrelevant.
"""

import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator

# Active subscriber queues: session_id -> list[asyncio.Queue]
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

# Event replay buffer: session_id -> list[str] (serialised JSON strings)
# Every broadcast is appended here so late-connecting clients catch up instantly
_event_buffer: dict[str, list[str]] = defaultdict(list)


def subscribe(session_id: str) -> asyncio.Queue:
    """
    Called when SSE client connects.
    Creates a queue, pre-fills it with all buffered events so the
    client instantly receives everything that already happened.
    """
    q: asyncio.Queue = asyncio.Queue()

    # Replay buffered events into the new queue immediately
    for buffered_event in _event_buffer.get(session_id, []):
        q.put_nowait(buffered_event)

    _subscribers[session_id].append(q)
    return q


def unsubscribe(session_id: str, queue: asyncio.Queue) -> None:
    """Called in finally block when SSE client disconnects."""
    try:
        _subscribers[session_id].remove(queue)
    except (ValueError, KeyError):
        pass


async def broadcast(session_id: str, event_type: str, data: dict) -> None:
    """
    Serialises and pushes event to:
    1. The replay buffer (so future/reconnecting clients get it)
    2. All currently connected subscriber queues

    MUST be awaited everywhere it is called.
    """
    payload = json.dumps({"type": event_type, "data": data})

    # Always buffer — even if no subscribers connected yet
    _event_buffer[session_id].append(payload)

    # Push to all currently connected clients
    for q in _subscribers.get(session_id, []):
        await q.put(payload)


async def event_generator(
    session_id: str, queue: asyncio.Queue
) -> AsyncGenerator[str, None]:
    """
    Async generator for the SSE StreamingResponse.
    Yields buffered + live events. Sends heartbeat every 30s.
    Stops on 'complete' or 'error'.
    """
    while True:
        try:
            message: str = await asyncio.wait_for(queue.get(), timeout=30.0)
        except asyncio.TimeoutError:
            yield 'data: {"type": "heartbeat", "data": {}}\n\n'
            continue

        yield f"data: {message}\n\n"

        try:
            parsed = json.loads(message)
            if parsed.get("type") in ("complete", "error"):
                break
        except json.JSONDecodeError:
            pass