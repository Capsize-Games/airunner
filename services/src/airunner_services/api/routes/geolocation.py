"""Geolocation endpoint — resolves ZIP codes to lat/lon.

The ZCTA data file is expected to live in
``{AIRUNNER_BASE_PATH}/map/2024_Gaz_zcta_national.txt``.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

_ZCTA_PATH = os.path.join(
    os.path.expanduser(str(AIRUNNER_BASE_PATH)),
    "map",
    "2024_Gaz_zcta_national.txt",
)


class GeolocationResponse(BaseModel):
    """Lat/lon resolved from a ZIP code."""

    zipcode: str
    lat: float | None = None
    lon: float | None = None
    display_name: str | None = None


@router.get("/geolocation/{zipcode}", response_model=GeolocationResponse)
async def geolocate_zip(zipcode: str) -> GeolocationResponse:
    """Return latitude and longitude for one US ZIP code."""
    result = GeolocationResponse(zipcode=zipcode)
    if not os.path.exists(_ZCTA_PATH):
        logger.error("ZCTA file not found: %s", _ZCTA_PATH)
        return result
    try:
        df = pd.read_csv(_ZCTA_PATH, sep="\t", dtype={"GEOID": str})
        df.columns = df.columns.str.strip()
        row = df[df["GEOID"] == zipcode]
        if row.empty:
            return result
        row_data = row.iloc[0]
        result.lat = float(row_data["INTPTLAT"])
        result.lon = float(row_data["INTPTLONG"])
        result.display_name = str(row_data.to_dict())
    except Exception as exc:
        logger.exception("Error reading ZCTA file: %s", exc)
    return result
