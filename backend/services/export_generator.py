import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path("exports")


def _ensure_exports_dir(session_id: str) -> Path:
    session_dir = EXPORTS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _safe_text(text) -> str:
    if text is None:
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _write_section(pdf, title: str, lines: list[str]) -> None:
    if not lines:
        return
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(239, 246, 255)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 8, title, ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)
    for line in lines:
        pdf.set_x(14)
        pdf.multi_cell(0, 6, _safe_text(line))
    pdf.ln(3)


def _generate_pdf_sync(session_dir: Path, job: dict, all_competitor_data: list, synthesis: dict) -> str:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    product_name = job.get("product_name", "Product")
    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")

    pdf.set_fill_color(30, 64, 175)
    pdf.rect(0, 0, 210, 36, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, "Competitor Intelligence Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(10, 21)
    pdf.cell(0, 8, _safe_text(f"Product: {product_name}"), ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(45)

    overview = job.get("product_description", "")
    if overview:
        _write_section(pdf, "Product Overview", [overview])

    market_summary = synthesis.get("market_summary", "")
    if market_summary:
        _write_section(pdf, "Market Summary", [market_summary])

    competitor_lines = []
    for idx, comp in enumerate(all_competitor_data, start=1):
        if not isinstance(comp, dict):
            continue
        competitor_lines.append(f"{idx}. {comp.get('name', f'Competitor {idx}')}")
        competitor_lines.append(f"URL: {comp.get('url', '')}")
        competitor_lines.append(f"Source: {'Browser' if comp.get('is_browser_analyzed') else 'Deep analysis'}")
        if comp.get("browser_findings"):
            competitor_lines.append(f"Browser Findings: {comp.get('browser_findings', '')[:700]}")
        if comp.get("market_position"):
            competitor_lines.append(f"Market Position: {comp.get('market_position', '')}")
        if comp.get("pricing_model") and comp.get("pricing_model") != "unknown":
            competitor_lines.append(
                f"Pricing: {comp.get('pricing_model')} | {comp.get('pricing_details', '')[:120]}"
            )
        features = comp.get("features") or []
        if features:
            competitor_lines.append("Features: " + ", ".join(str(x) for x in features[:5]))
        strengths = comp.get("strengths") or []
        if strengths:
            competitor_lines.append("Strengths: " + ", ".join(str(x) for x in strengths[:3]))
        weaknesses = comp.get("weaknesses") or []
        if weaknesses:
            competitor_lines.append("Weaknesses: " + ", ".join(str(x) for x in weaknesses[:3]))
        competitor_lines.append("")
    _write_section(pdf, "Competitor Profiles", competitor_lines)

    advantages = synthesis.get("advantages", [])
    if advantages:
        _write_section(pdf, "Our Competitive Advantages", [f"Y {item}" for item in advantages])

    gaps = synthesis.get("gaps", [])
    if gaps:
        _write_section(pdf, "Gaps and Blind Spots", [f"- {item}" for item in gaps])

    pricing_strategy = synthesis.get("pricing_strategy", "")
    if pricing_strategy:
        _write_section(pdf, "Pricing Strategy Recommendation", [pricing_strategy])

    recommendations = synthesis.get("recommendations", [])
    if recommendations:
        _write_section(
            pdf,
            "Top Prioritized Recommendations",
            [f"{idx}. {item}" for idx, item in enumerate(recommendations[:5], start=1)],
        )

    matrix = synthesis.get("matrix", [])
    if matrix:
        matrix_lines = []
        for row in matrix[:10]:
            feature = row.get("feature", "")
            states = []
            for key, value in row.items():
                if key == "feature":
                    continue
                states.append(f"{key}={'Yes' if value else 'No'}")
            matrix_lines.append(f"{feature}: " + " | ".join(states))
        _write_section(pdf, "Feature Comparison Matrix", matrix_lines)

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, _safe_text(f"{product_name} | Generated {generated_at}"), align="C")

    pdf_path = session_dir / "report.pdf"
    pdf.output(str(pdf_path))
    logger.info(f"[export] PDF written to {pdf_path}")
    return str(pdf_path)


async def generate_json(session_dir: Path, job: dict, all_competitor_data: list, synthesis: dict) -> str:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "product": {
            "name": job.get("product_name", ""),
            "description": job.get("product_description", ""),
            "differentiators": job.get("differentiators", ""),
            "url": job.get("product_url", ""),
        },
        "competitors": [],
        "synthesis": {
            "market_summary": synthesis.get("market_summary", ""),
            "advantages": synthesis.get("advantages", []),
            "gaps": synthesis.get("gaps", []),
            "pricing_strategy": synthesis.get("pricing_strategy", ""),
            "recommendations": synthesis.get("recommendations", []),
            "matrix": synthesis.get("matrix", []),
        },
    }

    for comp in all_competitor_data:
        if isinstance(comp, dict):
            payload["competitors"].append(comp)
        else:
            payload["competitors"].append({"error": "Data unavailable"})

    json_path = session_dir / "report.json"
    async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(payload, indent=2, ensure_ascii=False))

    logger.info(f"[export] JSON written to {json_path}")
    return str(json_path)


async def generate_exports(session_id: str, job: dict, all_competitor_data: list, synthesis: dict) -> dict:
    session_dir = _ensure_exports_dir(session_id)
    loop = asyncio.get_event_loop()

    pdf_task = loop.run_in_executor(None, _generate_pdf_sync, session_dir, job, all_competitor_data, synthesis)
    json_task = generate_json(session_dir, job, all_competitor_data, synthesis)

    results = await asyncio.gather(pdf_task, json_task, return_exceptions=True)

    pdf_path = results[0] if not isinstance(results[0], Exception) else None
    json_path = results[1] if not isinstance(results[1], Exception) else None

    if isinstance(results[0], Exception):
        logger.error(f"[export] PDF generation failed: {results[0]}", exc_info=True)
    if isinstance(results[1], Exception):
        logger.error(f"[export] JSON generation failed: {results[1]}", exc_info=True)

    return {"pdf_path": pdf_path, "json_path": json_path}
