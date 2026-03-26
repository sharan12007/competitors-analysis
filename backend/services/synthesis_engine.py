"""
Phase 6 — Synthesis Engine
Reads ALL competitor data (including browser_agent findings for competitor #1)
and streams a full chain-of-thought strategic analysis via Groq.
"""

import json
import logging
import re

from sse import broadcast
from services.llm_client import stream as llm_stream, ask as llm_ask

logger = logging.getLogger(__name__)


def _truncate(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def _build_competitor_block(c: dict, index: int) -> str:
    """Format one competitor entry for the synthesis prompt."""
    name = c.get("name", f"Competitor {index + 1}")
    url = c.get("url", "")
    is_browser = c.get("is_browser_analyzed", False)
    source_label = "Browser-analyzed (live site visit)" if is_browser else "Firecrawl-scraped"

    lines = [f"### Competitor {index + 1}: {name} ({url}) [{source_label}]"]

    # Browser findings (competitor #1)
    browser_findings = c.get("browser_findings", "")
    if browser_findings and browser_findings not in ("", "Browser analysis unavailable"):
        lines.append(f"Browser Findings:\n{_truncate(browser_findings, 600)}")

    # Structured fields (competitors #2–5 from deep_analyzer)
    pricing_model = c.get("pricing_model", "unknown")
    pricing_details = _truncate(c.get("pricing_details", ""), 200)
    market_position = c.get("market_position", "")
    target_audience = c.get("target_audience", "")

    features = c.get("features") or []
    strengths = c.get("strengths") or []
    weaknesses = c.get("weaknesses") or []

    if pricing_model and pricing_model != "unknown":
        lines.append(f"Pricing: {pricing_model} — {pricing_details}")
    if market_position:
        lines.append(f"Market Position: {market_position}")
    if target_audience:
        lines.append(f"Target Audience: {target_audience}")
    if features:
        lines.append(f"Features: {', '.join(features[:6])}")
    if strengths:
        lines.append(f"Strengths: {', '.join(strengths[:3])}")
    if weaknesses:
        lines.append(f"Weaknesses: {', '.join(weaknesses[:3])}")

    return "\n".join(lines)


def _extract_section(text: str, header: str, next_header: str = None) -> str:
    """Extract text between two section headers."""
    pattern = re.escape(header)
    if next_header:
        match = re.search(pattern + r"(.*?)" + re.escape(next_header), text, re.DOTALL | re.IGNORECASE)
    else:
        match = re.search(pattern + r"(.*?)$", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_bullets(text: str) -> list:
    """Pull bullet/numbered items from a text block."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        # Remove leading bullet chars or numbers
        line = re.sub(r"^[\-\*\•\d]+[\.\)]\s*", "", line)
        if line and len(line) > 5:
            items.append(line)
    return items[:10]


def _extract_matrix(text: str) -> list:
    """Find and parse the JSON feature matrix block from synthesis output."""
    # Look for ```json ... ``` or ``` ... ``` blocks containing "matrix"
    patterns = [
        r"```json\s*(\{.*?\"matrix\".*?\})\s*```",
        r"```\s*(\{.*?\"matrix\".*?\})\s*```",
        r"(\{[^{}]*\"matrix\"\s*:\s*\[.*?\]\s*\})",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(1))
                return obj.get("matrix", [])
            except Exception:
                continue
    return []


def _fallback_structured_synthesis(product_name: str, all_competitor_data: list) -> dict:
    competitors = [c for c in all_competitor_data if isinstance(c, dict)]
    names = [c.get("name", "Unknown") for c in competitors]
    browser_comp = competitors[0] if competitors else {}

    available_feature_sources = [c for c in competitors if c.get("features")]
    browser_summary = browser_comp.get("browser_findings", "")
    market_summary = (
        f"{product_name} is being compared against {len(competitors)} competitors: "
        f"{', '.join(names)}. This report was generated with partial live/browser and scraped data "
        f"because the LLM quota was rate-limited during synthesis."
    )

    advantages = [
        f"Use the live browser findings for {browser_comp.get('name', 'the primary competitor')} to sharpen homepage positioning."
    ]
    if browser_summary:
        advantages.append("Primary competitor messaging and pricing page were captured directly from the website.")
    if any(not c.get("features") for c in competitors[1:]):
        advantages.append("Several competitor profiles are only partially populated, so follow-up validation can create fast insight wins.")

    gaps = [
        "LLM quota exhaustion reduced the depth of structured competitor profiling in this run.",
        "Some competitors fell back to minimal scraped profiles with limited feature detail.",
    ]
    if not available_feature_sources:
        gaps.append("Feature matrix confidence is low because structured feature extraction was unavailable.")

    recommendations = [
        "Re-run the analysis after Groq quota resets to restore full structured competitor synthesis.",
        f"Prioritize manual review of {browser_comp.get('name', 'the browser-analyzed competitor')} homepage and pricing language.",
        "Cache successful competitor profiles so future runs consume fewer tokens.",
        "Reduce prompt size or switch to a lower-cost model for intermediate parsing steps.",
        "Review missing competitor fields and fill the highest-priority gaps first.",
    ]

    matrix = []
    feature_names = []
    for comp in competitors:
        for feature in comp.get("features") or []:
            if feature not in feature_names:
                feature_names.append(feature)
    for feature in feature_names[:8]:
        row = {"feature": feature, "us": False}
        for comp in competitors:
            row[comp.get("name", "Unknown")] = feature in (comp.get("features") or [])
        matrix.append(row)

    return {
        "market_summary": market_summary,
        "advantages": advantages,
        "gaps": gaps,
        "pricing_strategy": "Use the captured competitor pricing as directional input, then rerun once LLM quota is available for a stronger recommendation.",
        "recommendations": recommendations,
        "positioning_gaps": _fallback_positioning_gaps(product_name, competitors),
        "matrix": matrix,
        "full_text": "",
    }


def _fallback_positioning_gaps(product_name: str, competitors: list[dict]) -> list[str]:
    names = [c.get("name", "Unknown") for c in competitors if isinstance(c, dict)]
    gaps: list[str] = []

    feature_pool = set()
    pricing_models = set()
    audiences = []

    for competitor in competitors:
        if not isinstance(competitor, dict):
            continue
        for feature in competitor.get("features") or []:
            feature_pool.add(str(feature).lower())
        pricing_model = competitor.get("pricing_model")
        if pricing_model:
            pricing_models.add(str(pricing_model).lower())
        target_audience = competitor.get("target_audience")
        if target_audience:
            audiences.append(str(target_audience).lower())

    if "developer experience" not in " ".join(feature_pool):
        gaps.append(
            f"A developer-first positioning lane may still be open if {', '.join(names[:3]) or 'competitors'} emphasize broad work management over speed and ergonomics for software teams."
        )
    if "enterprise" not in " ".join(audiences):
        gaps.append("An enterprise-ready but product-simple positioning angle appears underdeveloped across the current competitor set.")
    if "free" not in pricing_models:
        gaps.append("A generous adoption-led free tier could be a whitespace move if most competitors are pushing users quickly into paid plans.")
    if "ai" not in " ".join(feature_pool):
        gaps.append("There may be room for a workflow-native AI copilot position rather than generic automation messaging.")

    if not gaps:
        gaps.append(
            f"The most likely open position for {product_name} is a sharper focus on a single ideal customer profile with simpler packaging than the broader competitor set."
        )

    return gaps[:4]


async def _generate_positioning_gaps(
    product_name: str,
    product_description: str,
    competitors: list[dict],
    synthesis: dict,
) -> list[str]:
    competitor_snapshot = []
    for competitor in competitors:
        if not isinstance(competitor, dict):
            continue
        competitor_snapshot.append(
            {
                "name": competitor.get("name"),
                "market_position": competitor.get("market_position"),
                "pricing_model": competitor.get("pricing_model"),
                "target_audience": competitor.get("target_audience"),
                "features": (competitor.get("features") or [])[:8],
                "strengths": (competitor.get("strengths") or [])[:4],
                "weaknesses": (competitor.get("weaknesses") or [])[:4],
                "browser_findings": _truncate(competitor.get("browser_findings", ""), 900),
            }
        )

    prompt = f"""
You are finding unoccupied market whitespace in a competitive software market.

Product:
- Name: {product_name}
- Description: {product_description}

Competitor data:
{json.dumps(competitor_snapshot, indent=2)}

Current synthesis:
{json.dumps({
    "market_summary": synthesis.get("market_summary"),
    "advantages": synthesis.get("advantages", []),
    "gaps": synthesis.get("gaps", []),
    "recommendations": synthesis.get("recommendations", []),
}, indent=2)}

Task:
Identify 3 to 4 positioning gaps that appear under-occupied or fully unoccupied in this market.

Return ONLY a raw JSON array of short strings.
Each item must:
- describe a specific open market position
- be grounded in the competitor evidence above
- be concise and strategy-ready
"""

    try:
        text = await llm_ask(
            prompt=prompt,
            max_tokens=350,
            system_prompt=(
                "You are a product strategy analyst specializing in competitive whitespace analysis. "
                "Return only raw JSON."
            ),
        )
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()][:4]
    except Exception as exc:
        logger.warning("[synthesis] Positioning gap generation fell back to deterministic output: %s", exc)

    return _fallback_positioning_gaps(product_name, competitors)


async def synthesize(session_id: str, job: dict, all_competitor_data: list) -> dict:
    """
    Main synthesis function. Streams chain_of_thought events and emits synthesis event.

    all_competitor_data: list of 5 dicts
      - index 0: browser_agent result (competitor #1)
      - index 1–4: deep_analyzer results (competitors #2–5)
    """
    product_name = job.get("product_name", "Our Product")
    product_description = job.get("product_description", "")
    differentiators = job.get("differentiators", "")

    logger.info(f"[synthesis] Starting for {product_name}, {len(all_competitor_data)} competitors")

    # Build competitor blocks — include ALL, especially browser-analyzed #1
    competitor_blocks = []
    for i, comp in enumerate(all_competitor_data):
        if isinstance(comp, Exception) or comp is None:
            competitor_blocks.append(f"### Competitor {i + 1}: Data unavailable (error during collection)")
        else:
            competitor_blocks.append(_build_competitor_block(comp, i))

    competitor_section = "\n\n".join(competitor_blocks)

    # Extract competitor names for feature matrix
    comp_names = []
    for c in all_competitor_data:
        if isinstance(c, dict):
            comp_names.append(c.get("name", "Unknown"))
        else:
            comp_names.append("Unknown")

    matrix_example = json.dumps({
        "matrix": [
            {"feature": "Free tier", "us": True, **{name: False for name in comp_names[:3]}},
            {"feature": "API access", "us": True, **{name: True for name in comp_names[:3]}},
        ]
    }, indent=2)

    system_prompt = (
        "You are a senior competitive intelligence analyst with 15 years of experience "
        "advising product teams at high-growth startups. You think rigorously and provide "
        "evidence-backed, actionable insights. Use [THINKING: your reasoning] blocks "
        "before each major section to show your analytical process."
    )

    user_prompt = f"""Analyze the competitive landscape for the following product and provide a complete strategic assessment.

## Our Product
Name: {product_name}
Description: {product_description}
{f"Key Differentiators: {differentiators}" if differentiators else ""}

## Competitor Intelligence
{competitor_section}

---

Provide your full analysis in this exact structure:

[THINKING: Consider the overall market dynamics, positioning gaps, and what the competitor data reveals about market maturity and opportunity.]
## Market Summary
Write 2-3 sentences describing the competitive landscape, market dynamics, and where our product sits.

[THINKING: Look specifically at weaknesses in the competitor profiles and browser findings — what are they NOT doing well?]
## Our Competitive Advantages
- List 4-6 specific, evidence-backed advantages based on competitor weaknesses found above
- Each bullet should cite which competitor(s) it applies to

[THINKING: Be honest — where are the competitors stronger, better-funded, or more mature?]
## Our Gaps and Blind Spots
- List 3-5 honest gaps or risks our product faces
- Include what competitors are doing that we are not

[THINKING: Look at the pricing models from all competitor data including browser findings for pricing pages visited.]
## Pricing Strategy Recommendation
Write 1 paragraph with a specific pricing recommendation based on the competitive pricing data gathered.

[THINKING: Prioritize by impact × feasibility. What should the team do in the next 90 days?]
## Top 5 Prioritized Recommendations
1. [Action]: [One-line action]
   [Rationale]: [One-line evidence-backed reason]
2. [Action]: ...
   [Rationale]: ...
3. [Action]: ...
   [Rationale]: ...
4. [Action]: ...
   [Rationale]: ...
5. [Action]: ...
   [Rationale]: ...

## Feature Comparison Matrix
Provide a JSON block with the feature matrix:
```json
{{
  "matrix": [
    {{"feature": "Feature Name", "us": true/false, {", ".join(f'"{n}": true/false' for n in comp_names)}}}
  ]
}}
```
Include 8-10 key features. Use the competitor data to determine true/false values accurately.
"""

    # Stream chain of thought
    full_text = ""
    chunk_count = 0

    try:
        async for chunk in llm_stream(
            prompt=user_prompt,
            max_tokens=3000,
            system_prompt=system_prompt,
        ):
            if chunk.startswith("ERROR:"):
                logger.error(f"[synthesis] LLM stream error: {chunk}")
                break
            full_text += chunk
            chunk_count += 1
            await broadcast(session_id, "chain_of_thought", {"chunk": chunk})

        logger.info(f"[synthesis] Streamed {chunk_count} chunks, {len(full_text)} chars")

    except Exception as e:
        logger.error(f"[synthesis] Streaming failed: {e}", exc_info=True)
        # Try non-streaming fallback
        try:
            full_text = await llm_ask(
                prompt=user_prompt,
                max_tokens=3000,
                system_prompt=system_prompt,
            )
            await broadcast(session_id, "chain_of_thought", {"chunk": full_text})
        except Exception as e2:
            logger.error(f"[synthesis] Fallback also failed: {e2}")
            full_text = "Synthesis failed due to LLM error."

    # --- Post-processing: extract structured fields ---
    headers = [
        "## Market Summary",
        "## Our Competitive Advantages",
        "## Our Gaps and Blind Spots",
        "## Pricing Strategy Recommendation",
        "## Top 5 Prioritized Recommendations",
        "## Feature Comparison Matrix",
    ]

    market_summary_raw = _extract_section(full_text, "## Market Summary", "## Our Competitive Advantages")
    advantages_raw = _extract_section(full_text, "## Our Competitive Advantages", "## Our Gaps")
    gaps_raw = _extract_section(full_text, "## Our Gaps and Blind Spots", "## Pricing Strategy")
    pricing_raw = _extract_section(full_text, "## Pricing Strategy Recommendation", "## Top 5")
    recommendations_raw = _extract_section(full_text, "## Top 5 Prioritized Recommendations", "## Feature Comparison")

    # Clean [THINKING:...] from display fields
    def strip_thinking(text: str) -> str:
        return re.sub(r"\[THINKING:.*?\]", "", text, flags=re.DOTALL).strip()

    market_summary = strip_thinking(market_summary_raw)
    advantages = _extract_bullets(strip_thinking(advantages_raw))
    gaps = _extract_bullets(strip_thinking(gaps_raw))
    pricing_strategy = strip_thinking(pricing_raw)
    recommendations = _extract_bullets(strip_thinking(recommendations_raw))
    matrix = _extract_matrix(full_text)

    # Fallback if extraction failed
    if not advantages:
        advantages = ["Analysis in chain-of-thought above"]
    if not gaps:
        gaps = ["See chain-of-thought analysis above"]
    if not recommendations:
        recommendations = ["See full analysis in chain-of-thought above"]

    if not full_text.strip():
        structured = _fallback_structured_synthesis(product_name, all_competitor_data)
        await broadcast(session_id, "synthesis", structured)
        logger.info("[synthesis] Using deterministic fallback synthesis because no LLM output was available")
        return structured

    positioning_gaps = await _generate_positioning_gaps(
        product_name=product_name,
        product_description=product_description,
        competitors=all_competitor_data,
        synthesis={
            "market_summary": market_summary or "See full analysis above.",
            "advantages": advantages,
            "gaps": gaps,
            "pricing_strategy": pricing_strategy or "See pricing analysis in chain-of-thought above.",
            "recommendations": recommendations,
            "full_text": full_text,
        },
    )

    structured = {
        "market_summary": market_summary or "See full analysis above.",
        "advantages": advantages,
        "gaps": gaps,
        "pricing_strategy": pricing_strategy or "See pricing analysis in chain-of-thought above.",
        "recommendations": recommendations,
        "positioning_gaps": positioning_gaps,
        "matrix": matrix,
        "full_text": full_text,
    }

    # Broadcast structured synthesis event (frontend renders panels from this)
    await broadcast(session_id, "synthesis", structured)
    logger.info(f"[synthesis] Done — {len(advantages)} advantages, {len(matrix)} matrix rows")

    return structured
