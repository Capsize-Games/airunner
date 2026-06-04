"""Loader operations mixin for dataset manager."""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from ..dataset_manager import DatasetManager

logger = logging.getLogger(__name__)


class DatasetLoaderMixin:
    """Handles loading datasets from cached files."""

    def load_parquet(self: "DatasetManager", path: Path) -> pd.DataFrame:
        """Load a parquet file into a pandas DataFrame.

        Args:
            path: Path to parquet file

        Returns:
            DataFrame with dataset contents
        """
        if not path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")

        logger.info(f"Loading parquet file: {path}")
        df = pd.read_parquet(path)
        logger.info(f"Loaded {len(df)} rows from {path}")
        return df

    def load_math_parquets(
        self: "DatasetManager",
        split: str = "test",
        level: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load MATH dataset parquet files.

        Args:
            split: Dataset split ('test', 'train')
            level: Optional level filter ('Level 1' through 'Level 5')

        Returns:
            Combined DataFrame from all subject files
        """
        subject_dir = self.get_dataset_path("math", split)

        if not subject_dir.exists():
            raise FileNotFoundError(
                f"MATH dataset directory not found: {subject_dir}"
            )

        parquet_files = list(subject_dir.glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files found in {subject_dir}")

        logger.info(f"Loading {len(parquet_files)} MATH parquet files")

        dfs = []
        for pq_file in parquet_files:
            df = self.load_parquet(pq_file)
            dfs.append(df)

        combined = pd.concat(dfs, ignore_index=True)

        if level and "level" in combined.columns:
            combined = combined[combined["level"] == level]
            logger.info(f"Filtered to {len(combined)} rows for {level}")

        return combined
