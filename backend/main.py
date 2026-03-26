"""
Main FastAPI application — Phase 6 complete version
Includes export router for PDF/JSON downloads.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.analyze import router as analyze_router
from routers.stream import router as stream_router
from routers.export import router as export_router
from worker import start_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the analysis worker before accepting requests
    asyncio.create_task(start_worker())
    logger.info("Worker started")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Competitor Intelligence Analyzer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(stream_router)
app.include_router(export_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
