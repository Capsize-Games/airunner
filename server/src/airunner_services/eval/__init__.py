"""Evaluation testing framework components."""

from airunner_services.eval.client import AIRunnerClient
from airunner_services.eval.evaluators import (
    LLMAsJudge,
    create_correctness_evaluator,
    create_conciseness_evaluator,
    create_helpfulness_evaluator,
    create_relevance_evaluator,
)
from airunner_services.eval.datasets import (
    MATH_REASONING_DATASET,
    GENERAL_KNOWLEDGE_DATASET,
    SUMMARIZATION_DATASET,
    CODING_DATASET,
    INSTRUCTION_FOLLOWING_DATASET,
    REASONING_DATASET,
    get_dataset_by_category,
    get_dataset_by_difficulty,
    get_all_test_cases,
)

__all__ = [
    "AIRunnerClient",
    "LLMAsJudge",
    "create_correctness_evaluator",
    "create_conciseness_evaluator",
    "create_helpfulness_evaluator",
    "create_relevance_evaluator",
    "MATH_REASONING_DATASET",
    "GENERAL_KNOWLEDGE_DATASET",
    "SUMMARIZATION_DATASET",
    "CODING_DATASET",
    "INSTRUCTION_FOLLOWING_DATASET",
    "REASONING_DATASET",
    "get_dataset_by_category",
    "get_dataset_by_difficulty",
    "get_all_test_cases",
]
