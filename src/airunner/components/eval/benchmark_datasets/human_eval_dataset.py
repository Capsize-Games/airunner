from typing import Dict, List
from airunner.components.eval.benchmark_datasets.benchmark_example import (
    BenchmarkExample,
)
from airunner.utils.application import get_logger

try:
    from datasets import load_dataset
except ImportError:
    load_dataset = None


class HumanEvalDataset:
    """HumanEval code generation benchmark.

    164 hand-written programming problems with function signatures,
    docstrings, and test cases. Used to evaluate code generation
    capabilities.
    """

    @staticmethod
    def load_sample(
        num_samples: int = 20,
        seed: int = 42,
    ) -> List[BenchmarkExample]:
        """Load sample from HumanEval dataset.

        Args:
            num_samples: Number of samples to load
            seed: Random seed for sampling

        Returns:
            List of BenchmarkExample instances
        """
        logger = get_logger(__name__)
        if load_dataset is None:
            logger.warning(
                "datasets library not installed. "
                "Install with: pip install datasets"
            )
            return HumanEvalDataset._get_fallback_samples()

        try:
            dataset = load_dataset("openai/openai_humaneval", split="test")
            examples = HumanEvalDataset._create_examples_from_dataset(
                dataset, num_samples, seed
            )
            logger.info(f"Loaded {len(examples)} HumanEval examples")
            return examples

        except Exception as e:
            logger.error(f"Error loading HumanEval dataset: {e}")
            return HumanEvalDataset._get_fallback_samples()

    @staticmethod
    def _create_examples_from_dataset(
        dataset, num_samples: int, seed: int
    ) -> List[BenchmarkExample]:
        """Create examples from HuggingFace dataset."""
        if len(dataset) > num_samples:
            dataset = dataset.shuffle(seed=seed).select(range(num_samples))

        examples = []
        for item in dataset:
            reference = HumanEvalDataset._format_reference(item)
            examples.append(
                BenchmarkExample(
                    prompt=item["prompt"],
                    reference_output=reference,
                    category="code_generation",
                    difficulty="medium",
                    answer=item["canonical_solution"],
                    metadata={
                        "dataset": "HumanEval",
                        "entry_point": item["entry_point"],
                        "test_code": item["test"],
                    },
                )
            )
        return examples

    @staticmethod
    def _format_reference(item: Dict) -> str:
        """Format reference output from dataset item."""
        return (
            f"Solution:\n{item['canonical_solution']}\n\n"
            f"Tests:\n{item['test']}"
        )

    @staticmethod
    def _get_fallback_samples() -> List[BenchmarkExample]:
        """Get hardcoded fallback samples when dataset can't be loaded."""
        return [
            BenchmarkExample(
                prompt='def has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n',
                reference_output="Solution:\n    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n            if idx != idx2:\n                distance = abs(elem - elem2)\n                if distance < threshold:\n                    return True\n    return False\n\nTests:\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False",
                category="code_generation",
                difficulty="medium",
                answer="    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n            if idx != idx2:\n                distance = abs(elem - elem2)\n                if distance < threshold:\n                    return True\n    return False",
                metadata={
                    "dataset": "HumanEval",
                    "entry_point": "has_close_elements",
                    "test_code": "def check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True",
                },
            )
        ]


def load_humaneval(
    num_samples: int = 20, seed: int = 42
) -> List[BenchmarkExample]:
    """Load HumanEval dataset.

    Args:
        num_samples: Number of samples
        seed: Random seed

    Returns:
        List of examples
    """
    return HumanEvalDataset.load_sample(num_samples=num_samples, seed=seed)
