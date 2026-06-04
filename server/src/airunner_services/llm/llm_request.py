"""Service-owned request model for LLM generation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llama_cloud import MessageRole  # type: ignore[import-untyped]

from airunner_services.database.models.chatbot import (  # type: ignore[import-untyped]
    Chatbot,
)
from airunner_services.database.models.llm_generator_settings import (  # type: ignore[import-untyped]
    LLMGeneratorSettings,
)
from airunner_services.llm.get_chatbot import get_chatbot
from airunner_services.utils.application.enum_resolver import llm_action_type


LLMActionType = llm_action_type()
_MIN_GENERATION_VALUE = 0.0001


def _clamp_generation_value(value: float) -> float:
    """Keep generation values above zero for downstream backends."""
    return max(value, _MIN_GENERATION_VALUE)


@dataclass
class LLMRequest:
    """Represent one request to a Large Language Model."""

    do_sample: bool = True
    early_stopping: bool = True
    eta_cutoff: int = 200
    length_penalty: float = 1.0
    max_new_tokens: int = 8192
    min_length: int = 1
    no_repeat_ngram_size: int = 3
    num_beams: int = 1
    num_return_sequences: int = 1
    repetition_penalty: float = 1.15
    temperature: float = 0.7
    top_k: int = 20
    top_p: float = 0.8
    use_cache: bool = True
    do_tts_reply: bool = True
    node_id: Optional[str] = None
    use_memory: bool = True
    ephemeral: bool = False
    tool_categories: Optional[List[str]] = field(default_factory=list)
    role: MessageRole = MessageRole.USER
    system_prompt: Optional[str] = None
    response_format: Optional[str] = None
    rag_files: Optional[List[str]] = field(default_factory=list)
    ephemeral_conversation: bool = False
    include_mood: Optional[bool] = None
    include_datetime: Optional[bool] = None
    include_style: Optional[bool] = None
    include_memory: Optional[bool] = None
    include_ui_context: Optional[bool] = None
    enable_thinking: Optional[bool] = None
    reasoning_effort: Optional[str] = None
    model: str = ""
    model_service: Optional[str] = None
    api_model: Optional[str] = None
    gguf_runtime_profile: Optional[str] = None
    dtype: Optional[str] = None
    force_tool: Optional[str] = None
    images: Optional[List[Any]] = field(default_factory=list)
    llm_overrides: Optional[Dict[str, Dict[str, Any]]] = None

    def merge_preset_overrides(
        self, overrides: Dict[str, Dict[str, Any]], label: str
    ) -> None:
        """Apply per-preset overrides when they exist for *label*."""
        preset_overrides = overrides.get(label)
        if not preset_overrides:
            return
        for attr, val in preset_overrides.items():
            if hasattr(self, attr):
                setattr(self, attr, val)

    def to_generation_kwargs(self) -> Dict[str, Any]:
        """Convert one request into model-generation kwargs."""
        generation_kwargs: Dict[str, Any] = {
            "do_sample": self.do_sample,
            "eta_cutoff": self.eta_cutoff,
            "max_new_tokens": self.max_new_tokens,
            "min_length": self.min_length,
            "no_repeat_ngram_size": self.no_repeat_ngram_size,
            "num_beams": self.num_beams,
            "num_return_sequences": self.num_return_sequences,
            "repetition_penalty": _clamp_generation_value(
                self.repetition_penalty
            ),
            "temperature": _clamp_generation_value(self.temperature),
            "top_k": self.top_k,
            "top_p": _clamp_generation_value(self.top_p),
            "use_cache": self.use_cache,
        }

        if self.num_beams != 1:
            generation_kwargs["early_stopping"] = self.early_stopping
            generation_kwargs["length_penalty"] = _clamp_generation_value(
                self.length_penalty
            )

        if self.enable_thinking is not None:
            generation_kwargs["enable_thinking"] = self.enable_thinking
        if self.reasoning_effort:
            generation_kwargs["reasoning_effort"] = self.reasoning_effort

        return generation_kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Return one explicit generation payload for compatibility."""
        return self.to_generation_kwargs()

    @classmethod
    def from_values(
        cls,
        do_sample: bool,
        early_stopping: bool,
        eta_cutoff: int,
        length_penalty: float,
        max_new_tokens: int,
        min_length: int,
        no_repeat_ngram_size: int,
        num_beams: int,
        num_return_sequences: int,
        repetition_penalty: float,
        temperature: float,
        top_k: int,
        top_p: float,
        use_cache: bool,
    ) -> "LLMRequest":
        """Create one request from explicit generation values."""
        return cls(
            do_sample=do_sample,
            early_stopping=early_stopping,
            eta_cutoff=eta_cutoff,
            length_penalty=length_penalty / 1000.0,
            max_new_tokens=max_new_tokens,
            min_length=min_length,
            no_repeat_ngram_size=no_repeat_ngram_size,
            num_beams=num_beams,
            num_return_sequences=num_return_sequences,
            repetition_penalty=repetition_penalty / 100.0,
            temperature=temperature / 1000.0,
            top_k=top_k,
            top_p=top_p / 1000.0,
            use_cache=use_cache,
        )

    @classmethod
    def from_chatbot(
        cls,
        chatbot_id: Optional[int] = None,
    ) -> "LLMRequest":
        """Create one request from one chatbot row."""
        if chatbot_id:
            chatbot = Chatbot.objects.get(chatbot_id)
        else:
            chatbot = Chatbot.objects.first()

        return cls.from_values(
            do_sample=chatbot.do_sample,
            early_stopping=chatbot.early_stopping,
            eta_cutoff=chatbot.eta_cutoff,
            length_penalty=chatbot.length_penalty,
            max_new_tokens=chatbot.max_new_tokens,
            min_length=chatbot.min_length,
            no_repeat_ngram_size=chatbot.ngram_size,
            num_beams=chatbot.num_beams,
            num_return_sequences=chatbot.num_return_sequences,
            repetition_penalty=chatbot.repetition_penalty,
            temperature=chatbot.temperature,
            top_k=chatbot.top_k,
            top_p=chatbot.top_p,
            use_cache=chatbot.use_cache,
        )

    @classmethod
    def from_llm_settings(
        cls,
        llm_settings_id: Optional[int] = None,
    ) -> "LLMRequest":
        """Create one request from one LLMGeneratorSettings row."""
        if llm_settings_id:
            llm_settings = LLMGeneratorSettings.objects.get(llm_settings_id)
        else:
            llm_settings = LLMGeneratorSettings.objects.first()

        if llm_settings.override_parameters:
            request = cls.from_values(
                do_sample=llm_settings.do_sample,
                early_stopping=llm_settings.early_stopping,
                eta_cutoff=llm_settings.eta_cutoff,
                length_penalty=llm_settings.length_penalty,
                max_new_tokens=llm_settings.max_new_tokens,
                min_length=llm_settings.min_length,
                no_repeat_ngram_size=llm_settings.ngram_size,
                num_beams=llm_settings.num_beams,
                num_return_sequences=llm_settings.sequences,
                repetition_penalty=llm_settings.repetition_penalty,
                temperature=llm_settings.temperature,
                top_k=llm_settings.top_k,
                top_p=llm_settings.top_p,
                use_cache=llm_settings.use_cache,
            )
        else:
            request = cls.from_chatbot(get_chatbot().id)

        request.enable_thinking = getattr(
            llm_settings,
            "enable_thinking",
            True,
        )
        request.reasoning_effort = getattr(
            llm_settings,
            "reasoning_effort",
            "medium",
        )
        return request

    @classmethod
    def from_default(cls) -> "LLMRequest":
        """Create one request using the default persisted settings."""
        return cls.from_llm_settings()

    @classmethod
    def for_action(cls, action: Any) -> "LLMRequest":
        """Create one request optimized for one action type."""
        if action in (LLMActionType.CHAT, LLMActionType.UPDATE_MOOD):
            return cls(
                do_sample=True,
                temperature=0.7,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                max_new_tokens=8192,
                top_k=20,
                top_p=0.8,
                tool_categories=None,
            )

        if action == LLMActionType.CODE:
            return cls(
                do_sample=True,
                temperature=0.6,
                repetition_penalty=1.1,
                no_repeat_ngram_size=2,
                max_new_tokens=8192,
                top_k=20,
                top_p=0.8,
                tool_categories=None,
            )

        if action == LLMActionType.PERFORM_RAG_SEARCH:
            return cls(
                do_sample=True,
                temperature=0.3,
                repetition_penalty=1.1,
                no_repeat_ngram_size=2,
                max_new_tokens=300,
                top_k=30,
                top_p=0.9,
                tool_categories=["RAG", "SEARCH"],
            )

        if action in (LLMActionType.SUMMARIZE, LLMActionType.SEARCH):
            return cls(
                do_sample=True,
                temperature=0.3,
                repetition_penalty=1.1,
                no_repeat_ngram_size=2,
                max_new_tokens=300,
                top_k=30,
                top_p=0.9,
                tool_categories=["SEARCH"],
            )

        if action == LLMActionType.GENERATE_IMAGE:
            return cls(
                do_sample=True,
                temperature=0.9,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                max_new_tokens=200,
                top_k=50,
                top_p=0.9,
            )

        if action in (
            LLMActionType.DECISION,
            LLMActionType.APPLICATION_COMMAND,
            LLMActionType.FILE_INTERACTION,
            LLMActionType.WORKFLOW,
            LLMActionType.WORKFLOW_INTERACTION,
        ):
            return cls(
                do_sample=True,
                temperature=0.6,
                repetition_penalty=1.0,
                no_repeat_ngram_size=0,
                max_new_tokens=32768,
                top_k=20,
                top_p=0.95,
                tool_categories=None,
            )

        if action == LLMActionType.DEEP_RESEARCH:
            return cls(
                do_sample=True,
                temperature=0.6,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                max_new_tokens=32768,
                top_k=20,
                top_p=0.95,
                tool_categories=["RESEARCH", "SEARCH"],
            )

        return cls(
            do_sample=True,
            temperature=0.8,
            repetition_penalty=1.15,
            no_repeat_ngram_size=3,
            max_new_tokens=500,
            top_k=50,
            top_p=0.9,
        )


@dataclass
class OpenrouterMistralRequest(LLMRequest):
    """Specialized request model for OpenRouter Mistral backends."""

    max_tokens: int = 256
    temperature: float = 0.1
    seed: int = 42
    top_p: float = 0.9
    top_k: int = 20
    frequency_penalty: float = 0
    presence_penalty: float = 0
    repetition_penalty: float = 0
    logit_bias: float = 0
    top_logprobs: int = 0
    min_p: float = 0
    top_a: int = 0

    def to_generation_kwargs(self) -> Dict[str, Any]:
        """Convert one OpenRouter request into API kwargs."""
        return {
            "max_tokens": self.max_tokens,
            "temperature": _clamp_generation_value(self.temperature),
            "seed": self.seed,
            "top_p": _clamp_generation_value(self.top_p),
            "top_k": self.top_k,
            "frequency_penalty": _clamp_generation_value(
                self.frequency_penalty
            ),
            "presence_penalty": _clamp_generation_value(
                self.presence_penalty
            ),
            "repetition_penalty": _clamp_generation_value(
                self.repetition_penalty
            ),
            "logit_bias": self.logit_bias,
            "top_logprobs": self.top_logprobs,
            "min_p": self.min_p,
            "top_a": self.top_a,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return one explicit generation payload for compatibility."""
        return self.to_generation_kwargs()