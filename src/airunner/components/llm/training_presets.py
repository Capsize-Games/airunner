"""Training presets for different fine-tuning scenarios."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TrainingScenario(Enum):
    """Scenarios for fine-tuning with optimized parameters."""

    QA_PAIRS = "qa_pairs"
    LONG_DOCUMENTS = "long_documents"
    AUTHOR_STYLE = "author_style"
    CONVERSATIONS = "conversations"
    NEWS_ARTICLES = "news_articles"
    CUSTOM = "custom"


@dataclass
class TrainingPreset:
    """Configuration preset for a specific training scenario."""

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


# Preset definitions optimized for each scenario
TRAINING_PRESETS = {
    TrainingScenario.QA_PAIRS: TrainingPreset(
        name="Q&A Pairs",
        description="Optimized for question-answer style training data",
        format_type="qa",
        learning_rate=2e-4,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=10,
        use_fp16=False,
        gradient_checkpointing=True,
    ),
    TrainingScenario.LONG_DOCUMENTS: TrainingPreset(
        name="Long Documents",
        description="Optimized for ebooks, manuals, and long-form content",
        format_type="long",
        learning_rate=1e-4,
        num_train_epochs=2,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=20,
        use_fp16=False,
        gradient_checkpointing=True,
    ),
    TrainingScenario.AUTHOR_STYLE: TrainingPreset(
        name="Author Style",
        description="Preserves writing style and voice from documents",
        format_type="author",
        learning_rate=1.5e-4,
        num_train_epochs=4,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=3,
        warmup_steps=15,
        use_fp16=False,
        gradient_checkpointing=True,
    ),
    TrainingScenario.CONVERSATIONS: TrainingPreset(
        name="Conversations",
        description="Optimized for chat logs and dialogue training",
        format_type="qa",
        learning_rate=2e-4,
        num_train_epochs=5,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=25,
        use_fp16=False,
        gradient_checkpointing=True,
    ),
    TrainingScenario.NEWS_ARTICLES: TrainingPreset(
        name="News Articles",
        description="Optimized for news, blog posts, and articles",
        format_type="qa",
        learning_rate=1.5e-4,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=15,
        use_fp16=False,
        gradient_checkpointing=True,
    ),
    TrainingScenario.CUSTOM: TrainingPreset(
        name="Custom",
        description="Manually configure all training parameters",
        format_type="qa",
        learning_rate=2e-4,
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        warmup_steps=0,
        use_fp16=False,
        gradient_checkpointing=True,
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
