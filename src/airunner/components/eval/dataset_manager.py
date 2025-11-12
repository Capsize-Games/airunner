"""
Dataset manager for downloading and caching evaluation datasets.

Uses direct HTTP downloads to fetch dataset files from HuggingFace as
parquet files, bypassing the datasets library's cache system and avoiding
any Qt/GUI dependencies.
"""

import os
from pathlib import Path
from typing import Optional, Callable

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)

from .mixins import (
    DatasetCacheMixin,
    DatasetDownloadMixin,
    DatasetLoaderMixin,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_airunner_base_path(base_path: str) -> str:
    """Get AI Runner base path without initializing settings infrastructure.

    Returns:
        Base path from environment variable or default location
    """
    if "AIRUNNER_BASE_PATH" in os.environ:
        return os.environ["AIRUNNER_BASE_PATH"]

    if "XDG_DATA_HOME" in os.environ:
        return os.path.join(os.environ["XDG_DATA_HOME"], "airunner")

    return os.path.expanduser(base_path)


class DatasetManager(
    MediatorMixin,
    SettingsMixin,
    DatasetCacheMixin,
    DatasetDownloadMixin,
    DatasetLoaderMixin,
):
    """Manages downloading and loading evaluation datasets.

    Downloads datasets as parquet files from HuggingFace, avoiding the
    datasets library cache system.

    Supported datasets:
    - GSM8K: openai/gsm8k
    - MATH: EleutherAI/hendrycks_math
    """

    DATASETS = {
        "gsm8k": {
            "repo": "openai/gsm8k",
            "files": {
                "test": "main/test-00000-of-00001.parquet",
                "train": "main/train-00000-of-00001.parquet",
            },
        },
        "math": {
            "repo": "EleutherAI/hendrycks_math",
            "subjects": [
                "algebra",
                "counting_and_probability",
                "geometry",
                "intermediate_algebra",
                "number_theory",
                "prealgebra",
                "precalculus",
            ],
        },
    }

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        headless: bool = True,
    ):
        """Initialize dataset manager.

        Args:
            cache_dir: Directory to cache downloaded datasets
            headless: If True, use tqdm progress bars
        """
        super().__init__()
        self.headless = headless

        if cache_dir is None:
            base_path = get_airunner_base_path(self.path_settings.base_path)
            cache_dir = os.path.join(base_path, "text", "datasets")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DatasetManager initialized with cache_dir: {self.cache_dir}"
        )

    def ensure_dataset(
        self,
        dataset_name: str,
        split: str = "test",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Ensure dataset is downloaded, downloading if necessary.

        Args:
            dataset_name: Name of dataset ('gsm8k', 'math')
            split: Dataset split ('test', 'train')
            progress_callback: Optional progress callback(current, total)

        Returns:
            Path to dataset file or directory
        """
        if self.is_dataset_cached(dataset_name, split):
            logger.info(f"Dataset {dataset_name} ({split}) already cached")
            return self.get_dataset_path(dataset_name, split)

        logger.info(
            f"Dataset {dataset_name} ({split}) not cached, downloading..."
        )

        if dataset_name == "gsm8k":
            return self.download_gsm8k(split, progress_callback)
        elif dataset_name == "math":
            return self.download_math(
                split, progress_callback=progress_callback
            )
        else:
            raise ValueError(f"Unknown dataset: {dataset_name}")
