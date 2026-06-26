import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .message import MessageOut


# ── Input Schemas (No ORM config) ───────────────────────────────────────────

class SessionCreate(BaseModel):
    """
    Empty body. user_id is injected by the dependency layer (auth),
    and title is auto-generated upon the first message.
    """
    pass


class SessionRename(BaseModel):
    title: str


# ── Output Schemas (ORM config enabled) ─────────────────────────────────────

class SessionListItem(BaseModel):
    """Lighter response for listing all sessions (omits created_at)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    updated_at: datetime


class SessionOut(BaseModel):
    """Full session response, including the ordered message history."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class SessionListOut(BaseModel):
    """Paginated wrapper for GET /api/sessions."""
    sessions: list[SessionListItem]
    total: int
