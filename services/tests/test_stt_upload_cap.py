"""STT uploads must be size-capped before transcription runs."""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

from airunner_services.api.routes.stt import transcribe_audio


def test_oversize_upload_is_rejected_with_413(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_STT_MAX_UPLOAD_BYTES", "1024")
    upload = UploadFile(filename="clip.wav", file=io.BytesIO(b"x" * 4096))

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(transcribe_audio(audio=upload, req=None))

    assert excinfo.value.status_code == 413
