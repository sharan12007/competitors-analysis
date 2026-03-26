"""
services/github_search.py — OSS alternative discovery via PyGithub.
Step 1: Groq extracts 3 keyword phrases from product context.
Step 2: PyGithub searches each phrase, deduplicates, returns top 8 by stars.
"""

import json
import asyncio
import logging
from typing import List
from github import Github, GithubException
from services import llm_client
from sse import broadcast
from config import settings

logger = logging.getLogger(__name__)

# Single Github client with token for higher rate limit
_github = Github(settings.GITHUB_TOKEN)


async def _extract_keywords(product_name: str, product_description: str) -> List[str]:
    """Use LLM to extract 3 concise technical keyword phrases for GitHub search."""
    prompt = f"""Extract exactly 3 short technical keyword phrases for searching GitHub repositories
related to this product:

Product: {product_name}
Description: {product_description}

Rules:
- Each phrase should be 1-3 words
- Focus on the core technical function (e.g. "issue tracker", "kanban board", "project management")
- Return ONLY a raw JSON array of 3 strings, nothing else

Example: ["issue tracker", "project management", "team collaboration"]

Return the JSON array now:"""

    try:
        raw = await llm_client.ask(prompt=prompt, max_tokens=100)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        keywords = json.loads(cleaned.strip())
        if isinstance(keywords, list) and len(keywords) >= 1:
            return [str(k) for k in keywords[:3]]
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")

    # Fallback: use product name directly
    return [product_name]


async def find_github_alternatives(
    session_id: str,
    product_name: str,
    product_description: str,
) -> List[dict]:
    """
    Main entry point.
    Returns list of up to 8 OSS repo dicts:
    {name, url, stars, description, language, last_updated}
    """
    await broadcast(session_id, "status", {"message": "Searching GitHub for OSS alternatives..."})

    # ── Step 1: Extract search keywords ──────────────────────
    keywords = await _extract_keywords(product_name, product_description)
    logger.info(f"[{session_id}] GitHub search keywords: {keywords}")

    # ── Step 2: Search GitHub for each keyword ────────────────
    loop = asyncio.get_event_loop()
    all_repos = {}  # keyed by full_name to deduplicate

    for keyword in keywords:
        try:
            def _search(kw=keyword):
                results = _github.search_repositories(
                    query=kw,
                    sort="stars",
                    order="desc",
                )
                repos = []
                for repo in results[:5]:
                    repos.append({
                        "full_name": repo.full_name,
                        "name": repo.full_name,
                        "url": repo.html_url,
                        "stars": repo.stargazers_count,
                        "description": repo.description or "",
                        "language": repo.language or "Unknown",
                        "last_updated": str(repo.updated_at)[:10],
                    })
                return repos

            repos = await loop.run_in_executor(None, _search)

            for repo in repos:
                full_name = repo["full_name"]
                if full_name not in all_repos:
                    all_repos[full_name] = repo

            logger.info(f"[{session_id}] GitHub search '{keyword}' returned {len(repos)} repos")

        except GithubException as e:
            logger.warning(f"[{session_id}] GitHub search failed for '{keyword}': {e}")
        except Exception as e:
            logger.error(f"[{session_id}] GitHub unexpected error for '{keyword}': {e}")

    # ── Step 3: Deduplicate + sort by stars + take top 8 ─────
    sorted_repos = sorted(
        all_repos.values(),
        key=lambda r: r.get("stars", 0),
        reverse=True,
    )[:8]

    # Remove internal full_name field before broadcasting
    for repo in sorted_repos:
        repo.pop("full_name", None)

    if not sorted_repos:
        logger.warning(f"[{session_id}] No GitHub results found")

    # ── Step 4: Broadcast ─────────────────────────────────────
    await broadcast(session_id, "github_results", {"repos": sorted_repos})
    logger.info(f"[{session_id}] github_results broadcast: {len(sorted_repos)} repos")

    return sorted_repos