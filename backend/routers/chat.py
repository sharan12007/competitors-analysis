import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from session_store import get_session_data
from services.llm_client import ask

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str


def _build_report_context(session_payload: dict) -> str:
    job = session_payload.get("job", {})
    competitors = session_payload.get("competitors", [])
    synthesis = session_payload.get("synthesis", {})
    github_repos = session_payload.get("github_repos", [])

    trimmed_competitors = []
    for competitor in competitors:
        trimmed_competitors.append(
            {
                "name": competitor.get("name"),
                "url": competitor.get("url"),
                "is_browser_analyzed": competitor.get("is_browser_analyzed"),
                "market_position": competitor.get("market_position"),
                "pricing_model": competitor.get("pricing_model"),
                "pricing_details": competitor.get("pricing_details"),
                "target_audience": competitor.get("target_audience"),
                "features": competitor.get("features", [])[:8],
                "strengths": competitor.get("strengths", [])[:5],
                "weaknesses": competitor.get("weaknesses", [])[:5],
                "browser_findings": (competitor.get("browser_findings") or "")[:2500],
            }
        )

    trimmed_synthesis = {
        "market_summary": synthesis.get("market_summary"),
        "advantages": synthesis.get("advantages", [])[:10],
        "gaps": synthesis.get("gaps", [])[:10],
        "pricing_strategy": synthesis.get("pricing_strategy"),
        "recommendations": synthesis.get("recommendations", [])[:10],
        "matrix": synthesis.get("matrix", [])[:20],
        "full_text": (synthesis.get("full_text") or "")[:5000],
    }

    trimmed_github = github_repos[:8]

    context = {
        "product": {
            "name": job.get("product_name"),
            "description": job.get("product_description"),
            "url": job.get("product_url"),
            "differentiators": job.get("differentiators"),
        },
        "competitors": trimmed_competitors,
        "synthesis": trimmed_synthesis,
        "github_repos": trimmed_github,
    }
    return json.dumps(context, indent=2, ensure_ascii=True)


def _build_history_text(history: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for item in history[-8:]:
        role = item.get("role", "").strip().lower()
        content = item.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


@router.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_with_report(session_id: str, request: ChatRequest) -> ChatResponse:
    session_payload = await get_session_data(session_id)
    if session_payload is None:
        raise HTTPException(status_code=404, detail="Analysis session not found or not ready yet.")

    context = _build_report_context(session_payload)
    history_text = _build_history_text(request.history)

    prompt = f"""
You are answering questions about a completed competitor intelligence report.

Rules:
- Answer ONLY from the provided session context.
- If the answer is not supported by the context, say that clearly.
- Be concise but useful.
- Prefer direct comparisons when asked.
- Quote specific competitors, pricing details, features, strengths, weaknesses, and synthesis findings when relevant.

Conversation so far:
{history_text or "No previous conversation."}

Current user question:
{request.question.strip()}

Session context:
{context}
"""

    try:
        answer = await ask(
            prompt=prompt,
            max_tokens=700,
            system_prompt=(
                "You are a sharp product strategy analyst answering follow-up questions about a completed "
                "competitive intelligence report. Stay grounded in the supplied report context."
            ),
        )
    except Exception as exc:
        logger.error("[chat] Failed to answer question for session %s: %s", session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Chat request failed.") from exc

    cleaned = (answer or "").strip()
    if not cleaned:
        cleaned = "I could not find a grounded answer in the saved report context."

    return ChatResponse(answer=cleaned)
