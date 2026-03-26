"""
Phase 6 — Export Router
GET /export/{session_id}/pdf  → download PDF report
GET /export/{session_id}/json → download JSON report
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

EXPORTS_DIR = Path("exports")


@router.get("/export/{session_id}/pdf")
async def download_pdf(session_id: str):
    pdf_path = EXPORTS_DIR / session_id / "report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF report not yet generated or session not found.")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=competitor_report.pdf"},
    )


@router.get("/export/{session_id}/json")
async def download_json(session_id: str):
    json_path = EXPORTS_DIR / session_id / "report.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="JSON report not yet generated or session not found.")
    return FileResponse(
        path=str(json_path),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=competitor_report.json"},
    )