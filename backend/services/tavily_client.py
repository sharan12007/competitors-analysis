"""
services/tavily_client.py — Async wrapper around the Tavily Python SDK.
Tavily SDK is synchronous — all calls are wrapped in run_in_executor
so they never block the FastAPI event loop.
"""

import asyncio
import logging
from typing import List
from tavily import TavilyClient
from config import settings

logger = logging.getLogger(__name__)

# Single client instance — never re-instantiated per request
_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


async def search(query: str, max_results: int = 8) -> List[dict]:
    """
    Async Tavily web search.
    Returns list of {title, url, content} dicts.
    Returns empty list on any exception — never raises.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: _client.search(
                query,
                max_results=max_results,
                include_answer=True,
            ),
        )
        return result.get("results", [])
    except Exception as e:
        logger.error(f"Tavily search failed for query '{query}': {e}")
        return []


async def scrape(url: str) -> str:
    """
    Async Tavily URL extraction.
    Returns raw content string of the first result.
    Returns empty string on any exception — never raises.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: _client.extract(urls=[url]),
        )
        results = result.get("results", [])
        if results:
            return results[0].get("raw_content", "")
        return ""
    except Exception as e:
        logger.error(f"Tavily scrape failed for url '{url}': {e}")
        return ""