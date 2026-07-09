"""
routers/internal.py — Internal operational endpoints (no user JWT required).

GET /internal/health        — Lightweight liveness check.
GET /internal/model/status  — Detailed model operational state for the UI indicator.
"""
from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import settings
from llm.client import LLMClient, ModelStatus

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """
    Lightweight liveness check. Confirms the FastAPI process is running.
    Does not test DB connectivity or model state — just confirms the process is alive.
    """
    return {"status": "ok"}

@router.get("/ready")
async def readiness() -> dict:
    """
    Used by Docker's HEALTHCHECK — unlike /health
    """
    try:
        client = LLMClient.get()
        current_status = client.status
    except RuntimeError:
        return JSONResponse(status_code=503, content={"status": "loading"})

    if current_status == ModelStatus.IDLE:
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": current_status.value})

@router.get("/model/status")
async def model_status() -> dict:
    """
    Return the current operational state of the local Qwen model.
    Used by the frontend '● AI model online' indicator.

    Possible status values:
      loading    — Model is being read into RAM (app just started)
      idle       — Model is loaded and ready
      processing — Model is currently generating a response
      error      — Model failed to load; inference is unavailable
    """
    model_filename = os.path.basename(settings.model_path)

    try:
        client = LLMClient.get()
        current_status = client.status.value
    except RuntimeError:
        # LLMClient.get() raises if initialize() was never called or is still running
        current_status = ModelStatus.LOADING.value

    return {
        "status": current_status,
        "model": model_filename,
        "context_window": settings.model_max_context,
        "token_budget": settings.chat_history_token_budget,
    }
