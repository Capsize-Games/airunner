"""Request models for legacy compatibility routes."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict


class LegacyLLMGenerateRequest(BaseModel):
    """Payload for the legacy streaming LLM endpoint."""

    model_config = ConfigDict(extra="allow")

    prompt: str
    action: str = "CHAT"
    stream: bool = True
    do_tts_reply: bool = False
    gguf_runtime_profile: Optional[str] = None
    system_prompt: Optional[str] = None
    search_hints: Optional[Dict[str, Any]] = None
    conversation_id: Optional[int] = None
    node_id: Optional[str] = None


class LegacyInterruptRequest(BaseModel):
    """Payload for the legacy interrupt endpoint."""

    kind: Literal["process", "image"] = "process"


class LegacyArtRequest(BaseModel):
    """Payload for the legacy synchronous art endpoint."""

    model_config = ConfigDict(extra="allow")

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    scale: Optional[float] = None
    cfg_scale: Optional[float] = None
    seed: Optional[int] = None
    random_seed: Optional[bool] = None
    n_samples: int = 1


__all__ = [
    "LegacyArtRequest",
    "LegacyInterruptRequest",
    "LegacyLLMGenerateRequest",
]