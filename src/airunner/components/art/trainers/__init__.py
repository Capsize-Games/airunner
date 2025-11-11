"""Training utilities for diffusion models.

This package provides trainer classes that can be used from the command line
or imported and executed in a background thread inside the GUI.

Modules:
- base: Common config, base class, logging helpers.
- datasets: Simple image+caption dataset loaders for folder-based data.
- finetune: Full or UNet-only fine-tuning trainer.
- textual_inversion: Trainer for learnable token embeddings.
"""

from airunner.components.art.trainers.base import TrainingConfig, BaseTrainer
from airunner.components.art.trainers.finetune import SDTextToImageTrainer
from airunner.components.art.trainers.textual_inversion import (
    TextualInversionTrainer,
)

__all__ = [
    "TrainingConfig",
    "BaseTrainer",
    "SDTextToImageTrainer",
    "TextualInversionTrainer",
]
