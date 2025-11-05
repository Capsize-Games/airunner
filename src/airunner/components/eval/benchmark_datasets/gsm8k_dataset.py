from typing import List
from airunner.components.eval.benchmark_datasets import extract_numeric_answer
from airunner.components.eval.benchmark_datasets.benchmark_example import (
    BenchmarkExample,
)
from airunner.components.eval.dataset_manager import DatasetManager
from airunner.utils.application import get_logger


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
        logger = get_logger(__name__)
        try:
            examples = GSM8KDataset._load_from_parquet(
                split, num_samples, seed
            )
            logger.info(f"Loaded {len(examples)} GSM8K examples from parquet")
            return examples

        except Exception as e:
            logger.error(f"Error loading GSM8K dataset: {e}")
            logger.exception("Full traceback:")
            return GSM8KDataset._get_fallback_samples()

    @staticmethod
    def _load_from_parquet(
        split: str, num_samples: int, seed: int
    ) -> List[BenchmarkExample]:
        """Load GSM8K data from parquet files."""
        manager = DatasetManager()
        parquet_path = manager.ensure_dataset("gsm8k", split=split)
        df = manager.load_parquet(parquet_path)

        if len(df) > num_samples:
            df = df.sample(n=num_samples, random_state=seed)

        return GSM8KDataset._create_examples_from_df(df, split)

    @staticmethod
    def _create_examples_from_df(df, split: str) -> List[BenchmarkExample]:
        """Create BenchmarkExample instances from dataframe."""
        examples = []
        for _, row in df.iterrows():
            question = row["question"]
            answer_text = row["answer"]
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
        return examples

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
