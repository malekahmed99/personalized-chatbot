import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class MessageFeedback(Base):
    __tablename__ = "message_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # UNIQUE enforces 1:1 — one feedback record per assistant message, no duplicates.
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    # VARCHAR(10) for future-proofing — 'up'/'down' fit easily, and the wider
    # type accommodates additional values without a migration.
    vote = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # No onupdate — updated_at is bumped explicitly by the feedback service (PATCH endpoint).
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="feedback")

    # Constraints
    __table_args__ = (
        CheckConstraint("vote IN ('up', 'down')", name="ck_message_feedback_vote"),
    )
