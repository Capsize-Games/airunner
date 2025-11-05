
import re
from typing import List, Optional
from airunner.components.eval.benchmark_datasets.benchmark_example import BenchmarkExample
from airunner.components.eval.dataset_manager import DatasetManager
from airunner.utils.application import get_logger


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
            examples = MATHDataset._load_from_parquet(
                split, num_samples, level, subject, seed
            )
            logger = get_logger(__name__)
            logger.info(f"Loaded {len(examples)} MATH examples from parquet")
            return examples

        except Exception as e:
            logger.error(f"Error loading MATH dataset: {e}")
            logger.exception("Full traceback:")
            return MATHDataset._get_fallback_samples()

    @staticmethod
    def _load_from_parquet(
        split: str,
        num_samples: int,
        level: Optional[str],
        subject: Optional[str],
        seed: int,
    ) -> List[BenchmarkExample]:
        """Load MATH data from parquet files."""
        manager = DatasetManager()
        manager.ensure_dataset("math", split=split)
        df = manager.load_math_parquets(split=split, level=level)

        if subject and "type" in df.columns:
            df = df[df["type"] == subject]

        if len(df) > num_samples:
            df = df.sample(n=num_samples, random_state=seed)

        return MATHDataset._create_examples_from_df(df, split)

    @staticmethod
    def _extract_boxed_answer(solution: str) -> str:
        """Extract answer from \boxed{} pattern in solution."""
        boxed_matches = list(re.finditer(r"\\boxed\{", solution))
        if not boxed_matches:
            return ""

        last_match = boxed_matches[-1]
        start = last_match.end()
        depth = 1
        i = start
        while i < len(solution) and depth > 0:
            if solution[i] == "{":
                depth += 1
            elif solution[i] == "}":
                depth -= 1
            i += 1
        if depth == 0:
            return solution[start : i - 1]
        return ""

    @staticmethod
    def _create_examples_from_df(df, split: str) -> List[BenchmarkExample]:
        """Create BenchmarkExample instances from dataframe."""
        examples = []
        for _, row in df.iterrows():
            problem = row["problem"]
            solution = row["solution"]
            answer = row.get("answer", "")

            if not answer and solution:
                answer = MATHDataset._extract_boxed_answer(solution)

            level_str = row.get("level", "unknown")
            subject_str = row.get("type", "unknown")

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
        return examples

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

