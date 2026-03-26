"""
Phase 6 — Worker (Complete Pipeline)
Orchestrates the full analysis pipeline:
  1. find_competitors (5 competitors)
  2. asyncio.gather:
       - browser_agent (competitor #1)   ← Track 1
       - deep_analyze_all (#2–5)         ← Track 2
       - github_search                   ← Track 2
  3. synthesize (streams chain-of-thought)
  4. generate_exports (PDF + JSON)
  5. export_ready + complete events

CRITICAL: browser_result from run_browser_analysis() is assembled into
all_competitor_data[0] so synthesis and export both include browser findings.
"""

import asyncio
import logging
import uuid

from sse import broadcast
from services.competitor_finder import find_competitors
from services.browser_agent import run_browser_analysis
from services.deep_analyzer import deep_analyze_all
from services.github_search import find_github_alternatives
from services.synthesis_engine import synthesize
from services.export_generator import generate_exports
from session_store import save_session_data

logger = logging.getLogger(__name__)

# Module-level queue — the single pipeline of analysis jobs
analysis_queue: asyncio.Queue = asyncio.Queue()


async def start_worker():
    """Forever-loop consuming analysis_queue. Launch once at startup."""
    logger.info("[worker] Started — waiting for jobs")
    while True:
        job = await analysis_queue.get()
        # Fire as background task so the loop immediately accepts the next job
        asyncio.create_task(run_analysis(job))


async def run_analysis(job: dict):
    """Full analysis pipeline for one job."""
    session_id = job["session_id"]
    product_name = job.get("product_name", "")
    product_description = job.get("product_description", "")

    logger.info(f"[worker] Starting analysis — session={session_id}, product={product_name}")

    # Small delay so the SSE client can connect (race condition prevention)
    # This is backed up by the event replay buffer in sse.py but doesn't hurt
    await asyncio.sleep(0.5)

    try:
        # ── Step 1: Broadcast start ──────────────────────────────────────────
        await broadcast(session_id, "status", {"message": "Analysis started"})

        # ── Step 2: Find competitors ─────────────────────────────────────────
        competitors_list = await find_competitors(session_id, product_name, product_description)
        await broadcast(session_id, "competitors_found", {"competitors": competitors_list})

        if not competitors_list:
            logger.error(f"[worker] No competitors found for session {session_id}")
            await broadcast(session_id, "error", {"message": "Could not find any competitors. Please try a different product description."})
            return

        # Ensure we have at least 1 competitor for browser and prepare slices
        browser_competitor = competitors_list[0]
        deep_competitors = competitors_list[1:] if len(competitors_list) > 1 else []

        # ── Step 3: Parallel execution ───────────────────────────────────────
        await broadcast(session_id, "status", {"message": "Running live browser analysis + deep scraping in parallel..."})

        gather_results = await asyncio.gather(
            run_browser_analysis(session_id, browser_competitor),
            deep_analyze_all(session_id, deep_competitors),
            find_github_alternatives(session_id, product_name, product_description),
            return_exceptions=True,
        )

        # ── Step 4: Collect results safely ──────────────────────────────────
        browser_result = gather_results[0]
        deep_results = gather_results[1]
        github_result = gather_results[2]  # already broadcast internally

        # Handle browser_result exception
        if isinstance(browser_result, Exception):
            logger.error(f"[worker] Browser agent failed: {browser_result}")
            browser_result = {
                "name": browser_competitor.get("name", ""),
                "url": browser_competitor.get("url", ""),
                "browser_findings": f"Browser analysis failed: {str(browser_result)}",
                "steps_taken": 0,
                "is_browser_analyzed": False,
                "pricing_model": "unknown",
                "pricing_details": "",
                "features": [],
                "strengths": [],
                "weaknesses": [],
                "market_position": "Browser analysis unavailable",
                "target_audience": "",
            }

        # Handle deep_results exception or unexpected type
        if isinstance(deep_results, Exception):
            logger.error(f"[worker] Deep analysis failed: {deep_results}")
            deep_results = []

        if not isinstance(deep_results, list):
            deep_results = []

        # Patch any individual deep_result exceptions
        clean_deep_results = []
        for i, r in enumerate(deep_results):
            if isinstance(r, Exception) or r is None:
                logger.warning(f"[worker] Deep result {i} failed: {r}")
                # Fallback using the competitor metadata we already have
                if i + 1 < len(competitors_list):
                    fallback_comp = competitors_list[i + 1]
                else:
                    fallback_comp = {}
                clean_deep_results.append({
                    "name": fallback_comp.get("name", f"Competitor {i + 2}"),
                    "url": fallback_comp.get("url", ""),
                    "browser_findings": "",
                    "is_browser_analyzed": False,
                    "pricing_model": "unknown",
                    "pricing_details": "",
                    "features": [],
                    "strengths": [],
                    "weaknesses": [],
                    "market_position": "Data unavailable",
                    "target_audience": "",
                })
            else:
                clean_deep_results.append(r)

        # ── Step 5: Assemble all_competitor_data ─────────────────────────────
        # CRITICAL: browser_result MUST be index 0 — synthesis reads it as competitor #1
        all_competitor_data = [browser_result] + clean_deep_results

        logger.info(
            f"[worker] Assembled {len(all_competitor_data)} competitors: "
            f"#1 browser={'yes' if browser_result.get('is_browser_analyzed') else 'no (fallback)'}, "
            f"#2-5 deep={len(clean_deep_results)}"
        )

        # Log browser findings to confirm they're present
        browser_findings = browser_result.get("browser_findings", "")
        logger.info(f"[worker] Browser findings length: {len(browser_findings)} chars")
        if browser_findings:
            logger.info(f"[worker] Browser findings preview: {browser_findings[:200]}")

        # ── Step 6: Synthesis ─────────────────────────────────────────────────
        await broadcast(session_id, "status", {"message": "Synthesizing competitive intelligence..."})

        synthesis_result = await synthesize(session_id, job, all_competitor_data)

        # ── Step 7: Generate exports ──────────────────────────────────────────
        await broadcast(session_id, "status", {"message": "Generating PDF and JSON reports..."})

        export_paths = await generate_exports(session_id, job, all_competitor_data, synthesis_result)

        pdf_path = export_paths.get("pdf_path")
        json_path = export_paths.get("json_path")

        await save_session_data(
            session_id,
            {
                "job": job,
                "competitors": all_competitor_data,
                "synthesis": synthesis_result,
                "github_repos": github_result if isinstance(github_result, list) else [],
                "exports": export_paths,
            },
        )

        if pdf_path or json_path:
            await broadcast(session_id, "export_ready", {
                "pdf_url": f"/export/{session_id}/pdf" if pdf_path else None,
                "json_url": f"/export/{session_id}/json" if json_path else None,
            })
            logger.info(f"[worker] Exports ready — PDF: {pdf_path}, JSON: {json_path}")
        else:
            logger.warning(f"[worker] Export generation failed for session {session_id}")

        # ── Step 8: Complete ──────────────────────────────────────────────────
        await broadcast(session_id, "complete", {"session_id": session_id})
        logger.info(f"[worker] Pipeline complete — session={session_id}")

    except Exception as e:
        logger.error(f"[worker] Unhandled error in run_analysis: {e}", exc_info=True)
        await broadcast(session_id, "error", {"message": f"Analysis failed: {str(e)}"})
