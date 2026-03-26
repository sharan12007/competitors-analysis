"""
routers/analyze.py — POST /analyze
Validates input, generates session_id, enqueues job, returns immediately.
The frontend then connects to /stream/{session_id} for all results.
"""

import uuid
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from worker import analysis_queue

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    product_name: str
    product_description: str
    product_url: Optional[str] = None
    differentiators: Optional[str] = None


class AnalyzeResponse(BaseModel):
    session_id: str


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Starts an analysis run. Returns a session_id immediately.
    All results are delivered asynchronously via SSE on /stream/{session_id}.
    """
    session_id = str(uuid.uuid4())

    job = {
        "session_id": session_id,
        "product_name": request.product_name,
        "product_description": request.product_description,
        "product_url": request.product_url,
        "differentiators": request.differentiators,
    }

    await analysis_queue.put(job)
    logger.info(f"Enqueued job: session_id={session_id}, product={request.product_name}")

    return AnalyzeResponse(session_id=session_id)