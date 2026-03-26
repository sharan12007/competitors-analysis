"""
services/competitor_finder.py — Two-step competitor discovery.
Step 1: Tavily search for raw web results.
Step 2: Groq LLM ranks and structures exactly 5 competitors as JSON.
"""

import json
import logging
from typing import List
from services import tavily_client, llm_client
from sse import broadcast

logger = logging.getLogger(__name__)


def _strip_json_fences(text: str) -> str:
    """Remove accidental markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _heuristic_fallback(tavily_results: list, count: int = 5) -> List[dict]:
    """
    Last-resort fallback: build basic competitor list from raw Tavily results.
    Used only if LLM JSON parsing fails twice.
    """
    fallback = []
    for r in tavily_results[:count]:
        fallback.append({
            "name": r.get("title", "Unknown"),
            "url": r.get("url", ""),
            "description": r.get("content", "")[:120],
            "category": "direct",
        })
    # Pad to 5 if needed
    while len(fallback) < 5:
        fallback.append({
            "name": f"Competitor {len(fallback)+1}",
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
    Main entry point.
    Returns a list of exactly 5 competitor dicts:
    {name, url, description, category}
    where category is one of: direct | indirect | emerging
    """

    # ── Step 1: Build search query ────────────────────────────
    description_excerpt = product_description[:120]
    query = f"{product_name} competitors alternatives {description_excerpt}"

    await broadcast(session_id, "status", {"message": "Searching for competitors..."})

    # ── Step 2: Tavily search ─────────────────────────────────
    raw_results = await tavily_client.search(query, max_results=8)

    if not raw_results:
        # Try broader fallback query
        raw_results = await tavily_client.search(
            f"best {product_name} alternatives", max_results=8
        )

    logger.info(f"[{session_id}] Tavily returned {len(raw_results)} results")

    # ── Step 3: Build prompt for LLM ─────────────────────────
    results_text = ""
    for i, r in enumerate(raw_results, 1):
        content_preview = r.get("content", "")[:250]
        results_text += (
            f"{i}. Title: {r.get('title','')}\n"
            f"   URL: {r.get('url','')}\n"
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
4. Return ONLY a raw JSON array with NO surrounding text, NO markdown fences, NO explanation

Each object in the array must have exactly these fields:
- "name": string (company/product name)
- "url": string (actual product homepage, e.g. https://linear.app not a search URL)
- "description": string (one sentence describing what they do)
- "category": string (one of: "direct", "indirect", or "emerging")

Example format (return ONLY this, nothing else):
[
  {{"name": "Asana", "url": "https://asana.com", "description": "Project and task management platform for teams.", "category": "direct"}},
  {{"name": "Monday.com", "url": "https://monday.com", "description": "Work OS for managing projects and workflows.", "category": "direct"}}
]

Return the JSON array now:"""

    # ── Step 4: LLM ranking with retry ───────────────────────
    competitors = None

    for attempt in range(2):
        try:
            raw_response = await llm_client.ask(
                prompt=prompt if attempt == 0 else prompt + "\n\nCRITICAL: Return ONLY the raw JSON array. No text before or after. No ```json fences.",
                max_tokens=1024,
            )
            cleaned = _strip_json_fences(raw_response)
            parsed = json.loads(cleaned)

            # Validate structure
            if isinstance(parsed, list) and len(parsed) >= 1:
                competitors = []
                for item in parsed[:5]:
                    competitors.append({
                        "name": str(item.get("name", "Unknown")),
                        "url": str(item.get("url", "")),
                        "description": str(item.get("description", "")),
                        "category": item.get("category", "direct")
                            if item.get("category") in ("direct", "indirect", "emerging")
                            else "direct",
                    })
                # Pad to exactly 5
                while len(competitors) < 5:
                    competitors.append({
                        "name": f"Competitor {len(competitors)+1}",
                        "url": "",
                        "description": "Could not retrieve details.",
                        "category": "direct",
                    })
                logger.info(f"[{session_id}] LLM returned {len(competitors)} competitors (attempt {attempt+1})")
                break

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[{session_id}] LLM JSON parse failed (attempt {attempt+1}): {e}")
            if attempt == 1:
                logger.warning(f"[{session_id}] Using heuristic fallback")
                competitors = _heuristic_fallback(raw_results)

    if not competitors:
        competitors = _heuristic_fallback(raw_results)

    # ── Step 5: Broadcast result ──────────────────────────────
    await broadcast(session_id, "competitors_found", {"competitors": competitors})
    logger.info(f"[{session_id}] competitors_found broadcast: {[c['name'] for c in competitors]}")

    return competitors