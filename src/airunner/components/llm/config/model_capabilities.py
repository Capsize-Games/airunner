"""
Model Capability Registry

Defines which models are used for which specialized tasks in the multi-tier
LLM architecture. The primary conversational model handles tool calling and
orchestration, while specialized models handle specific tasks triggered by
tool calls.

Architecture:
    - Primary LLM: Handles conversation, tool calling, orchestration
    - Specialized Models: Execute specific tasks (prompt enhancement, code gen, etc.)
    - Resource Manager: Handles model swapping and VRAM management
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class ModelCapability(Enum):
    """Capabilities that models can be assigned to."""

    # Primary conversational LLM with tool calling
    PRIMARY_CONVERSATION = "primary_conversation"

    # Specialized task models
    PROMPT_ENHANCEMENT = "prompt_enhancement"
    CODE_GENERATION = "code_generation"
    CODE_EDITING = "code_editing"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"


@dataclass
class ModelSpec:
    """Specification for a model and its capabilities."""

    model_path: str
    """HuggingFace model path or local path."""

    capabilities: list[ModelCapability]
    """What this model can do."""

    max_context: int = 32768
    """Maximum context length."""

    supports_function_calling: bool = False
    """Whether model has native function calling support."""

    quantization: Optional[str] = "4bit"
    """Quantization method (4bit, 8bit, None)."""

    gpu_memory_gb: float = 4.0
    """Approximate VRAM usage in GB."""

    priority: int = 0
    """Priority for auto-selection (higher = preferred)."""


# Model Registry
# Maps model paths to their specifications
MODEL_REGISTRY: Dict[str, ModelSpec] = {
    # Primary Conversational Models (tool-calling capable)
    "Qwen/Qwen2.5-7B-Instruct": ModelSpec(
        model_path="Qwen/Qwen2.5-7B-Instruct",
        capabilities=[ModelCapability.PRIMARY_CONVERSATION],
        max_context=32768,
        supports_function_calling=True,  # Has good prompt-based tool calling
        quantization="4bit",
        gpu_memory_gb=5.0,
        priority=100,
    ),
    "Qwen/Qwen3-8B": ModelSpec(
        model_path="Qwen/Qwen3-8B",
        capabilities=[ModelCapability.PRIMARY_CONVERSATION],
        max_context=32768,  # 131K with YaRN
        supports_function_calling=True,
        quantization="4bit",
        gpu_memory_gb=8.0,
        priority=95,  # Higher priority - supports both thinking and instruct modes
    ),
    # Specialized Small Models (2-3B for specific tasks)
    "Qwen/Qwen2.5-3B-Instruct": ModelSpec(
        model_path="Qwen/Qwen2.5-3B-Instruct",
        capabilities=[
            ModelCapability.PROMPT_ENHANCEMENT,
            ModelCapability.SUMMARIZATION,
            ModelCapability.TRANSLATION,
        ],
        max_context=32768,
        supports_function_calling=False,
        quantization="4bit",
        gpu_memory_gb=2.0,
        priority=80,
    ),
    "Qwen/Qwen2.5-Coder-7B-Instruct": ModelSpec(
        model_path="Qwen/Qwen2.5-Coder-7B-Instruct",
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_EDITING,
        ],
        max_context=32768,
        supports_function_calling=False,
        quantization="4bit",
        gpu_memory_gb=4.5,
        priority=85,
    ),
    "deepseek-ai/deepseek-coder-6.7b-instruct": ModelSpec(
        model_path="deepseek-ai/deepseek-coder-6.7b-instruct",
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_EDITING,
        ],
        max_context=16384,
        supports_function_calling=False,
        quantization="4bit",
        gpu_memory_gb=4.0,
        priority=75,
    ),
    # Fallback models
    "mistralai/Ministral-3-8B-Instruct-2512": ModelSpec(
        model_path="mistralai/Ministral-3-8B-Instruct-2512",
        capabilities=[
            ModelCapability.SUMMARIZATION,
            ModelCapability.TRANSLATION,
        ],
        max_context=262144,  # 256K context
        supports_function_calling=True,  # Ministral 3 has native function calling
        quantization="4bit",
        gpu_memory_gb=8.0,
        priority=50,
    ),
}


# Capability to Model Mapping
# Maps capabilities to preferred models
CAPABILITY_TO_MODEL: Dict[ModelCapability, str] = {
    ModelCapability.PRIMARY_CONVERSATION: "Qwen/Qwen2.5-7B-Instruct",
    ModelCapability.PROMPT_ENHANCEMENT: "Qwen/Qwen2.5-3B-Instruct",
    ModelCapability.CODE_GENERATION: "Qwen/Qwen2.5-Coder-7B-Instruct",
    ModelCapability.CODE_EDITING: "Qwen/Qwen2.5-Coder-7B-Instruct",
    ModelCapability.SUMMARIZATION: "Qwen/Qwen2.5-3B-Instruct",
    ModelCapability.TRANSLATION: "Qwen/Qwen2.5-3B-Instruct",
}


def get_model_for_capability(
    capability: ModelCapability,
) -> Optional[ModelSpec]:
    """
    Get the best model for a given capability.

    Args:
        capability: The capability needed

    Returns:
        ModelSpec for the best model, or None if no model found
    """
    model_path = CAPABILITY_TO_MODEL.get(capability)
    if not model_path:
        return None
    return MODEL_REGISTRY.get(model_path)


def get_primary_model() -> ModelSpec:
    """
    Get the primary conversational model.

    Returns:
        ModelSpec for the primary model
    """
    return get_model_for_capability(ModelCapability.PRIMARY_CONVERSATION)


def list_models_by_capability(
    capability: ModelCapability,
) -> list[ModelSpec]:
    """
    List all models that support a given capability.

    Args:
        capability: The capability to search for

    Returns:
        List of ModelSpecs, sorted by priority (highest first)
    """
    models = [
        spec
        for spec in MODEL_REGISTRY.values()
        if capability in spec.capabilities
    ]
    return sorted(models, key=lambda x: x.priority, reverse=True)
