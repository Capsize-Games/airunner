"""Download and setup endpoints for the GUI daemon client."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class DownloadsClientMixin:
    """Download-related daemon API endpoints."""

    _request: Any
    _sleep: Any
    _time_fn: Any
    _poll_interval_seconds: float
    logger: Any

    # ------------------------------------------------------------------
    # Setup wizard
    # ------------------------------------------------------------------

    def start_setup(
        self,
        *,
        enabled_models: Dict[str, bool],
        base_path: str,
        prefer_pre_quantized: bool = True,
        progress_callback: Optional[
            Callable[[Dict[str, Any]], None]
        ] = None,
    ) -> None:
        """Run one daemon-backed setup install.  Progress is streamed
        via SSE events and forwarded through ``progress_callback``.
        """
        import json
        self._request_timeout_seconds
        response = self._request(
            "POST",
            "/api/v1/setup/install",
            json_payload={
                "enabled_models": enabled_models,
                "base_path": base_path,
                "prefer_pre_quantized": prefer_pre_quantized,
            },
            timeout_seconds=3600.0,
            stream=True,
        )
        for line in response.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            try:
                payload = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if progress_callback is not None:
                progress_callback(payload)

    # ------------------------------------------------------------------
    # HuggingFace downloads
    # ------------------------------------------------------------------

    def start_huggingface_file_download(
        self,
        *,
        repo_id: str,
        filename: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed single-file HuggingFace download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/huggingface/file",
            json_payload={
                "repo_id": repo_id,
                "filename": filename,
                "output_dir": output_dir,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def start_huggingface_download(
        self,
        *,
        repo_id: str,
        model_type: str = "llm",
        output_dir: Optional[str] = None,
        missing_files: Optional[list[str]] = None,
        gguf_filename: Optional[str] = None,
        prefer_pre_quantized: bool = True,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed HuggingFace model download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/huggingface",
            json_payload={
                "repo_id": repo_id,
                "model_type": model_type,
                "output_dir": output_dir,
                "missing_files": missing_files,
                "gguf_filename": gguf_filename,
                "prefer_pre_quantized": prefer_pre_quantized,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    # ------------------------------------------------------------------
    # URL / NLTK downloads
    # ------------------------------------------------------------------

    def start_url_download(
        self,
        *,
        url: str,
        output_dir: str,
        filename: Optional[str] = None,
        extract_zip: bool = False,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed generic URL download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/url",
            json_payload={
                "url": url,
                "output_dir": output_dir,
                "filename": filename,
                "extract_zip": extract_zip,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def start_nltk_download(
        self,
        *,
        data_names: list[str],
    ) -> Dict[str, Any]:
        """Queue one daemon-backed NLTK data download job."""
        response = self._request(
            "POST",
            "/api/v1/downloads/nltk",
            json_payload={"data_names": data_names},
            timeout_seconds=30.0,
        )
        return response.json()

    # ------------------------------------------------------------------
    # CivitAI
    # ------------------------------------------------------------------

    def start_civitai_file_download(
        self,
        *,
        url: str,
        output_path: str,
        file_size: int,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed single-file CivitAI download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/file",
            json_payload={
                "url": url,
                "output_path": output_path,
                "file_size": file_size,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def search_civitai_models(
        self,
        *,
        query: str = "",
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return one filtered CivitAI browser search payload."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/models",
            json_payload={
                "query": query,
                "base_models": base_models,
                "model_types": model_types,
                "limit": limit,
                "cursor": cursor,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def fetch_civitai_model(
        self,
        *,
        model_id: str,
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return one filtered CivitAI browser detail payload."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/model",
            json_payload={
                "model_id": model_id,
                "base_models": base_models,
                "model_types": model_types,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def fetch_civitai_image(
        self,
        *,
        url: str,
        max_bytes: Optional[int] = None,
    ) -> bytes:
        """Fetch one CivitAI preview image through the daemon."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/image",
            json_payload={
                "url": url,
                "max_bytes": max_bytes,
            },
            timeout_seconds=30.0,
        )
        return response.content

    # ------------------------------------------------------------------
    # Download job management
    # ------------------------------------------------------------------

    def download_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return the current daemon download-job status payload."""
        response = self._request(
            "GET",
            f"/api/v1/downloads/status/{job_id}",
        )
        return response.json()

    def wait_download_job(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 1800.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Poll one download job until it reaches a terminal state."""
        deadline = self._time_fn() + timeout_seconds
        last_status: Optional[str] = None
        last_progress: Optional[float] = None

        while self._time_fn() < deadline:
            status = self.download_job_status(job_id)
            state = str(status.get("status", "")).lower()
            progress = float(status.get("progress") or 0.0)

            if progress_callback is not None and (
                state != last_status or progress != last_progress
            ):
                progress_callback(status)

            if state != last_status or progress != last_progress:
                self.logger.debug(
                    "wait_download_job job_id=%s status=%s progress=%.1f",
                    job_id,
                    state,
                    progress,
                )
                last_status = state
                last_progress = progress

            if state == "completed":
                return status
            if state == "failed":
                raise RuntimeError(
                    str(status.get("error") or "Download failed")
                )
            if state == "cancelled":
                raise RuntimeError("Download cancelled")

            self._sleep(self._poll_interval_seconds)

        try:
            self.cancel_download_job(job_id)
        except RuntimeError:
            pass

        raise RuntimeError("Timed out waiting for download job")

    def cancel_download_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel one daemon-backed download job."""
        response = self._request(
            "DELETE",
            f"/api/v1/downloads/cancel/{job_id}",
        )
        return response.json()
