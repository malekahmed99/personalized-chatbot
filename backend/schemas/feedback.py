import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .enums import VoteEnum


# ── Input Schemas (No ORM config) ───────────────────────────────────────────

class FeedbackIn(BaseModel):
    vote: VoteEnum


# ── Output Schemas (ORM config enabled) ─────────────────────────────────────

class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    vote: VoteEnum
    created_at: datetime
    updated_at: datetime
