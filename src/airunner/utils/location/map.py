from pathlib import Path
from typing import Optional, Dict
import pyrosm
import time
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def extract_geojson_from_pbf(
    pbf_path: str,
    data_types: Optional[list[str]] = None,
    cache_ttl: int = 86400,
) -> Dict[str, Optional[str]]:
    """Extracts specified data types from a PBF file and stores them as GeoJSON files, with caching.

    Args:
        pbf_path (str): Path to the PBF file.
        data_types (Optional[list[str]]): List of data types to extract. Supported: 'buildings', 'roads', 'cycling', 'walking', 'landuse', 'natural', 'pois', 'water', 'boundaries', 'places'. If None, all are extracted.
        cache_ttl (int): Cache time-to-live in seconds. Default is 86400 (24 hours).

    Returns:
        Dict[str, Optional[str]]: Dictionary with keys for each data type containing the paths to the generated GeoJSON files, or None if extraction failed.
    """
    pbf = Path(pbf_path)
    supported = [
        "buildings",
        "roads",
        "cycling",
        "walking",
        "landuse",
        "natural",
        "pois",
        "water",
        "boundaries",
        "places",
    ]
    if data_types is None:
        data_types = supported
    output = {k: None for k in data_types}
    if not pbf.exists():
        logger.error(f"PBF file not found: {pbf_path}")
        return output
    now = time.time()
    try:
        osm = pyrosm.OSM(str(pbf))
        for dtype in data_types:
            geojson_path = pbf.with_name(f"{dtype}.geojson")
            if (
                geojson_path.exists()
                and now - geojson_path.stat().st_mtime < cache_ttl
            ):
                output[dtype] = str(geojson_path)
                logger.info(f"Using cached {dtype} at {geojson_path}")
                continue
            if dtype == "buildings":
                data = osm.get_buildings()
            elif dtype == "roads":
                data = osm.get_network(network_type="driving")
            elif dtype == "cycling":
                data = osm.get_network(network_type="cycling")
            elif dtype == "walking":
                data = osm.get_network(network_type="walking")
            elif dtype == "landuse":
                data = osm.get_landuse()
            elif dtype == "natural":
                data = osm.get_natural()
            elif dtype == "pois":
                data = osm.get_pois()
            elif dtype == "water":
                data = osm.get_water()
            elif dtype == "boundaries":
                data = osm.get_boundaries()
            elif dtype == "places":
                data = osm.get_places()
            else:
                logger.warning(f"Unsupported data type: {dtype}")
                continue
            if data is not None and not data.empty:
                data.to_file(str(geojson_path), driver="GeoJSON")
                output[dtype] = str(geojson_path)
                logger.info(f"Extracted {len(data)} {dtype} to {geojson_path}")
    except Exception as e:
        logger.exception(f"Failed to extract data from {pbf_path}: {e}")
    return output


def download_and_extract(
    directory: str,
    region: str,
    data_types: Optional[list[str]] = None,
    cache_ttl: int = 86400,
) -> Dict[str, Optional[str]]:
    """Downloads a PBF file for a given region and extracts specified data types as GeoJSON, with caching.

    Args:
        directory (str): Directory to store the downloaded PBF file.
        region (str): Name of the region to download (e.g., 'Colorado').
        data_types (Optional[list[str]]): List of data types to extract. Supported: 'buildings', 'roads', 'cycling', 'walking', 'landuse', 'natural', 'pois', 'water', 'boundaries', 'places'. If None, all are extracted.
        cache_ttl (int): Cache time-to-live in seconds. Default is 86400 (24 hours).

    Returns:
        Dict[str, Optional[str]]: Dictionary with keys for each data type containing the paths to the generated GeoJSON files, or None if extraction failed.
    """
    from pathlib import Path
    import time

    try:
        pbf_path = pyrosm.get_data(region, directory=directory)
        pbf = Path(pbf_path)
        now = time.time()
        if pbf.exists() and now - pbf.stat().st_mtime < cache_ttl:
            logger.info(f"Using cached PBF for region: {region} at {pbf_path}")
        elif pbf.exists():
            logger.info(
                f"PBF for region {region} is older than cache_ttl, re-downloading..."
            )
            pbf_path = pyrosm.get_data(
                region, directory=directory, update=True
            )
        else:
            logger.info(f"Downloading PBF for region: {region}")
            pbf_path = pyrosm.get_data(region, directory=directory)
        if not pbf_path or not Path(pbf_path).exists():
            logger.error(f"Failed to download PBF for region: {region}")
            return {
                k: None
                for k in (
                    data_types
                    or [
                        "buildings",
                        "roads",
                        "cycling",
                        "walking",
                        "landuse",
                        "natural",
                        "pois",
                        "water",
                        "boundaries",
                        "places",
                    ]
                )
            }
        return extract_geojson_from_pbf(pbf_path, data_types, cache_ttl)
    except Exception as e:
        logger.exception(
            f"Failed to download and extract for region {region}: {e}"
        )
        return {
            k: None
            for k in (
                data_types
                or [
                    "buildings",
                    "roads",
                    "cycling",
                    "walking",
                    "landuse",
                    "natural",
                    "pois",
                    "water",
                    "boundaries",
                    "places",
                ]
            )
        }


def list_available_regions() -> list[str]:
    """Returns a list of all valid region names available for download via pyrosm.

    Returns:
        list[str]: List of available region names.
    """
    data = pyrosm.data.available
    return data.get("reigions", {})
