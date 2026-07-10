from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.metrics import (inference_duration_seconds, time_to_first_token_seconds, tokens_generated_total, stream_errors_total,)

from llm.client import LLMClient
from llm.prompt import count_tokens
from models.message import Message
from models.session import Session
from models.user import User
from schemas.enums import RoleEnum
import logging

_logger = logging.getLogger("core.sse")

async def get_owned_session(
    session_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Session:
    """
    Fetch a session by ID and verify it belongs to the authenticated user.
    Raises 404 if not found or not owned.
    """
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session

def build_sse_event(event: str, data: dict) -> str:
    """Format an SSE string from an event name and JSON payload."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

async def sse_generator(
    db: AsyncSession,
    client: LLMClient,
    prompt: str,
    session: Session,
    user_message_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AsyncGenerator[str, None]:
    """
    Async generator that drives the SSE stream for a single chat turn.
    """
    from datetime import datetime, timezone
    
    # 1. Signal the start
    yield build_sse_event("message_start", {
        "user_message_id": str(user_message_id), 
        "assistant_message_id": str(assistant_message_id)
    })

    # 2. Stream tokens
    full_response: list[str] = []
    start_time = time.monotonic()
    first_token_time: float | None = None

    try:
        async for token in client.generate_stream(prompt):
            if first_token_time is None:
                first_token_time = time.monotonic()
                time_to_first_token_seconds.observe(first_token_time - start_time)

            normalized = token.replace("\\n", "\n").replace("\\t", "\t")
            full_response.append(normalized)
            yield build_sse_event("token", {"token": normalized})
    except Exception as exc:
        stream_errors_total.inc()
        _logger.error("Inference error: %s", exc, exc_info=True)
        yield build_sse_event("error", {"detail": "Generation failed. Please retry."})

    # 3. Persist the assistant message
    complete_content = "".join(full_response)
    assistant_token_count = count_tokens(complete_content) if complete_content else 0
    finish_reason = client.last_finish_reason

    assistant_msg = Message(
        id=assistant_message_id,
        session_id=session_id,
        role=RoleEnum.assistant.value,
        content=complete_content,
        token_count=assistant_token_count,
    )
    db.add(assistant_msg)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    inference_duration_seconds.observe(time.monotonic() - start_time)
    tokens_generated_total.inc(assistant_token_count)


    # 4. Signal completion
    yield build_sse_event("message_end", {
        "assistant_message_id": str(assistant_message_id),
        "token_count": assistant_token_count,
        "finish_reason": finish_reason
    })
