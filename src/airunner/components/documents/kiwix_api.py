"""
kiwix_api.py

Provides KiwixAPI for listing available ZIM files from the Kiwix library.

"""

from typing import List, Dict, Optional
import requests
import xml.etree.ElementTree as ET

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KiwixAPI:
    """KiwixAPI fetches available ZIM files from the Kiwix Atom feed."""

    ATOM_URL = "https://browse.library.kiwix.org/catalog/v2/entries"

    @staticmethod
    def list_zim_files(
        language: Optional[str] = None, query: Optional[str] = None
    ) -> List[Dict]:
        """List available ZIM files from the Kiwix Atom feed.

        Args:
            language (Optional[str]): Language code to filter results.
            query (Optional[str]): Search query string.

        Returns:
            List[Dict]: List of ZIM file metadata dicts.
        """
        params = {}
        if language:
            params["lang"] = language
        if query:
            params["q"] = query
        try:
            resp = requests.get(KiwixAPI.ATOM_URL, params=params, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "opds": "https://specs.opds.io/opds-1.2",
                "dc": "http://purl.org/dc/terms/",
            }
            entries = []
            for entry in root.findall("atom:entry", ns):
                zim = {
                    "id": entry.findtext("atom:id", default="", namespaces=ns),
                    "title": entry.findtext(
                        "atom:title", default="", namespaces=ns
                    ),
                    "summary": entry.findtext(
                        "atom:summary", default="", namespaces=ns
                    ),
                    "updated": entry.findtext(
                        "atom:updated", default="", namespaces=ns
                    ),
                    "name": entry.findtext(
                        "atom:name", default="", namespaces=ns
                    ),
                    "category": entry.findtext(
                        "atom:category", default="", namespaces=ns
                    ),
                }
                # Find image/illustration
                img_link = entry.find(
                    "atom:link[@rel='http://opds-spec.org/image/thumbnail']",
                    ns,
                )
                if img_link is not None and "href" in img_link.attrib:
                    zim["image_url"] = img_link.attrib["href"]
                # Find ZIM download link
                zim_url = None
                for link in entry.findall("atom:link", ns):
                    rel = link.attrib.get("rel", "")
                    href = link.attrib.get("href", "")
                    if (
                        rel == "http://opds-spec.org/acquisition/open-access"
                        and href.endswith(".meta4")
                    ):
                        zim_url = href[:-6]  # Remove .meta4 only
                        break
                if zim_url:
                    zim["url"] = zim_url
                entries.append(zim)
            return entries
        except Exception as e:
            logger.error(f"Failed to fetch or parse Kiwix Atom feed: {e}")
            return []
