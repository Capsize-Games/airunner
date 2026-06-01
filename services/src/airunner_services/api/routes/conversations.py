"""Conversation session routes backed by the service data layer."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)

from .conversations_models import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessagesUpdateRequest,
    ConversationMutationResponse,
    ConversationSessionResponse,
    ConversationSummaryEnvelope,
    ConversationUserDataUpdateRequest,
    DeleteAllConversationsResponse,
    DeleteConversationResponse,
    SelectConversationRequest,
)

router = APIRouter()


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
    """Delete all conversations through the service API."""
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
