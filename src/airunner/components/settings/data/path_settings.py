import os
import re
from sqlalchemy import Column, Integer, String, event
from sqlalchemy.orm import validates

from airunner.components.data.models.base import BaseModel
from airunner.settings import AIRUNNER_BASE_PATH


def _resolve_path(stored_path: str) -> str:
    """
    Resolve a stored path to work across different environments.
    
    Handles paths that were stored with a different home directory
    (e.g., /home/joe/.local/share/airunner stored on host, but running
    in Docker where home is /root).
    
    This allows the same database to work both on the host and in containers.
    """
    if not stored_path:
        return stored_path
    
    # Pattern to match paths like /home/<user>/.local/share/airunner/...
    # or /root/.local/share/airunner/...
    pattern = r'^(/home/[^/]+|/root)/\.local/share/airunner(/.*)?$'
    match = re.match(pattern, stored_path)
    
    if match:
        # Extract the relative part after .local/share/airunner
        relative_part = match.group(2) or ''
        # Reconstruct with current AIRUNNER_BASE_PATH
        return AIRUNNER_BASE_PATH + relative_part
    
    return stored_path


class PathSettings(BaseModel):
    """
    Path settings with automatic cross-environment path resolution.
    
    When paths are stored from one environment (e.g., /home/joe on host)
    and accessed from another (e.g., /root in Docker), they are automatically
    translated to work in the current environment.
    """
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

    # List of path attributes that should be auto-resolved
    _PATH_ATTRS = {
        'base_path', 'documents_path', 'ebook_path', 'image_path',
        'llama_index_path', 'webpages_path', 'stt_model_path', 'tts_model_path'
    }

    def __getattribute__(self, name: str):
        """Override attribute access to auto-resolve paths."""
        # Get the raw value first using parent's __getattribute__
        value = super().__getattribute__(name)
        
        # Check if this is a path attribute that needs resolution
        # Use object.__getattribute__ to avoid recursion
        path_attrs = object.__getattribute__(self, '_PATH_ATTRS')
        if name in path_attrs and isinstance(value, str):
            return _resolve_path(value)
        
        return value

    def tts_processor_path(self) -> str:
        return os.path.join(self.tts_model_path, "processor")
