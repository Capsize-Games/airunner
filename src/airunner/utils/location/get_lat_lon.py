"""Location utilities for latitude/longitude lookup by ZIP code using a local CSV/TSV file.

This module provides a function to get latitude and longitude for a US ZIP code using a pandas DataFrame loaded from a local file (2024_Gaz_zcta_national.txt).

The file is expected to be a tab-delimited file with columns: 'GEOID', 'INTPTLAT', 'INTPTLONG'.

Returns a dict with keys 'lat', 'lon', and 'row', or all None if not found.
"""

import os
from typing import Optional, Any, Dict

import pandas as pd

from airunner.components.settings.data.path_settings import PathSettings
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_lat_lon(
    zipcode: str, country_code: str = "US"
) -> Dict[str, Optional[Any]]:
    """Get latitude and longitude for a ZIP code using a local ZCTA file.

    Args:
        zipcode (str): ZIP code as a string (5 digits).
        country_code (str): Country code (default: 'US').

    Returns:
        dict: Dictionary with keys 'lat', 'lon', and 'row'. Values are float or None.
    """
    path_settings = PathSettings.objects.first()
    path = os.path.join(
        path_settings.base_path, "map", "2024_Gaz_zcta_national.txt"
    )
    res: Dict[str, Optional[Any]] = {"lat": None, "lon": None, "row": None}
    if not os.path.exists(path):
        logger.error(f"ZCTA file not found: {path}")
        return res
    try:
        df = pd.read_csv(path, sep="\t", dtype={"GEOID": str})
        df.columns = (
            df.columns.str.strip()
        )  # Strip whitespace from column names
        row = df[df["GEOID"] == zipcode]
        if row.empty:
            return res
        row_data = row.iloc[0]
        res["lat"] = float(row_data["INTPTLAT"])
        res["lon"] = float(row_data["INTPTLONG"])
        res["row"] = row_data
    except Exception as e:
        logger.exception(f"Error reading or parsing file {path}: {e}")
    return res
