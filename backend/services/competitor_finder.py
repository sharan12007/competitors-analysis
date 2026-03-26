"""
services/competitor_finder.py - Two-step competitor discovery.
Step 1: Tavily search for raw web results.
Step 2: Groq LLM ranks and structures exactly 5 competitors as JSON.
"""

import json
import logging
from typing import List
from urllib.parse import urlparse

from services import llm_client, tavily_client
from sse import broadcast

logger = logging.getLogger(__name__)

BAD_URL_MARKERS = (
    "/alternatives",
    "/alternative",
    "/compare",
    "/comparison",
    "/vs",
    "/blog",
    "/reviews",
    "/review",
    "/best-",
    "/top-",
    "/directory",
    "/list",
)

BAD_HOST_MARKERS = (
    "g2.com",
    "capterra.com",
    "getapp.com",
    "saashub.com",
    "alternative.to",
    "alternativeto.net",
    "toolfinder.co",
    "efficient.app",
)


def _strip_json_fences(text: str) -> str:
    """Remove accidental markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _is_bad_competitor_url(url: str) -> bool:
    if not url:
        return True

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    if any(marker in host for marker in BAD_HOST_MARKERS):
        return True

    if any(marker in path for marker in BAD_URL_MARKERS):
        return True

    return False


def _filter_search_results(results: list) -> list:
    filtered = []
    for result in results:
        url = result.get("url", "")
        title = (result.get("title", "") or "").lower()
        content = (result.get("content", "") or "").lower()

        if _is_bad_competitor_url(url):
            continue

        if any(marker in title for marker in ("alternatives", "compare", "comparison", "review", "best ")):
            continue

        if any(marker in content[:220] for marker in ("alternatives to", "best alternatives", "compare ")):
            continue

        filtered.append(result)

    return filtered


def _heuristic_fallback(tavily_results: list, count: int = 5) -> List[dict]:
    """
    Last-resort fallback: build basic competitor list from raw Tavily results.
    Used only if LLM JSON parsing fails twice.
    """
    fallback = []
    for result in tavily_results:
        if _is_bad_competitor_url(result.get("url", "")):
            continue

        fallback.append({
            "name": result.get("title", "Unknown"),
            "url": result.get("url", ""),
            "description": result.get("content", "")[:120],
            "category": "direct",
        })

        if len(fallback) >= count:
            break

    while len(fallback) < 5:
        fallback.append({
            "name": f"Competitor {len(fallback) + 1}",
            "url": "",
            "description": "Could not retrieve details.",
            "category": "direct",
        })

    return fallback[:5]


async def find_competitors(
    session_id: str,
    product_name: str,
    product_description: str,
) -> List[dict]:
    """
    Returns a list of exactly 5 competitor dicts:
    {name, url, description, category}
    where category is one of: direct | indirect | emerging
    """
    description_excerpt = product_description[:120]
    query = f"{product_name} competitors alternatives {description_excerpt}"

    await broadcast(session_id, "status", {"message": "Searching for competitors..."})

    raw_results = await tavily_client.search(query, max_results=8)

    if not raw_results:
        raw_results = await tavily_client.search(f"best {product_name} alternatives", max_results=8)

    logger.info(f"[{session_id}] Tavily returned {len(raw_results)} results")

    filtered_results = _filter_search_results(raw_results)
    if filtered_results:
        raw_results = filtered_results
        logger.info(f"[{session_id}] Filtered to {len(raw_results)} candidate product homepages")

    results_text = ""
    for index, result in enumerate(raw_results, 1):
        content_preview = result.get("content", "")[:250]
        results_text += (
            f"{index}. Title: {result.get('title', '')}\n"
            f"   URL: {result.get('url', '')}\n"
            f"   Content: {content_preview}\n\n"
        )

    prompt = f"""You are analyzing competitors for a product called "{product_name}".

Product description: {product_description}

Here are web search results that may contain competitor information:

{results_text}

Your task:
1. Identify the 5 most relevant DIRECT competitors or alternatives to "{product_name}"
2. Exclude "{product_name}" itself from the list
3. Exclude generic directories, review sites (G2, Capterra, etc.), and blog posts
4. Exclude alternatives pages, compare pages, listicles, and article URLs such as "/alternatives"
5. Every URL must be the official product homepage or official product page, not an article about that product
6. Return ONLY a raw JSON array with NO surrounding text, NO markdown fences, NO explanation

Each object in the array must have exactly these fields:
- "name": string
- "url": string
- "description": string
- "category": string (one of: "direct", "indirect", or "emerging")

Example format:
[
  {{"name": "Asana", "url": "https://asana.com", "description": "Project and task management platform for teams.", "category": "direct"}},
  {{"name": "Monday.com", "url": "https://monday.com", "description": "Work OS for managing projects and workflows.", "category": "direct"}}
]

Return the JSON array now:"""

    competitors = None

    for attempt in range(2):
        try:
            retry_suffix = ""
            if attempt == 1:
                retry_suffix = (
                    "\n\nCRITICAL: Return ONLY the raw JSON array. "
                    "Do not include alternatives pages, compare pages, directories, or review URLs."
                )

            raw_response = await llm_client.ask(
                prompt=prompt + retry_suffix,
                max_tokens=1024,
            )
            cleaned = _strip_json_fences(raw_response)
            parsed = json.loads(cleaned)

            if isinstance(parsed, list) and len(parsed) >= 1:
                competitors = []
                for item in parsed:
                    candidate_url = str(item.get("url", ""))
                    if _is_bad_competitor_url(candidate_url):
                        continue

                    competitors.append({
                        "name": str(item.get("name", "Unknown")),
                        "url": candidate_url,
                        "description": str(item.get("description", "")),
                        "category": (
                            item.get("category", "direct")
                            if item.get("category") in ("direct", "indirect", "emerging")
                            else "direct"
                        ),
                    })

                    if len(competitors) >= 5:
                        break

                while len(competitors) < 5:
                    competitors.append({
                        "name": f"Competitor {len(competitors) + 1}",
                        "url": "",
                        "description": "Could not retrieve details.",
                        "category": "direct",
                    })

                logger.info(f"[{session_id}] LLM returned {len(competitors)} competitors (attempt {attempt + 1})")
                break

        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(f"[{session_id}] LLM JSON parse failed (attempt {attempt + 1}): {exc}")
            if attempt == 1:
                logger.warning(f"[{session_id}] Using heuristic fallback")
                competitors = _heuristic_fallback(raw_results)

    if not competitors:
        competitors = _heuristic_fallback(raw_results)

    await broadcast(session_id, "competitors_found", {"competitors": competitors})
    logger.info(f"[{session_id}] competitors_found broadcast: {[c['name'] for c in competitors]}")

    return competitors
