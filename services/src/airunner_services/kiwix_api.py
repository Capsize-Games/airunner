"""Service-owned Kiwix catalog helpers."""

from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.url_safety import safe_fetch_url
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KiwixAPI:
    """Fetch available ZIM archives from the Kiwix catalog."""

    ATOM_URL = "https://browse.library.kiwix.org/catalog/v2/entries"

    @staticmethod
    def list_zim_files(
        language: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Return Kiwix catalog entries filtered by language or query."""
        params: dict[str, str] = {}
        if language:
            params["lang"] = language
        if query:
            params["q"] = query

        url = KiwixAPI.ATOM_URL
        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            response_text = safe_fetch_url(url, timeout_seconds=15)
            root = ET.fromstring(response_text)
            return KiwixAPI._parse_entries(root)
        except Exception as error:
            logger.error(
                "Failed to fetch or parse Kiwix Atom feed: %s",
                error,
            )
            return []

    @staticmethod
    def _parse_entries(root: ET.Element) -> List[Dict[str, str]]:
        """Parse one Atom feed payload into Kiwix entry dictionaries."""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "opds": "https://specs.opds.io/opds-1.2",
            "dc": "http://purl.org/dc/terms/",
        }
        entries: list[dict[str, str]] = []
        for entry in root.findall("atom:entry", ns):
            zim = {
                "id": entry.findtext("atom:id", default="", namespaces=ns),
                "title": entry.findtext(
                    "atom:title",
                    default="",
                    namespaces=ns,
                ),
                "summary": entry.findtext(
                    "atom:summary",
                    default="",
                    namespaces=ns,
                ),
                "updated": entry.findtext(
                    "atom:updated",
                    default="",
                    namespaces=ns,
                ),
                "name": entry.findtext(
                    "atom:name",
                    default="",
                    namespaces=ns,
                ),
                "category": entry.findtext(
                    "atom:category",
                    default="",
                    namespaces=ns,
                ),
            }
            image_link = entry.find(
                "atom:link[@rel='http://opds-spec.org/image/thumbnail']",
                ns,
            )
            if image_link is not None and "href" in image_link.attrib:
                zim["image_url"] = image_link.attrib["href"]

            zim_url = None
            for link in entry.findall("atom:link", ns):
                rel = link.attrib.get("rel", "")
                href = link.attrib.get("href", "")
                if (
                    rel == "http://opds-spec.org/acquisition/open-access"
                    and href.endswith(".meta4")
                ):
                    zim_url = href[:-6]
                    break
            if zim_url:
                zim["url"] = zim_url

            entries.append(zim)
        return entries


__all__ = ["KiwixAPI"]