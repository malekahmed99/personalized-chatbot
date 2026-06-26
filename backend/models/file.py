import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class File(Base):
    """
    SCAFFOLDED — do not implement upload logic yet.
    Schema is defined now to avoid a painful migration when file/image upload
    support is added in a future iteration.
    """
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    # ON DELETE SET NULL: file records survive message deletion.
    # Only the association to that specific message is severed.
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    # Absolute path on host filesystem or object store key (e.g. S3).
    # Never store binary data in the DB.
    storage_path = Column(Text, nullable=False)
    # Display only — never used as the actual storage path.
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(127), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="files")
    message = relationship("Message", back_populates="files")
