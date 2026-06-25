import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .enums import RoleEnum


# ── Input Schemas (No ORM config) ───────────────────────────────────────────

class MessageIn(BaseModel):
    """
    The user's prompt. user_id is injected via auth dependency,
    and session_id is typically extracted from the URL path.
    """
    content: str


# ── Output Schemas (ORM config enabled) ─────────────────────────────────────

class MessageOut(BaseModel):
    """
    Individual message response.
    Note: token_count is intentionally omitted as it is an internal metric.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: RoleEnum
    content: str
    created_at: datetime
