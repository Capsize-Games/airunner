"""Conversation session routes backed by the service data layer."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)

router = APIRouter()


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


def _manager() -> ConversationHistoryManager:
    """Return one conversation history manager instance."""
    return ConversationHistoryManager()


def _sync_selected_conversation(request: Request, conversation_id: int) -> None:
    """Best-effort sync of service-owned selection through lifecycle APIs."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    sync_selection = getattr(
        lifecycle_service,
        "sync_selected_conversation",
        None,
    )
    if callable(sync_selection):
        sync_selection(conversation_id)


def _sync_deleted_conversation(request: Request, conversation_id: int) -> None:
    """Best-effort sync of conversation deletion through lifecycle APIs."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    sync_deleted = getattr(
        lifecycle_service,
        "sync_deleted_conversation",
        None,
    )
    if callable(sync_deleted):
        sync_deleted(conversation_id)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(limit: int = 50) -> ConversationListResponse:
    """Return serialized conversation metadata through the service API."""
    return ConversationListResponse(
        conversations=_manager().list_conversations(limit=limit)
    )


@router.post(
    "/conversations",
    response_model=ConversationSessionResponse,
)
async def create_conversation(
    body: ConversationCreateRequest,
    request: Request,
) -> ConversationSessionResponse:
    """Create one new current conversation through the service API."""
    session = _manager().create_conversation(max_messages=body.max_messages)
    conversation_id = session.get("conversation_id")
    if conversation_id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create conversation",
        )
    _sync_selected_conversation(request, conversation_id)
    return ConversationSessionResponse(**session)


@router.get(
    "/conversations/session",
    response_model=ConversationSessionResponse,
)
async def get_conversation_session(
    conversation_id: Optional[int] = None,
    max_messages: int = 50,
) -> ConversationSessionResponse:
    """Return one conversation session without changing the selection."""
    session = _manager().get_conversation_session(
        conversation_id=conversation_id,
        max_messages=max_messages,
    )
    if conversation_id is not None and session.get("conversation") is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationSessionResponse(**session)


@router.post(
    "/conversations/select",
    response_model=ConversationSessionResponse,
)
async def select_conversation(
    body: SelectConversationRequest,
    request: Request,
) -> ConversationSessionResponse:
    """Mark one conversation current and return the serialized session."""
    session = _manager().get_conversation_session(
        conversation_id=body.conversation_id,
        max_messages=body.max_messages,
        mark_current=True,
    )
    if session.get("conversation") is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _sync_selected_conversation(request, body.conversation_id)
    return ConversationSessionResponse(**session)


@router.get(
    "/conversations/{conversation_id}/summary",
    response_model=ConversationSummaryEnvelope,
)
async def summarize_conversation(
    conversation_id: int,
) -> ConversationSummaryEnvelope:
    """Return one persisted or generated summary for a conversation."""
    summary = _manager().summarize_conversation(conversation_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationSummaryEnvelope(**summary)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteConversationResponse,
)
async def delete_conversation(
    conversation_id: int,
    request: Request,
) -> DeleteConversationResponse:
    """Delete one conversation through the service API."""
    deleted = _manager().delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _sync_deleted_conversation(request, conversation_id)
    return DeleteConversationResponse(
        conversation_id=conversation_id,
        deleted=True,
    )


@router.delete(
    "/conversations",
    response_model=DeleteAllConversationsResponse,
)
async def delete_all_conversations() -> DeleteAllConversationsResponse:
    """Delete all conversations through the service API in tests only."""
    if os.environ.get("AIRUNNER_ENVIRONMENT") != "test":
        raise HTTPException(
            status_code=403,
            detail="delete_all_conversations only allowed in test environment",
        )
    return DeleteAllConversationsResponse(
        deleted=_manager().delete_all_conversations(),
    )


@router.put(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMutationResponse,
)
async def update_conversation_messages(
    conversation_id: int,
    body: ConversationMessagesUpdateRequest,
) -> ConversationMutationResponse:
    """Replace one conversation's stored messages through the API."""
    updated = _manager().update_conversation_messages(
        conversation_id,
        body.messages,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationMutationResponse(
        conversation_id=conversation_id,
        updated=True,
    )


@router.put(
    "/conversations/{conversation_id}/user-data",
    response_model=ConversationMutationResponse,
)
async def update_conversation_user_data(
    conversation_id: int,
    body: ConversationUserDataUpdateRequest,
) -> ConversationMutationResponse:
    """Replace one conversation's stored user-data through the API."""
    updated = _manager().update_conversation_user_data(
        conversation_id,
        body.user_data,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationMutationResponse(
        conversation_id=conversation_id,
        updated=True,
    )
