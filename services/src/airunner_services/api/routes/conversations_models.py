"""Request/response models for conversation endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationSummaryResponse(BaseModel):
    """Serialized conversation metadata for service consumers."""

    id: Optional[int] = None
    title: str = ""
    summary: str = ""
    current: bool = False
    timestamp: str = ""
    chatbot_id: Optional[int] = None
    chatbot_name: str = ""
    user_id: Optional[int] = None
    user_name: str = ""
    message_count: int = 0
    user_data: Dict[str, Any] = Field(default_factory=dict)


class ConversationListResponse(BaseModel):
    """Envelope for one conversation listing response."""

    conversations: List[ConversationSummaryResponse] = Field(
        default_factory=list
    )


class ConversationSessionResponse(BaseModel):
    """Envelope for one loaded conversation session."""

    conversation: Optional[ConversationSummaryResponse] = None
    conversation_id: Optional[int] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    """Request payload for creating one new conversation."""

    max_messages: int = 50


class SelectConversationRequest(BaseModel):
    """Request payload for selecting one active conversation."""

    conversation_id: int
    max_messages: int = 50


class ConversationSummaryEnvelope(BaseModel):
    """Envelope for one conversation summary request."""

    conversation_id: int
    summary: str = ""


class DeleteConversationResponse(BaseModel):
    """Envelope for one conversation deletion request."""

    conversation_id: int
    deleted: bool


class DeleteAllConversationsResponse(BaseModel):
    """Envelope for deleting all conversations in test environments."""

    deleted: int


class ConversationMessagesUpdateRequest(BaseModel):
    """Request payload for replacing one conversation's messages."""

    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationUserDataUpdateRequest(BaseModel):
    """Request payload for replacing one conversation's user data."""

    user_data: Dict[str, Any] = Field(default_factory=dict)


class ConversationMutationResponse(BaseModel):
    """Envelope for one conversation mutation response."""

    conversation_id: int
    updated: bool
