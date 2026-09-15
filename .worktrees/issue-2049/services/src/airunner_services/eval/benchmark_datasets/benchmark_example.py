"""
Standard benchmark datasets for evaluation.

Provides loaders for industry-standard datasets:
- GSM8K: Grade school math problems
- MATH: Competition-level math problems
- HumanEval: Code generation benchmark

Uses Hugging Face datasets library for easy access.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BenchmarkExample:
    """Single example from a benchmark dataset."""

    prompt: str
    reference_output: str
    category: str
    difficulty: str
    metadata: Dict[str, Any]
    answer: Optional[str] = None  # Extracted numeric/short answer
