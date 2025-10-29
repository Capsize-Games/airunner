"""
Standard benchmark datasets for evaluation.

Provides loaders for industry-standard datasets:
- GSM8K: Grade school math problems
- MATH: Competition-level math problems
- HumanEval: Code generation benchmark

Uses Hugging Face datasets library for easy access.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkExample:
    """Single example from a benchmark dataset."""

    prompt: str
    reference_output: str
    category: str
    difficulty: str
    metadata: Dict[str, Any]
    answer: Optional[str] = None  # Extracted numeric/short answer


def extract_numeric_answer(text: str) -> Optional[str]:
    """Extract numeric answer from text.

    Looks for patterns like:
    - "#### 42" (GSM8K format)
    - "The answer is 42"
    - "= 42"
    - Final number in text

    Args:
        text: Text containing answer

    Returns:
        Extracted numeric answer or None
    """
    # GSM8K format: #### answer
    gsm8k_match = re.search(r"####\s*(-?[\d,]+\.?\d*)", text)
    if gsm8k_match:
        return gsm8k_match.group(1).replace(",", "")

    # "The answer is X" format
    answer_is_match = re.search(
        r"(?:the answer is|answer:)\s*(-?[\d,]+\.?\d*)",
        text,
        re.IGNORECASE,
    )
    if answer_is_match:
        return answer_is_match.group(1).replace(",", "")

    # "= X" format
    equals_match = re.search(r"=\s*(-?[\d,]+\.?\d*)(?:\s|$)", text)
    if equals_match:
        return equals_match.group(1).replace(",", "")

    # Last number in text (fallback)
    numbers = re.findall(r"-?[\d,]+\.?\d*", text)
    if numbers:
        return numbers[-1].replace(",", "")

    return None


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison.

    Args:
        answer: Answer string

    Returns:
        Normalized answer (lowercase, stripped, no punctuation)
    """
    # Remove commas from numbers
    answer = answer.replace(",", "")
    # Lowercase
    answer = answer.lower().strip()
    # Remove trailing periods
    answer = answer.rstrip(".")
    # Remove dollar signs, percent signs
    answer = answer.replace("$", "").replace("%", "")
    return answer


class GSM8KDataset:
    """GSM8K (Grade School Math 8K) dataset.

    8,000+ grade school math word problems requiring multi-step reasoning.
    Each problem has a question and a solution with step-by-step reasoning
    ending with #### followed by the numeric answer.

    Example:
        Question: "Janet's ducks lay 16 eggs per day..."
        Answer: "...#### 18"
    """

    @staticmethod
    def load_sample(
        split: str = "test",
        num_samples: int = 100,
        seed: int = 42,
    ) -> List[BenchmarkExample]:
        """Load sample from GSM8K dataset.

        Args:
            split: Dataset split ('test', 'train')
            num_samples: Number of samples to load
            seed: Random seed for sampling

        Returns:
            List of BenchmarkExample instances
        """
        try:
            from datasets import load_dataset
        except ImportError:
            logger.warning(
                "datasets library not installed. "
                "Install with: pip install datasets"
            )
            return GSM8KDataset._get_fallback_samples()

        try:
            dataset = load_dataset("openai/gsm8k", "main", split=split)
            # Sample randomly
            if len(dataset) > num_samples:
                dataset = dataset.shuffle(seed=seed).select(range(num_samples))

            examples = []
            for item in dataset:
                question = item["question"]
                answer_text = item["answer"]
                numeric_answer = extract_numeric_answer(answer_text)

                examples.append(
                    BenchmarkExample(
                        prompt=question,
                        reference_output=answer_text,
                        category="math_gsm8k",
                        difficulty="grade_school",
                        answer=numeric_answer,
                        metadata={
                            "dataset": "gsm8k",
                            "split": split,
                        },
                    )
                )

            logger.info(f"Loaded {len(examples)} GSM8K examples")
            return examples

        except Exception as e:
            logger.error(f"Error loading GSM8K dataset: {e}")
            return GSM8KDataset._get_fallback_samples()

    @staticmethod
    def _get_fallback_samples() -> List[BenchmarkExample]:
        """Get hardcoded fallback samples when dataset can't be loaded."""
        return [
            BenchmarkExample(
                prompt="Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?",
                reference_output="Janet sells 16 - 3 - 4 = 9 duck eggs a day.\nShe makes 9 * 2 = $18 every day at the farmer's market.\n#### 18",
                category="math_gsm8k",
                difficulty="grade_school",
                answer="18",
                metadata={"dataset": "gsm8k", "split": "fallback"},
            ),
            BenchmarkExample(
                prompt="A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?",
                reference_output="It takes 2/2=1 bolt of white fiber\nSo the total amount of fabric is 2+1=3 bolts of fiber\n#### 3",
                category="math_gsm8k",
                difficulty="grade_school",
                answer="3",
                metadata={"dataset": "gsm8k", "split": "fallback"},
            ),
            BenchmarkExample(
                prompt="Josh decides to try flipping a house. He buys a house for $80,000 and then puts in $50,000 in repairs. This increased the value of the house by 150%. How much profit did he make?",
                reference_output="The cost of the house and repairs came out to 80,000+50,000=$130,000\nHe increased the value of the house by 80,000*1.5=120,000\nSo the new value of the house is 120,000+80,000=$200,000\nSo he made a profit of 200,000-130,000=$70,000\n#### 70000",
                category="math_gsm8k",
                difficulty="grade_school",
                answer="70000",
                metadata={"dataset": "gsm8k", "split": "fallback"},
            ),
        ]


class MATHDataset:
    """MATH dataset (competition-level mathematics).

    12,500 competition mathematics problems from AMC, AIME, and other
    contests. Problems are categorized by type (Algebra, Geometry, etc.)
    and difficulty level (1-5).

    Recommended to use 'math_oai' subset which is the OpenAI test set.
    """

    @staticmethod
    def load_sample(
        split: str = "test",
        num_samples: int = 50,
        level: Optional[str] = None,
        subject: Optional[str] = None,
        seed: int = 42,
    ) -> List[BenchmarkExample]:
        """Load sample from MATH dataset.

        Args:
            split: Dataset split ('test', 'train')
            num_samples: Number of samples to load
            level: Filter by difficulty level ('Level 1' through 'Level 5')
            subject: Filter by subject (
                'Algebra', 'Counting & Probability', 'Geometry',
                'Intermediate Algebra', 'Number Theory',
                'Prealgebra', 'Precalculus'
            )
            seed: Random seed for sampling

        Returns:
            List of BenchmarkExample instances
        """
        try:
            from datasets import load_dataset
        except ImportError:
            logger.warning(
                "datasets library not installed. "
                "Install with: pip install datasets"
            )
            return MATHDataset._get_fallback_samples()

        try:
            dataset = load_dataset("lighteval/MATH", split=split)

            # Filter by level/subject if specified
            if level:
                dataset = dataset.filter(lambda x: x["level"] == level)
            if subject:
                dataset = dataset.filter(lambda x: x["type"] == subject)

            # Sample randomly
            if len(dataset) > num_samples:
                dataset = dataset.shuffle(seed=seed).select(range(num_samples))

            examples = []
            for item in dataset:
                problem = item["problem"]
                solution = item["solution"]
                answer = item.get("answer", "")
                level_str = item.get("level", "unknown")
                subject_str = item.get("type", "unknown")

                examples.append(
                    BenchmarkExample(
                        prompt=problem,
                        reference_output=solution,
                        category="math_competition",
                        difficulty=level_str,
                        answer=answer,
                        metadata={
                            "dataset": "MATH",
                            "split": split,
                            "level": level_str,
                            "subject": subject_str,
                        },
                    )
                )

            logger.info(f"Loaded {len(examples)} MATH examples")
            return examples

        except Exception as e:
            logger.error(f"Error loading MATH dataset: {e}")
            return MATHDataset._get_fallback_samples()

    @staticmethod
    def _get_fallback_samples() -> List[BenchmarkExample]:
        """Get hardcoded fallback samples when dataset can't be loaded."""
        return [
            BenchmarkExample(
                prompt="What is the greatest common divisor of 12 and 18?",
                reference_output="The factors of 12 are 1, 2, 3, 4, 6, and 12. The factors of 18 are 1, 2, 3, 6, 9, and 18. The greatest common divisor is 6.",
                category="math_competition",
                difficulty="Level 1",
                answer="6",
                metadata={
                    "dataset": "MATH",
                    "split": "fallback",
                    "level": "Level 1",
                    "subject": "Number Theory",
                },
            ),
            BenchmarkExample(
                prompt="Solve for x: x^2 - 5x + 6 = 0",
                reference_output="We can factor this as (x-2)(x-3) = 0. Therefore x = 2 or x = 3.",
                category="math_competition",
                difficulty="Level 2",
                answer="2, 3",
                metadata={
                    "dataset": "MATH",
                    "split": "fallback",
                    "level": "Level 2",
                    "subject": "Algebra",
                },
            ),
        ]


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
        try:
            from datasets import load_dataset
        except ImportError:
            logger.warning(
                "datasets library not installed. "
                "Install with: pip install datasets"
            )
            return HumanEvalDataset._get_fallback_samples()

        try:
            dataset = load_dataset("openai/openai_humaneval", split="test")

            # Sample randomly
            if len(dataset) > num_samples:
                dataset = dataset.shuffle(seed=seed).select(range(num_samples))

            examples = []
            for item in dataset:
                prompt = item["prompt"]
                canonical_solution = item["canonical_solution"]
                test_code = item["test"]
                entry_point = item["entry_point"]

                # Combine prompt and test for reference
                reference = (
                    f"Solution:\n{canonical_solution}\n\n"
                    f"Tests:\n{test_code}"
                )

                examples.append(
                    BenchmarkExample(
                        prompt=prompt,
                        reference_output=reference,
                        category="code_generation",
                        difficulty="medium",
                        answer=canonical_solution,
                        metadata={
                            "dataset": "HumanEval",
                            "entry_point": entry_point,
                            "test_code": test_code,
                        },
                    )
                )

            logger.info(f"Loaded {len(examples)} HumanEval examples")
            return examples

        except Exception as e:
            logger.error(f"Error loading HumanEval dataset: {e}")
            return HumanEvalDataset._get_fallback_samples()

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


# Convenience functions for loading datasets
def load_gsm8k(
    num_samples: int = 100, split: str = "test", seed: int = 42
) -> List[BenchmarkExample]:
    """Load GSM8K dataset.

    Args:
        num_samples: Number of samples
        split: Dataset split
        seed: Random seed

    Returns:
        List of examples
    """
    return GSM8KDataset.load_sample(
        split=split, num_samples=num_samples, seed=seed
    )


def load_math(
    num_samples: int = 50,
    split: str = "test",
    level: Optional[str] = None,
    subject: Optional[str] = None,
    seed: int = 42,
) -> List[BenchmarkExample]:
    """Load MATH dataset.

    Args:
        num_samples: Number of samples
        split: Dataset split
        level: Difficulty level filter
        subject: Subject filter
        seed: Random seed

    Returns:
        List of examples
    """
    return MATHDataset.load_sample(
        split=split,
        num_samples=num_samples,
        level=level,
        subject=subject,
        seed=seed,
    )


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
