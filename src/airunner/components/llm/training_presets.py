"""
Training presets for LoRA fine-tuning focused on STYLE adaptation.

LoRA adapters are designed to learn:
- Writing style and tone
- Response patterns
- Domain-specific vocabulary
- Linguistic patterns

For FACTUAL knowledge, use RAG instead of fine-tuning.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class TrainingScenario(Enum):
    """Scenarios for style-focused LoRA fine-tuning."""

    AUTHOR_STYLE = "author_style"
    CONVERSATIONAL_TONE = "conversational_tone"
    DOMAIN_VOCABULARY = "domain_vocabulary"
    RESPONSE_FORMAT = "response_format"
    CUSTOM = "custom"


@dataclass
class TrainingPreset:
    """Configuration preset for LoRA style training."""

    name: str
    description: str
    format_type: str
    learning_rate: float
    num_train_epochs: int
    per_device_train_batch_size: int
    gradient_accumulation_steps: int
    warmup_steps: int
    use_fp16: bool
    gradient_checkpointing: bool
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: Optional[List[str]] = None


# Preset definitions optimized for style learning (NOT factual memorization)
TRAINING_PRESETS = {
    TrainingScenario.AUTHOR_STYLE: TrainingPreset(
        name="Author Writing Style",
        description="Learn writing style, tone, sentence structure, and voice from documents. Use for mimicking specific authors.",
        format_type="completion",
        learning_rate=5e-4,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        use_fp16=False,
        gradient_checkpointing=True,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "o_proj"],
    ),
    TrainingScenario.CONVERSATIONAL_TONE: TrainingPreset(
        name="Conversational Tone",
        description="Adapt response personality and tone from conversation examples. Use for formal/casual/empathetic styles.",
        format_type="chat",
        learning_rate=3e-4,
        num_train_epochs=5,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=15,
        use_fp16=False,
        gradient_checkpointing=True,
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj"],
    ),
    TrainingScenario.DOMAIN_VOCABULARY: TrainingPreset(
        name="Domain-Specific Language",
        description="Learn specialized vocabulary and phrasing for a domain (medical, legal, technical). Higher rank for vocabulary.",
        format_type="completion",
        learning_rate=2e-4,
        num_train_epochs=8,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=20,
        use_fp16=False,
        gradient_checkpointing=True,
        lora_r=32,
        lora_alpha=64,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "gate_proj", "up_proj"],
    ),
    TrainingScenario.RESPONSE_FORMAT: TrainingPreset(
        name="Response Format",
        description="Learn specific response formats (code style, documentation format, structured output). Lightweight adapter.",
        format_type="chat",
        learning_rate=4e-4,
        num_train_epochs=4,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=10,
        use_fp16=False,
        gradient_checkpointing=True,
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
    ),
    TrainingScenario.CUSTOM: TrainingPreset(
        name="Custom",
        description="Manually configure all training parameters for experimental setups.",
        format_type="completion",
        learning_rate=2e-4,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        warmup_steps=0,
        use_fp16=False,
        gradient_checkpointing=True,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    ),
}


def get_preset(scenario: TrainingScenario) -> TrainingPreset:
    """Get preset configuration for a training scenario."""
    return TRAINING_PRESETS.get(
        scenario, TRAINING_PRESETS[TrainingScenario.CUSTOM]
    )


def get_preset_by_name(name: str) -> Optional[TrainingPreset]:
    """Get preset by name string."""
    for scenario, preset in TRAINING_PRESETS.items():
        if preset.name == name:
            return preset
    return None


def get_scenario_by_name(name: str) -> Optional[TrainingScenario]:
    """Get scenario enum by preset name."""
    for scenario, preset in TRAINING_PRESETS.items():
        if preset.name == name:
            return scenario
    return None
