"""Service-owned path settings model."""

import os
import re

from sqlalchemy import Column, Integer, String

from airunner_services.database.base import BaseModel
from airunner_services.settings import AIRUNNER_BASE_PATH


def _resolve_path(stored_path: str) -> str:
    """Resolve persisted paths across different runtime environments."""
    if not stored_path:
        return stored_path

    pattern = r"^(/home/[^/]+|/root)/\.local/share/airunner(/.*)?$"
    match = re.match(pattern, stored_path)
    if match:
        relative_part = match.group(2) or ""
        return AIRUNNER_BASE_PATH + relative_part
    return stored_path


class PathSettings(BaseModel):
    """Persisted AIRunner filesystem locations with path translation."""

    __tablename__ = "path_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_path = Column(String, default=AIRUNNER_BASE_PATH)
    documents_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/other", "documents")
        ),
    )
    ebook_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/other", "ebooks")
        ),
    )
    image_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "art/other", "images")
        ),
    )
    llama_index_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/rag", "db")
        ),
    )
    webpages_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/other", "webpages")
        ),
    )
    stt_model_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/models/stt")
        ),
    )
    tts_model_path = Column(
        String,
        default=os.path.expanduser(
            os.path.join(AIRUNNER_BASE_PATH, "text/models/tts")
        ),
    )

    _PATH_ATTRS = {
        "base_path",
        "documents_path",
        "ebook_path",
        "image_path",
        "llama_index_path",
        "rag_index_path",
        "webpages_path",
        "stt_model_path",
        "tts_model_path",
    }

    @property
    def rag_index_path(self) -> str:
        """Compatibility alias for the legacy llama_index_path column."""
        return self.llama_index_path

    @rag_index_path.setter
    def rag_index_path(self, value: str) -> None:
        self.llama_index_path = value

    def __getattribute__(self, name: str):
        """Auto-resolve stored paths when callers access them."""
        value = super().__getattribute__(name)
        path_attrs = object.__getattribute__(self, "_PATH_ATTRS")
        if name in path_attrs and isinstance(value, str):
            return _resolve_path(value)
        return value

    def tts_processor_path(self) -> str:
        """Return the processor directory under the configured TTS root."""
        return os.path.join(self.tts_model_path, "processor")


__all__ = ["PathSettings"]
