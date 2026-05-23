"""
CivitAIAPI: Interface for interacting with the CivitAI REST API.

See: https://github.com/civitai/civitai/wiki/REST-API-Reference
"""

import re
import requests
from typing import Any, Dict, Optional


class CivitAIAPI:
    """CivitAI API client for model info and downloads."""

    BASE_API_URL = "https://civitai.com/api/v1/models/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @staticmethod
    def parse_url(url: str) -> Dict[str, Any]:
        """Extract model_id and modelVersionId from a civitai.com URL."""
        # Example: https://civitai.com/models/995002/70s-sci-fi-movie?modelVersionId=1880417
        model_id = None
        model_version_id = None
        m = re.search(r"/models/(\d+)", url)
        if m:
            model_id = m.group(1)
        m2 = re.search(r"modelVersionId=(\d+)", url)
        if m2:
            model_version_id = m2.group(1)
        return {"model_id": model_id, "model_version_id": model_version_id}

    def get_model_info(self, url: str) -> Dict[str, Any]:
        """Query the CivitAI API for model info given a civitai.com URL."""
        ids = self.parse_url(url)
        model_id = ids["model_id"]
        if not model_id:
            raise ValueError("Invalid CivitAI model URL")
        api_url = f"{self.BASE_API_URL}{model_id}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            # Some clients expect the API token as a query parameter. Include it
            # in the URL for compatibility with tests and external callers.
            sep = "&" if "?" in api_url else "?"
            api_url = f"{api_url}{sep}token={self.api_key}"
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Optionally filter for a specific version
        if ids["model_version_id"]:
            for v in data.get("modelVersions", []):
                if str(v.get("id")) == ids["model_version_id"]:
                    data["selectedVersion"] = v
                    break
        return data
