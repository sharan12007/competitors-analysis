"""
services/firecrawl_client.py — Async Firecrawl REST API wrapper via httpx.
No official async SDK exists — we call the REST API directly.
Single module-level AsyncClient with API key in default headers.
"""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

# Single async client — never recreated per request
_client = httpx.AsyncClient(
    headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}"},
    timeout=20.0,
)


async def scrape_url(url: str) -> str:
    """
    Scrapes a URL and returns clean markdown content.
    Returns empty string on any HTTP error, timeout, or quota issue.
    Never raises — caller always gets a string back.
    """
    try:
        response = await _client.post(
            f"{FIRECRAWL_BASE}/scrape",
            json={"url": url, "formats": ["markdown"]},
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data", {}).get("markdown", "")
        # 402 = quota exceeded, 429 = rate limit — both handled silently
        logger.warning(f"Firecrawl scrape_url {url} returned {response.status_code}")
        return ""
    except httpx.TimeoutException:
        logger.warning(f"Firecrawl timeout scraping {url}")
        return ""
    except Exception as e:
        logger.error(f"Firecrawl scrape_url error for {url}: {e}")
        return ""


async def scrape_pricing(base_url: str) -> str:
    """
    Tries to scrape /pricing then /plans pages.
    Returns first non-empty result or empty string.
    Never raises.
    """
    base = base_url.rstrip("/")
    for path in ["/pricing", "/plans"]:
        content = await scrape_url(f"{base}{path}")
        if content:
            return content
    return ""