import asyncio
from copy import deepcopy


_sessions: dict[str, dict] = {}
_lock = asyncio.Lock()


async def save_session_data(session_id: str, payload: dict) -> None:
    async with _lock:
        _sessions[session_id] = deepcopy(payload)


async def get_session_data(session_id: str) -> dict | None:
    async with _lock:
        payload = _sessions.get(session_id)
        return deepcopy(payload) if payload is not None else None

