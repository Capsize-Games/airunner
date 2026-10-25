"""Geolocation endpoint — resolves ZIP codes to lat/lon.

The ZCTA data file is expected to live in
``{AIRUNNER_BASE_PATH}/map/2024_Gaz_zcta_national.txt``.
"""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from airunner_common.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

_ZCTA_PATH = os.path.join(
    os.path.expanduser(str(AIRUNNER_BASE_PATH)),
    "map",
    "2024_Gaz_zcta_national.txt",
)

#: Accept 5-digit ZIPs with an optional ZIP+4 suffix.
ZIPCODE_RE = re.compile(r"^\d{5}(-\d{4})?$")


class GeolocationResponse(BaseModel):
    """Lat/lon resolved from a ZIP code."""

    zipcode: str
    lat: float | None = None
    lon: float | None = None
    display_name: str | None = None


def normalize_zipcode(zipcode: str) -> str:
    """Return the 5-digit ZIP, or raise when the input is not a ZIP."""
    if not isinstance(zipcode, str) or not ZIPCODE_RE.match(
        zipcode.strip()
    ):
        raise ValueError(f"Invalid ZIP code: {zipcode!r}")
    return zipcode.strip()[:5]


@lru_cache(maxsize=1)
def _load_zcta_frame() -> pd.DataFrame | None:
    """Load the ZCTA table once per process instead of per request."""
    if not os.path.exists(_ZCTA_PATH):
        logger.error("ZCTA file not found: %s", _ZCTA_PATH)
        return None
    try:
        df = pd.read_csv(_ZCTA_PATH, sep="\t", dtype={"GEOID": str})
    except Exception as exc:
        logger.exception("Error reading ZCTA file: %s", exc)
        return None
    df.columns = df.columns.str.strip()
    return df


@router.get("/geolocation/{zipcode}", response_model=GeolocationResponse)
async def geolocate_zip(zipcode: str) -> GeolocationResponse:
    """Return latitude and longitude for one US ZIP code."""
    try:
        normalized = normalize_zipcode(zipcode)
    except ValueError:
        return GeolocationResponse(zipcode=zipcode)
    result = GeolocationResponse(zipcode=zipcode)
    df = _load_zcta_frame()
    if df is None:
        return result
    try:
        row = df[df["GEOID"] == normalized]
        if row.empty:
            return result
        row_data = row.iloc[0]
        result.lat = float(row_data["INTPTLAT"])
        result.lon = float(row_data["INTPTLONG"])
        result.display_name = f"ZCTA {normalized}"
    except Exception as exc:
        logger.exception("Error resolving ZIP code: %s", exc)
    return result
