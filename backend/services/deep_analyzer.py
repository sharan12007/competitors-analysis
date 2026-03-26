"""
services/deep_analyzer.py — Firecrawl scrape + Groq LLM structured extraction.
Competitors #2-5 are analyzed in parallel via asyncio.gather().
Each profile is broadcast the moment it's ready — not batched.
"""

import json
import asyncio
import logging
from typing import List, Optional
from services import firecrawl_client, llm_client
from sse import broadcast

logger = logging.getLogger(__name__)


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _minimal_profile(competitor: dict) -> dict:
    """Fallback profile when both scrape and LLM fail."""
    return {
        "name": competitor.get("name", "Unknown"),
        "url": competitor.get("url", ""),
        "pricing_model": "unknown",
        "pricing_details": "Could not retrieve pricing information.",
        "features": ["Information unavailable"],
        "strengths": ["Well-established product"],
        "weaknesses": ["Could not retrieve detailed information"],
        "market_position": "Established player in the market.",
        "target_audience": "Business teams and professionals.",
    }


async def analyze_one(session_id: str, competitor: dict) -> dict:
    """
    Analyzes a single competitor:
    1. Scrape homepage + pricing page concurrently
    2. Send combined content to Groq for structured extraction
    3. Broadcast competitor_analyzed event immediately
    Returns the structured profile dict.
    """
    name = competitor.get("name", "Unknown")
    url = competitor.get("url", "")

    logger.info(f"[{session_id}] Analyzing competitor: {name} ({url})")

    # ── Step 1: Scrape homepage + pricing in parallel ─────────
    homepage_md, pricing_md = await asyncio.gather(
        firecrawl_client.scrape_url(url),
        firecrawl_client.scrape_pricing(url),
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(homepage_md, Exception):
        homepage_md = ""
    if isinstance(pricing_md, Exception):
        pricing_md = ""

    # Combine and truncate to stay within token budget
    combined = ""
    if homepage_md:
        combined += f"=== HOMEPAGE ===\n{homepage_md[:2000]}\n\n"
    if pricing_md:
        combined += f"=== PRICING PAGE ===\n{pricing_md[:1000]}\n\n"

    if not combined:
        logger.warning(f"[{session_id}] No scraped content for {name} — using LLM knowledge only")
        combined = f"No scraped content available. Use your knowledge about {name} ({url})."

    # ── Step 2: Structured extraction via LLM ────────────────
    prompt = f"""Analyze the competitor "{name}" (URL: {url}) based on this scraped content:

{combined}

Return a JSON object with EXACTLY these fields (no other text, no markdown fences):
{{
  "name": "{name}",
  "url": "{url}",
  "pricing_model": "<one of: free | freemium | paid | enterprise | unknown>",
  "pricing_details": "<string describing pricing tiers and amounts if visible>",
  "features": ["<feature 1>", "<feature 2>", "<up to 6 key features>"],
  "strengths": ["<strength 1>", "<strength 2>", "<up to 3 strengths>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "<up to 3 weaknesses>"],
  "market_position": "<one sentence describing their market position>",
  "target_audience": "<one sentence describing who they target>"
}}

Return ONLY the JSON object:"""

    profile = None
    for attempt in range(2):
        try:
            raw = await llm_client.ask(prompt=prompt, max_tokens=1024)
            cleaned = _strip_json_fences(raw)
            parsed = json.loads(cleaned)

            # Validate required fields exist
            required = ["name", "url", "pricing_model", "pricing_details",
                        "features", "strengths", "weaknesses",
                        "market_position", "target_audience"]
            if all(k in parsed for k in required):
                # Normalise pricing_model
                valid_models = {"free", "freemium", "paid", "enterprise", "unknown"}
                if parsed["pricing_model"] not in valid_models:
                    parsed["pricing_model"] = "unknown"
                # Ensure lists
                for list_field in ["features", "strengths", "weaknesses"]:
                    if not isinstance(parsed[list_field], list):
                        parsed[list_field] = [str(parsed[list_field])]
                profile = parsed
                logger.info(f"[{session_id}] Structured profile ready for {name} (attempt {attempt+1})")
                break
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[{session_id}] Profile parse failed for {name} attempt {attempt+1}: {e}")

    if not profile:
        logger.warning(f"[{session_id}] Using minimal fallback profile for {name}")
        profile = _minimal_profile(competitor)

    # ── Step 3: Broadcast immediately ────────────────────────
    await broadcast(session_id, "competitor_analyzed", profile)
    logger.info(f"[{session_id}] competitor_analyzed broadcast for {name}")

    return profile


async def deep_analyze_all(session_id: str, competitors: List[dict]) -> List[dict]:
    """
    Runs analyze_one() for all competitors concurrently.
    return_exceptions=True ensures one failure doesn't cancel others.
    Returns list of profile dicts (failed ones return minimal profile).
    """
    tasks = [analyze_one(session_id, c) for c in competitors]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    profiles = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[{session_id}] analyze_one failed for competitor {i}: {result}")
            profiles.append(_minimal_profile(competitors[i]))
        else:
            profiles.append(result)

    return profiles