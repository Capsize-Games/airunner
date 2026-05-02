"""Dedicated loader for local transformers execution components."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from transformers import AutoModelForCausalLM

from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.llm.adapters import is_gguf_model
from airunner.components.llm.managers.llm_settings import LLMSettings
from airunner.components.llm.managers.mixins.adapter_loader_mixin import (
    AdapterLoaderMixin,
)
from airunner.components.llm.managers.mixins.model_loader_mixin import (
    ModelLoaderMixin,
)
from airunner.components.llm.managers.mixins.property_mixin import (
    PropertyMixin,
)
from airunner.components.llm.managers.mixins.quantization_config_mixin import (
    QuantizationConfigMixin,
)
from airunner.components.llm.managers.mixins.tokenizer_loader_mixin import (
    TokenizerLoaderMixin,
)
from airunner.enums import ModelStatus, ModelType


class LocalExecutionComponentLoader(
    BaseModelManager,
    AdapterLoaderMixin,
    ModelLoaderMixin,
    PropertyMixin,
    QuantizationConfigMixin,
    TokenizerLoaderMixin,
):
    """Load local tokenizer/model pairs without constructing the full manager."""

    model_type: ModelType = ModelType.LLM
    model_class: str = "llm_local_execution_loader"

    _model: Optional[AutoModelForCausalLM] = None
    _tokenizer: Optional[object] = None
    _current_model_path: Optional[str] = None

    def __init__(
        self,
        llm_settings: Any,
        model_path: Optional[str],
    ):
        super().__init__()
        self.llm_settings = llm_settings or LLMSettings()
        self.llm_request = SimpleNamespace(model=model_path)
        self._current_model_path = model_path
        self._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.chatbot = SimpleNamespace(use_cache=True, model_version="")
        self._tool_manager = None
        self._hw_profiler = None

    def load(self) -> None:
        """Load tokenizer and model for local transformers execution."""
        if not self.llm_settings.use_local_llm:
            return
        if is_gguf_model(self.model_path):
            self.logger.info(
                "GGUF model detected at %s, skipping HuggingFace local "
                "execution component loading",
                self.model_path,
            )
            return
        self._load_tokenizer()
        self._load_model()

    def unload(self) -> None:
        """Release loaded tokenizer and model references."""
        self._model = None
        self._tokenizer = None

    def load_components(self) -> tuple[Any, Any]:
        """Load and return model/tokenizer references for the factory."""
        self.load()
        model = self._model
        tokenizer = self._tokenizer
        self._model = None
        self._tokenizer = None
        return model, tokenizer