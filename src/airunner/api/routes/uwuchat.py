from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, update, func

from airunner.components.data.session_manager import session_scope
from airunner.components.uwuchat.data.models.chat import (
    UwUChatMessage,
    UwUChatMedia,
    UwUChatProfile,
    UwUChatSession,
)
from airunner.utils.crypto.data_encryption import decrypt_bytes, encrypt_bytes


router = APIRouter()


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    # Keep it simple and stable for JS.
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


class ChatSessionCreateRequest(BaseModel):
    character_id: str
    title: str = ""


class ChatSessionResponse(BaseModel):
    id: str
    character_id: str
    title: str
    message_count: int
    total_tokens_used: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_message_at: Optional[str] = None
    is_archived: bool


class MessageCreateRequest(BaseModel):
    role: str
    content: str
    tokens_used: int = 0
    is_edited: bool = False
    original_content: str = ""


class MessagePatchRequest(BaseModel):
    content: Optional[str] = None
    is_edited: Optional[bool] = None
    original_content: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    tokens_used: int
    is_edited: bool
    created_at: Optional[str] = None


class TruncateRequest(BaseModel):
    message_id: str
    include_target: bool = True


class TruncateResponse(BaseModel):
    deleted_count: int
    deleted_tokens: int


class ProfileResponse(BaseModel):
    avatar_job_id: str = ""
    banner_job_id: str = ""
    avatar_media_id: str = ""
    banner_media_id: str = ""


class ProfilePatchRequest(BaseModel):
    avatar_job_id: Optional[str] = None
    banner_job_id: Optional[str] = None
    avatar_media_id: Optional[str] = None
    banner_media_id: Optional[str] = None


class MediaCreateRequest(BaseModel):
    kind: str = ""
    content_type: str = "application/octet-stream"
    data_b64: str = Field(..., description="Base64-encoded bytes")


class MediaCreateResponse(BaseModel):
    id: str


@router.post("/chats", response_model=ChatSessionResponse)
def create_chat(req: ChatSessionCreateRequest):
    chat_id = str(uuid.uuid4())

    with session_scope() as session:
        chat = UwUChatSession(
            id=chat_id,
            character_id=req.character_id,
            title=(req.title or "").strip(),
        )
        session.add(chat)
        session.flush()
        session.refresh(chat)

        return ChatSessionResponse(
            id=chat.id,
            character_id=chat.character_id,
            title=chat.title or "",
            message_count=chat.message_count or 0,
            total_tokens_used=chat.total_tokens_used or 0,
            created_at=_utc_iso(chat.created_at),
            updated_at=_utc_iso(chat.updated_at),
            last_message_at=_utc_iso(chat.last_message_at),
            is_archived=bool(chat.is_archived),
        )


@router.get("/chats")
def list_chats():
    with session_scope() as session:
        rows = session.execute(
            select(UwUChatSession).where(UwUChatSession.is_archived.is_(False)).order_by(
                UwUChatSession.last_message_at.desc().nullslast(), UwUChatSession.created_at.desc()
            )
        ).scalars().all()

        payload: list[dict[str, Any]] = []
        for chat in rows:
            # Last message preview (decrypt just 1 row)
            last_msg = session.execute(
                select(UwUChatMessage)
                .where(UwUChatMessage.session_id == chat.id)
                .order_by(UwUChatMessage.created_at.desc())
                .limit(1)
            ).scalars().first()

            last_message = None
            if last_msg is not None:
                try:
                    content = decrypt_bytes(last_msg.content_enc).decode("utf-8", errors="replace")
                except Exception:
                    content = ""
                preview = content[:100] + ("..." if len(content) > 100 else "")
                last_message = {"role": last_msg.role, "content": preview}

            payload.append(
                {
                    "id": chat.id,
                    "character_id": chat.character_id,
                    "title": chat.title or "",
                    "message_count": int(chat.message_count or 0),
                    "total_tokens_used": int(chat.total_tokens_used or 0),
                    "created_at": _utc_iso(chat.created_at),
                    "updated_at": _utc_iso(chat.updated_at),
                    "last_message_at": _utc_iso(chat.last_message_at),
                    "is_archived": bool(chat.is_archived),
                    "last_message": last_message,
                }
            )

        return payload


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    with session_scope() as session:
        chat = session.get(UwUChatSession, chat_id)
        if chat is None or chat.is_archived:
            raise HTTPException(status_code=404, detail="Chat not found")

        messages = session.execute(
            select(UwUChatMessage)
            .where(UwUChatMessage.session_id == chat_id)
            .order_by(UwUChatMessage.created_at.asc())
        ).scalars().all()

        msg_payload: list[dict[str, Any]] = []
        for m in messages:
            msg_payload.append(
                {
                    "id": m.id,
                    "session_id": m.session_id,
                    "role": m.role,
                    "content": decrypt_bytes(m.content_enc).decode("utf-8", errors="replace"),
                    "tokens_used": int(m.tokens_used or 0),
                    "is_edited": bool(m.is_edited),
                    "created_at": _utc_iso(m.created_at),
                }
            )

        return {
            "id": chat.id,
            "character_id": chat.character_id,
            "title": chat.title or "",
            "message_count": int(chat.message_count or 0),
            "total_tokens_used": int(chat.total_tokens_used or 0),
            "created_at": _utc_iso(chat.created_at),
            "updated_at": _utc_iso(chat.updated_at),
            "last_message_at": _utc_iso(chat.last_message_at),
            "is_archived": bool(chat.is_archived),
            "messages": msg_payload,
        }


@router.delete("/chats/{chat_id}")
def archive_chat(chat_id: str):
    with session_scope() as session:
        chat = session.get(UwUChatSession, chat_id)
        if chat is None or chat.is_archived:
            raise HTTPException(status_code=404, detail="Chat not found")
        chat.is_archived = True
        session.add(chat)
        session.flush()
        return {"ok": True}


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
def create_message(chat_id: str, req: MessageCreateRequest):
    role = (req.role or "").strip()
    if role not in {"user", "assistant", "system"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    raw = (req.content or "").encode("utf-8")
    enc = encrypt_bytes(raw)

    original_enc = None
    if (req.original_content or "").strip():
        original_enc = encrypt_bytes((req.original_content or "").encode("utf-8"))

    with session_scope() as session:
        chat = session.get(UwUChatSession, chat_id)
        if chat is None or chat.is_archived:
            raise HTTPException(status_code=404, detail="Chat not found")

        msg = UwUChatMessage(
            session_id=chat_id,
            role=role,
            content_enc=enc,
            tokens_used=int(req.tokens_used or 0),
            is_edited=bool(req.is_edited),
            original_content_enc=original_enc,
        )
        session.add(msg)

        # Update session stats (simple + correct)
        chat.message_count = int(chat.message_count or 0) + 1
        chat.total_tokens_used = int(chat.total_tokens_used or 0) + int(req.tokens_used or 0)
        chat.last_message_at = func.now()
        session.add(chat)

        session.flush()
        session.refresh(msg)
        session.refresh(chat)

        return MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=req.content,
            tokens_used=int(msg.tokens_used or 0),
            is_edited=bool(msg.is_edited),
            created_at=_utc_iso(msg.created_at),
        )


@router.patch("/chats/{chat_id}/messages/{message_id}", response_model=MessageResponse)
def patch_message(chat_id: str, message_id: str, req: MessagePatchRequest):
    with session_scope() as session:
        msg = session.get(UwUChatMessage, message_id)
        if msg is None or msg.session_id != chat_id:
            raise HTTPException(status_code=404, detail="Message not found")

        if req.content is not None:
            msg.content_enc = encrypt_bytes((req.content or "").encode("utf-8"))
        if req.is_edited is not None:
            msg.is_edited = bool(req.is_edited)
        if req.original_content is not None:
            if (req.original_content or "").strip():
                msg.original_content_enc = encrypt_bytes((req.original_content or "").encode("utf-8"))
            else:
                msg.original_content_enc = None

        session.add(msg)
        session.flush()
        session.refresh(msg)

        return MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=decrypt_bytes(msg.content_enc).decode("utf-8", errors="replace"),
            tokens_used=int(msg.tokens_used or 0),
            is_edited=bool(msg.is_edited),
            created_at=_utc_iso(msg.created_at),
        )


@router.post("/chats/{chat_id}/messages/truncate", response_model=TruncateResponse)
def truncate_from_message(chat_id: str, req: TruncateRequest):
    with session_scope() as session:
        target = session.get(UwUChatMessage, req.message_id)
        if target is None or target.session_id != chat_id:
            raise HTTPException(status_code=404, detail="Message not found")

        # Delete messages created_at >= target.created_at (or strictly after, for edit flows).
        cmp = (
            UwUChatMessage.created_at >= target.created_at
            if req.include_target
            else UwUChatMessage.created_at > target.created_at
        )
        to_delete = session.execute(
            select(UwUChatMessage).where(
                UwUChatMessage.session_id == chat_id,
                cmp,
            )
        ).scalars().all()

        deleted_count = len(to_delete)
        deleted_tokens = sum(int(m.tokens_used or 0) for m in to_delete)

        for m in to_delete:
            session.delete(m)

        # Recompute session stats
        remaining = session.execute(
            select(UwUChatMessage).where(UwUChatMessage.session_id == chat_id)
        ).scalars().all()

        remaining_count = len(remaining)
        remaining_tokens = sum(int(m.tokens_used or 0) for m in remaining)
        last_message_at = None
        if remaining:
            last_message_at = max((m.created_at for m in remaining if m.created_at is not None), default=None)

        chat = session.get(UwUChatSession, chat_id)
        if chat is not None:
            chat.message_count = remaining_count
            chat.total_tokens_used = remaining_tokens
            chat.last_message_at = last_message_at
            session.add(chat)

        session.flush()

        return TruncateResponse(deleted_count=deleted_count, deleted_tokens=deleted_tokens)


@router.post("/profile", response_model=ProfileResponse)
def upsert_profile(req: ProfilePatchRequest):
    with session_scope() as session:
        profile = session.get(UwUChatProfile, 1)
        if profile is None:
            profile = UwUChatProfile(id=1)
            session.add(profile)
            session.flush()
            session.refresh(profile)

        if req.avatar_job_id is not None:
            profile.avatar_job_id = req.avatar_job_id or ""
        if req.banner_job_id is not None:
            profile.banner_job_id = req.banner_job_id or ""
        if req.avatar_media_id is not None:
            profile.avatar_media_id = req.avatar_media_id or ""
        if req.banner_media_id is not None:
            profile.banner_media_id = req.banner_media_id or ""

        session.add(profile)
        session.flush()
        session.refresh(profile)

        return ProfileResponse(
            avatar_job_id=profile.avatar_job_id or "",
            banner_job_id=profile.banner_job_id or "",
            avatar_media_id=profile.avatar_media_id or "",
            banner_media_id=profile.banner_media_id or "",
        )


@router.get("/profile", response_model=ProfileResponse)
def get_profile():
    with session_scope() as session:
        profile = session.get(UwUChatProfile, 1)
        if profile is None:
            profile = UwUChatProfile(id=1)
            session.add(profile)
            session.flush()
            session.refresh(profile)

        return ProfileResponse(
            avatar_job_id=profile.avatar_job_id or "",
            banner_job_id=profile.banner_job_id or "",
            avatar_media_id=profile.avatar_media_id or "",
            banner_media_id=profile.banner_media_id or "",
        )


@router.post("/media", response_model=MediaCreateResponse)
def create_media(req: MediaCreateRequest):
    try:
        raw = base64.b64decode(req.data_b64.encode("utf-8"), validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64")

    media_id = str(uuid.uuid4())
    enc = encrypt_bytes(raw)

    with session_scope() as session:
        media = UwUChatMedia(
            id=media_id,
            kind=(req.kind or "").strip(),
            content_type=(req.content_type or "application/octet-stream").strip(),
            data_enc=enc,
        )
        session.add(media)
        session.flush()
        return MediaCreateResponse(id=media_id)


@router.get("/media/{media_id}")
def get_media(media_id: str):
    with session_scope() as session:
        media = session.get(UwUChatMedia, media_id)
        if media is None:
            raise HTTPException(status_code=404, detail="Not found")

        raw = decrypt_bytes(media.data_enc)
        return Response(content=raw, media_type=media.content_type or "application/octet-stream")
