from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any

from llama_cloud import MessageRole

from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.llm.config.generation_presets import (
    get_action_generation_preset,
)
from airunner.components.llm.managers.request_plan import RequestPlan
from airunner.components.llm.utils import get_chatbot
from airunner.enums import LLMActionType


DEBUG_SETTING_FIELDS = (
    "max_new_tokens",
    "temperature",
    "top_p",
    "top_k",
    "num_beams",
    "repetition_penalty",
    "no_repeat_ngram_size",
    "reasoning_effort",
    "enable_thinking",
    "force_tool",
    "planner_mode",
    "planner_tool_hints",
    "rewritten_prompt",
    "preprocessed_primary_tool",
    "tool_categories",
    "attached_document_total_tokens",
    "attached_document_total_characters",
    "document_query_intent",
    "document_summary_focus",
    "document_answer_mode",
)


@dataclass
class LLMRequest:
    """
    Represents a request to a Large Language Model.

    This dataclass stores parameters for LLM generation, providing methods
    to convert between various formats and sources.

    Attributes:
        do_sample: Whether to use sampling for generation.
        early_stopping: Whether to stop generation when all beams are finished.
        eta_cutoff: Eta value cutoff for generation.
        length_penalty: Exponential penalty to the length of generated sequences.
        max_new_tokens: Maximum number of tokens to generate.
        min_length: Minimum length of the generated text.
        no_repeat_ngram_size: Size of n-grams that should not be repeated.
        num_beams: Number of beams for beam search.
        num_return_sequences: Number of sequences to return.
        repetition_penalty: Penalty for repeating tokens.
        temperature: Temperature for sampling.
        top_k: Keep only top-k tokens with highest probability.
        top_p: Keep the top tokens with cumulative probability >= top_p.
        use_cache: Whether to use the past key/values cache.
        do_tts_reply: Whether to convert the reply to speech.
        images: List of PIL Image objects for multimodal vision-capable models.
    """

    do_sample: bool = True
    early_stopping: bool = True
    eta_cutoff: int = 200
    length_penalty: float = 1.0
    max_new_tokens: int = 8192  # Qwen2.5 generation limit, Qwen3 can do 32768
    min_length: int = 1
    no_repeat_ngram_size: int = 3  # Block 3-word phrase repetition
    num_beams: int = 1
    num_return_sequences: int = 1
    repetition_penalty: float = 1.15  # Penalize token repetition
    temperature: float = 0.7  # Qwen3 non-thinking mode recommended
    top_k: int = 20  # Qwen3 recommended value
    top_p: float = 0.8  # Qwen3 non-thinking mode recommended
    use_cache: bool = True
    do_tts_reply: bool = True
    node_id: Optional[str] = None
    use_memory: bool = True
    ephemeral: bool = False  # If True, conversation won't be saved to database
    tool_categories: Optional[List[str]] = field(
        default_factory=list
    )  # Default: no tools (empty list). Use None for all tools.
    role: MessageRole = MessageRole.USER
    system_prompt: Optional[str] = None  # Optional system prompt override
    response_format: Optional[str] = (
        None  # Override response format instruction (e.g., "json", "conversational")
    )
    rag_files: Optional[List[str]] = field(
        default_factory=list
    )  # List of file paths to load into RAG
    ephemeral_conversation: bool = (
        False  # If True, conversation stays in memory but not saved to database
    )
    # Optional prompt augmentation toggles (used when a custom system_prompt is provided)
    include_mood: Optional[bool] = None
    include_datetime: Optional[bool] = None
    include_style: Optional[bool] = None
    include_memory: Optional[bool] = None
    include_ui_context: Optional[bool] = None
    # Request-level thinking toggle (Qwen3-style <think> blocks).
    # None means "use the global DB/default setting".
    enable_thinking: Optional[bool] = None
    # GPT-OSS reasoning effort override for runtimes without a native API knob.
    reasoning_effort: Optional[str] = None
    model: str = ""
    # Request-level backend selection (used by headless API)
    model_service: Optional[str] = None  # local | openrouter | ollama
    api_model: Optional[str] = None  # provider model name for API backends
    final_system_prompt: Optional[str] = None
    rewritten_prompt: Optional[str] = None
    preprocessed_primary_tool: Optional[str] = None
    # Request-level quantization override for local HF models.
    # This is consumed by the model manager to set llm_generator_settings.dtype
    # before loading; it must NOT be passed through to transformers generate().
    dtype: Optional[str] = None  # auto | 4bit | 8bit | 32bit
    force_tool: Optional[str] = (
        None  # Force a specific tool to be called (from slash commands)
    )
    planner_mode: Optional[str] = None
    planner_tool_hints: Optional[List[str]] = field(default_factory=list)
    attached_document_capabilities: Optional[List[Dict[str, Any]]] = field(
        default_factory=list
    )
    attached_document_total_tokens: int = 0
    attached_document_total_characters: int = 0
    document_query_intent: Optional[str] = None
    document_summary_focus: Optional[str] = None
    document_primary_tool: Optional[str] = None
    document_answer_mode: Optional[str] = None
    request_plan: Optional[RequestPlan] = None
    images: Optional[List[Any]] = field(
        default_factory=list
    )  # List of PIL Image objects for vision-capable models

    def to_dict(self) -> Dict:
        """
        Convert the request parameters to a dictionary suitable for API calls.

        Ensures all values meet minimum thresholds and handles special cases
        for beam-based generation parameters.

        Returns:
            Dict: Dictionary representation of the request parameters.
        """
        min_val = 0.0001
        length_penalty = max(self.length_penalty, min_val)
        repetition_penalty = max(self.repetition_penalty, min_val)
        top_p = max(self.top_p, min_val)
        temperature = max(self.temperature, min_val)

        data = asdict(self)
        data.update(
            {
                "length_penalty": length_penalty,
                "repetition_penalty": repetition_penalty,
                "top_p": top_p,
                "temperature": temperature,
            }
        )

        # Length penalty flag is only used in beam-based generation modes
        # so num_beams should be > 1 for length penalty to be used.
        if self.num_beams == 1 and length_penalty != 0.0:
            del data["length_penalty"]

        # Early stopping flag is only used in beam-based generation modes
        # so num_beams should be > 1 for early stopping to be used.
        if self.num_beams == 1:
            del data["early_stopping"]

        data.pop("node_id")
        data.pop("use_memory")
        data.pop("role")
        # Request-level routing knobs are handled by the manager, not the model.
        data.pop("model_service", None)
        data.pop("api_model", None)
        data.pop("final_system_prompt", None)
        data.pop("rewritten_prompt", None)
        data.pop("preprocessed_primary_tool", None)
        data.pop("dtype", None)
        data.pop("reasoning_effort", None)
        data.pop("planner_mode", None)
        data.pop("planner_tool_hints", None)
        data.pop("attached_document_capabilities", None)
        data.pop("attached_document_total_tokens", None)
        data.pop("attached_document_total_characters", None)
        data.pop("document_query_intent", None)
        data.pop("document_summary_focus", None)
        data.pop("document_primary_tool", None)
        data.pop("document_answer_mode", None)
        data.pop("request_plan", None)
        # Prompt augmentation toggles are consumed by workflow setup, not passed to the model
        data.pop("include_mood", None)
        data.pop("include_datetime", None)
        data.pop("include_style", None)
        data.pop("include_memory", None)
        data.pop("include_ui_context", None)
        # Images are PIL objects, not JSON serializable - handle separately
        data.pop("images", None)

        return data

    def to_debug_metadata(
        self,
        *,
        title: str = "Request Settings",
    ) -> Dict[str, Any]:
        """Return one compact, read-only debug snapshot for the request."""
        settings: Dict[str, Any] = {}
        for field_name in DEBUG_SETTING_FIELDS:
            value = getattr(self, field_name, None)
            if value is None:
                continue
            if isinstance(value, list) and not value:
                continue
            settings[field_name] = value
        if self.request_plan is not None:
            settings["request_plan"] = self.request_plan.to_dict()
        return {
            "kind": "llm_request_settings",
            "title": title,
            "settings": settings,
        }

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
        """
        Create an LLMRequest instance from individual parameter values.

        Args:
            do_sample: Whether to use sampling for generation.
            early_stopping: Whether to stop generation when all beams are finished.
            eta_cutoff: Eta value cutoff for generation.
            length_penalty: Exponential penalty to the length (already scaled).
            max_new_tokens: Maximum number of tokens to generate.
            min_length: Minimum length of the generated text.
            no_repeat_ngram_size: Size of n-grams that should not be repeated.
            num_beams: Number of beams for beam search.
            num_return_sequences: Number of sequences to return.
            repetition_penalty: Penalty for repeating tokens (already scaled).
            temperature: Temperature for sampling (already scaled).
            top_k: Keep only top-k tokens with highest probability.
            top_p: Keep the top tokens with cumulative probability >= top_p (already scaled).
            use_cache: Whether to use the past key/values cache.

        Returns:
            LLMRequest: A new instance with the specified parameter values.
        """
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
            temperature=temperature
            / 1000.0,  # Fixed: was /10000.0 causing 0.1 instead of 1.0
            top_k=top_k,  # Ensure top_k is correctly passed through
            top_p=top_p / 1000.0,
            use_cache=use_cache,
        )

    @classmethod
    def from_chatbot(cls, chatbot_id: int = None) -> "LLMRequest":
        """
        Create an LLMRequest instance from a Chatbot model.

        Args:
            chatbot_id: Optional ID of the chatbot to use. If None, uses the first chatbot.

        Returns:
            LLMRequest: A new instance with parameters from the specified chatbot.
        """
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
        cls, llm_settings_id: Optional[int] = None
    ) -> "LLMRequest":
        """
        Create an LLMRequest instance from LLMGeneratorSettings.

        Args:
            llm_settings_id: Optional ID of the settings to use. If None, uses the first settings.

        Returns:
            LLMRequest: A new instance with parameters from the specified settings or from
                        the associated chatbot if settings don't override parameters.
        """
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

        request.enable_thinking = True
        request.reasoning_effort = getattr(
            llm_settings,
            "reasoning_effort",
            "medium",
        )
        return request

    @classmethod
    def from_default(cls) -> "LLMRequest":
        """
        Create an LLMRequest instance with default settings.

        Returns:
            LLMRequest: A new instance with default settings from LLMGeneratorSettings.
        """
        return cls.from_llm_settings()

    @staticmethod
    def _copy_generation_fields(
        target: "LLMRequest",
        source: "LLMRequest",
    ) -> None:
        """Copy generation-only fields without changing routing behavior."""
        fields = (
            "do_sample",
            "early_stopping",
            "eta_cutoff",
            "length_penalty",
            "max_new_tokens",
            "min_length",
            "no_repeat_ngram_size",
            "num_beams",
            "num_return_sequences",
            "repetition_penalty",
            "temperature",
            "top_k",
            "top_p",
            "use_cache",
        )
        for field_name in fields:
            setattr(target, field_name, getattr(source, field_name))

    @classmethod
    def for_visible_action(
        cls,
        action: "LLMActionType",  # type: ignore
        llm_settings: Optional[Any] = None,
    ) -> "LLMRequest":
        """Create one top-level request using presets or manual overrides."""
        request = cls.for_action(action)
        if not getattr(llm_settings, "override_parameters", False):
            return request

        overrides = cls.from_values(
            do_sample=getattr(llm_settings, "do_sample", request.do_sample),
            early_stopping=getattr(
                llm_settings,
                "early_stopping",
                request.early_stopping,
            ),
            eta_cutoff=getattr(llm_settings, "eta_cutoff", request.eta_cutoff),
            length_penalty=getattr(
                llm_settings,
                "length_penalty",
                int(request.length_penalty * 1000),
            ),
            max_new_tokens=getattr(
                llm_settings,
                "max_new_tokens",
                request.max_new_tokens,
            ),
            min_length=getattr(llm_settings, "min_length", request.min_length),
            no_repeat_ngram_size=getattr(
                llm_settings,
                "ngram_size",
                request.no_repeat_ngram_size,
            ),
            num_beams=getattr(llm_settings, "num_beams", request.num_beams),
            num_return_sequences=getattr(
                llm_settings,
                "sequences",
                request.num_return_sequences,
            ),
            repetition_penalty=getattr(
                llm_settings,
                "repetition_penalty",
                int(request.repetition_penalty * 100),
            ),
            temperature=getattr(
                llm_settings,
                "temperature",
                int(request.temperature * 1000),
            ),
            top_k=getattr(llm_settings, "top_k", request.top_k),
            top_p=getattr(
                llm_settings,
                "top_p",
                int(request.top_p * 1000),
            ),
            use_cache=getattr(llm_settings, "use_cache", request.use_cache),
        )
        cls._copy_generation_fields(request, overrides)
        return request

    @classmethod
    def for_action(cls, action: "LLMActionType") -> "LLMRequest":  # type: ignore
        """
        Create an LLMRequest optimized for a specific action type.

        Different actions require different generation parameters:
        - CHAT: Conversational, creative, variety
        - CODE: Precise, deterministic, structured
        - SUMMARIZE: Concise, factual, consistent
        - GENERATE_IMAGE: Descriptive, creative
        - SEARCH/RAG: Precise, focused, factual

        Args:
            action: The LLMActionType to optimize for

        Returns:
            LLMRequest: A new instance with parameters optimized for the action
        """
        preset = get_action_generation_preset(action)
        return cls(**preset.to_request_kwargs())


@dataclass
class OpenrouterMistralRequest(LLMRequest):
    """
    A specialized LLMRequest for OpenRouter Mistral model.

    This class extends LLMRequest with parameters specific to OpenRouter's
    Mistral implementation.

    Attributes:
        max_tokens: Maximum number of tokens to generate.
        temperature: Temperature for sampling.
        seed: Random seed for reproducible generation.
        top_p: Keep the top tokens with cumulative probability >= top_p.
        top_k: Keep only top-k tokens with highest probability.
        frequency_penalty: Penalty for token frequency (range: [-2, 2]).
        presence_penalty: Penalty for token presence (range: [-2, 2]).
        repetition_penalty: Penalty for repeating tokens (range: [-2, 2]).
        logit_bias: Token bias to apply during generation.
        top_logprobs: Number of most likely tokens to return at each step.
        min_p: Minimum probability for token consideration.
        top_a: Parameter for nucleus sampling.
    """

    max_tokens: int = 256
    temperature: float = 0.1
    seed: int = 42
    top_p: float = 0.9
    top_k: int = 20  # Qwen3 recommended value
    frequency_penalty: float = 0  # Range: [-2, 2]
    presence_penalty: float = 0  # Range: [-2, 2]
    repetition_penalty: float = 0  # Range: [-2, 2]
    logit_bias: float = 0
    top_logprobs: int = 0
    min_p: float = 0
    top_a: int = 0

    def to_dict(self) -> Dict:
        """
        Convert the request parameters to a dictionary suitable for OpenRouter API calls.

        Ensures all values meet minimum thresholds.

        Returns:
            Dict: Dictionary representation of the request parameters for OpenRouter.
        """
        min_val = 0.0001
        frequency_penalty = max(self.frequency_penalty, min_val)
        presence_penalty = max(self.presence_penalty, min_val)
        repetition_penalty = max(self.repetition_penalty, min_val)
        top_p = max(self.top_p, min_val)
        temperature = max(self.temperature, min_val)

        data = {
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "seed": self.seed,
            "top_p": top_p,
            "top_k": self.top_k,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "repetition_penalty": repetition_penalty,
            "logit_bias": self.logit_bias,
            "top_logprobs": self.top_logprobs,
            "min_p": self.min_p,
            "top_a": self.top_a,
        }
        return data
