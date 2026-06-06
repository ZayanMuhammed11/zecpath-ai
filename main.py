"""
Zecpath ATS API — FastAPI application entry point.
"""

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from routers import ats, jobs, resume
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Zecpath ATS API",
    version="1.0.0",
    description="AI-powered hiring platform API layer for ATS scoring and ranking.",
)

# ── Router registration ────────────────────────────────────────────────────────
app.include_router(resume.router, prefix="/resume", tags=["Resume"])
app.include_router(ats.router, prefix="/ats", tags=["ATS"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])


# ── Startup event ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    """Log a startup confirmation when the API process initialises."""
    logger.info("Zecpath ATS API started")


# ── Root health-check ──────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root() -> dict:
    """
    Root health-check endpoint.

    Returns:
        dict: API name and version confirmation.
    """
    return {"message": "Zecpath ATS API Running", "version": "1.0.0"}


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exception escaping an endpoint.
    Returns a standardised ErrorResponse JSON body with HTTP 500.

    Args:
        request (Request): The incoming FastAPI request object.
        exc (Exception): The unhandled exception.

    Returns:
        JSONResponse: Standardised error payload with status 500.
    """
    logger.error("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "PROCESSING_ERR",
            "message": str(exc),
            "detail": None,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )