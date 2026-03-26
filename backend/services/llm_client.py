"""
LLM Client — Groq backend
ask()    → single-shot call with 1 retry
stream() → async generator yielding text chunks
"""

import asyncio
import logging

from groq import AsyncGroq, Groq

from config import settings

logger = logging.getLogger(__name__)

MODEL = settings.GROQ_MODEL

# Singletons — instantiated once at module load
_sync_client = Groq(api_key=settings.GROQ_API_KEY)
_async_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

DEFAULT_SYSTEM = (
    "You are an expert competitive intelligence analyst. "
    "Provide precise, evidence-backed analysis. "
    "When returning JSON, return ONLY raw JSON with no markdown fences."
)


async def ask(
    prompt: str,
    max_tokens: int = 1500,
    system_prompt: str = DEFAULT_SYSTEM,
) -> str:
    """Single-shot async LLM call with one retry."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(2):
        try:
            resp = await _async_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"[llm_client] ask() attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(1)
            else:
                raise


async def stream(
    prompt: str,
    max_tokens: int = 3000,
    system_prompt: str = DEFAULT_SYSTEM,
):
    """
    Async generator that yields text chunks as they stream from Groq.
    On error, yields a single error marker and exits — never raises.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        stream_resp = await _async_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
            stream=True,
        )
        async for chunk in stream_resp:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    except Exception as e:
        logger.error(f"[llm_client] stream() failed: {e}", exc_info=True)
        yield f"ERROR: LLM streaming failed — {str(e)}"
