from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.sql import func

from airunner.components.data.models.base import BaseModel


class UwUChatSession(BaseModel):
    __tablename__ = "uwuchat_chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Stored as string so we don't depend on postgres uuid extensions.
    character_id = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False, default="")

    message_count = Column(Integer, nullable=False, default=0)
    total_tokens_used = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    is_archived = Column(Boolean, nullable=False, default=False)


class UwUChatMessage(BaseModel):
    __tablename__ = "uwuchat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    session_id = Column(
        String,
        ForeignKey("uwuchat_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String, nullable=False)

    # Encrypted at rest (Fernet token)
    content_enc = Column(LargeBinary, nullable=False)

    tokens_used = Column(Integer, nullable=False, default=0)

    is_edited = Column(Boolean, nullable=False, default=False)
    original_content_enc = Column(LargeBinary, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UwUChatProfile(BaseModel):
    __tablename__ = "uwuchat_profile"

    # Single-row table per tenant schema.
    id = Column(Integer, primary_key=True, default=1)

    avatar_job_id = Column(String, nullable=False, default="")
    banner_job_id = Column(String, nullable=False, default="")

    avatar_media_id = Column(String, nullable=False, default="")
    banner_media_id = Column(String, nullable=False, default="")

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UwUChatMedia(BaseModel):
    __tablename__ = "uwuchat_media"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    kind = Column(String, nullable=False, default="")
    content_type = Column(String, nullable=False, default="application/octet-stream")

    # Encrypted at rest (Fernet token)
    data_enc = Column(LargeBinary, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
