from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any

from llama_cloud import MessageRole

from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.llm.utils import get_chatbot
from airunner.enums import LLMActionType


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
    model: str = ""
    use_mode_routing: bool = (
        False  # Enable mode-based routing (author/code/research/qa/general)
    )
    mode_override: Optional[str] = (
        None  # Force specific mode instead of auto-classification
    )
    force_tool: Optional[str] = (
        None  # Force a specific tool to be called (from slash commands)
    )
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
        # Images are PIL objects, not JSON serializable - handle separately
        data.pop("images", None)

        return data

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
            return cls.from_values(
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
            return cls.from_chatbot(get_chatbot().id)

    @classmethod
    def from_default(cls) -> "LLMRequest":
        """
        Create an LLMRequest instance with default settings.

        Returns:
            LLMRequest: A new instance with default settings from LLMGeneratorSettings.
        """
        return cls.from_llm_settings()

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
        # Action-specific parameters
        if action in (LLMActionType.CHAT, LLMActionType.UPDATE_MOOD):
            # Chat: Conversational, coherent, natural
            # Qwen3 non-thinking mode: temp=0.7, top_p=0.8, top_k=20
            return cls(
                do_sample=True,
                temperature=0.7,  # Qwen3 non-thinking mode recommended
                repetition_penalty=1.15,  # Moderate anti-repetition
                no_repeat_ngram_size=3,  # Block phrase repetition
                max_new_tokens=8192,  # Qwen2.5 generation limit
                top_k=20,  # Qwen3 recommended
                top_p=0.8,  # Qwen3 non-thinking mode recommended
                tool_categories=[],  # No tools by default for chat - enable explicitly when needed
            )

        elif action == LLMActionType.CODE:
            # Code: Precise, structured, with thinking enabled
            # Enable CODE and WORKFLOW tools for TDD workflow
            # Qwen3 thinking mode: temp=0.6, top_p=0.95, top_k=20
            # max_new_tokens=32768 per Qwen3 docs for adequate thinking + tool calls
            return cls(
                do_sample=True,  # Required for Qwen3 thinking mode
                temperature=0.6,  # Qwen3 thinking mode recommended
                repetition_penalty=1.05,  # Light penalty (code can repeat patterns)
                no_repeat_ngram_size=0,  # Allow code patterns
                max_new_tokens=32768,  # Qwen3 recommended for thinking + code
                top_k=20,  # Qwen3 recommended
                top_p=0.95,  # Qwen3 thinking mode recommended
                tool_categories=[
                    "CODE",
                    "WORKFLOW",
                    "SYSTEM",  # For file operations
                ],
            )

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            # RAG Search: Enable RAG and search tools for document retrieval
            return cls(
                do_sample=True,
                temperature=0.3,  # Mostly consistent
                repetition_penalty=1.1,  # Moderate anti-repetition
                no_repeat_ngram_size=2,  # Some phrase blocking
                max_new_tokens=300,  # Concise responses
                top_k=30,
                top_p=0.9,
                tool_categories=[
                    "RAG",
                    "SEARCH",
                ],  # Enable RAG and search tools
            )

        elif action in (
            LLMActionType.SUMMARIZE,
            LLMActionType.SEARCH,
        ):
            # Summarize/Search: Concise, factual, consistent
            return cls(
                do_sample=True,
                temperature=0.3,  # Mostly consistent
                repetition_penalty=1.1,  # Moderate anti-repetition
                no_repeat_ngram_size=2,  # Some phrase blocking
                max_new_tokens=300,  # Concise responses
                top_k=30,
                top_p=0.9,
                tool_categories=["SEARCH"],  # Enable search tools
            )

        elif action == LLMActionType.GENERATE_IMAGE:
            # Image prompts: Descriptive, creative, detailed
            return cls(
                do_sample=True,
                temperature=0.9,  # More creative
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                max_new_tokens=200,  # Focused descriptions
                top_k=50,
                top_p=0.9,
            )

        elif action in (
            LLMActionType.DECISION,
            LLMActionType.APPLICATION_COMMAND,
            LLMActionType.FILE_INTERACTION,
            LLMActionType.WORKFLOW,
            LLMActionType.WORKFLOW_INTERACTION,
        ):
            # Commands/Decisions: Precise with thinking for complex reasoning
            # Use Qwen3 thinking mode for multi-step tool chains
            return cls(
                do_sample=True,  # Required for Qwen3 thinking mode
                temperature=0.6,  # Qwen3 thinking mode
                repetition_penalty=1.0,  # No penalty needed
                no_repeat_ngram_size=0,  # Allow any patterns
                max_new_tokens=32768,  # Full thinking + tool call budget
                top_k=20,  # Qwen3 recommended
                top_p=0.95,  # Qwen3 thinking mode
                tool_categories=None,  # Enable all tools for commands/decisions
            )

        elif action == LLMActionType.DEEP_RESEARCH:
            # Deep Research: Comprehensive, creative, high token budget
            # Needs to generate long-form structured content with extensive tool use
            # Use Qwen3 thinking mode for complex research tasks
            return cls(
                do_sample=True,  # Required for Qwen3 thinking mode
                temperature=0.6,  # Qwen3 thinking mode
                repetition_penalty=1.15,  # Avoid redundant phrasing
                no_repeat_ngram_size=3,  # Some phrase blocking
                max_new_tokens=32768,  # Qwen3 recommended for complex reasoning
                top_k=20,  # Qwen3 recommended
                top_p=0.95,  # Qwen3 thinking mode
                tool_categories=["RESEARCH", "SEARCH"],  # Research tools only
            )

        else:
            # Default: Balanced settings
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
