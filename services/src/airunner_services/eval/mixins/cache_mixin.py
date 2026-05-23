"""Cache management mixin for dataset operations."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..dataset_manager import DatasetManager


class DatasetCacheMixin:
    """Handles dataset caching and path management."""

    def get_dataset_path(
        self: "DatasetManager", dataset_name: str, split: str = "test"
    ) -> Path:
        """Get the local path where dataset file should be stored.

        Args:
            dataset_name: Name of dataset ('gsm8k', 'math')
            split: Dataset split ('test', 'train')

        Returns:
            Path to dataset file
        """
        if dataset_name == "gsm8k":
            filename = self.DATASETS["gsm8k"]["files"][split]
            filename = filename.split("/")[-1]
            return self.cache_dir / "gsm8k" / filename
        elif dataset_name == "math":
            return self.cache_dir / "math" / split
        else:
            raise ValueError(f"Unknown dataset: {dataset_name}")

    def is_dataset_cached(
        self: "DatasetManager", dataset_name: str, split: str = "test"
    ) -> bool:
        """Check if dataset is already downloaded.

        Args:
            dataset_name: Name of dataset ('gsm8k', 'math')
            split: Dataset split ('test', 'train')

        Returns:
            True if dataset exists locally
        """
        if dataset_name == "gsm8k":
            path = self.get_dataset_path(dataset_name, split)
            return path.exists()
        elif dataset_name == "math":
            path = self.get_dataset_path(dataset_name, split)
            if not path.exists():
                return False
            parquet_files = list(path.glob("*.parquet"))
            return len(parquet_files) > 0
        return False
