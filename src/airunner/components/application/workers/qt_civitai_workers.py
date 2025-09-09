"""Qt workers for CivitAI API operations (model info + file download).

These workers are designed to run on a QThread and communicate with the GUI
using Qt signals, keeping all network and file I/O off the main thread.

They do not depend on application-specific mixins to remain thread-safe.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os
import requests
from PySide6.QtCore import QObject, Signal


class ModelInfoWorker(QObject):
    """Fetch model information from CivitAI in a background thread.

    Signals:
        fetched: Emitted with the model info dict on success.
        error: Emitted with an error message on failure.
    """

    fetched = Signal(dict)
    error = Signal(str)

    def __init__(self, url: str, api_key: Optional[str] = None) -> None:
        super().__init__()
        self.url = url
        self.api_key = api_key or ""

    @staticmethod
    def _parse_url(url: str) -> Dict[str, Any]:
        import re

        model_id = None
        model_version_id = None
        m = re.search(r"/models/(\d+)", url)
        if m:
            model_id = m.group(1)
        m2 = re.search(r"modelVersionId=(\d+)", url)
        if m2:
            model_version_id = m2.group(1)
        return {"model_id": model_id, "model_version_id": model_version_id}

    def run(self) -> None:
        try:
            ids = self._parse_url(self.url)
            model_id = ids.get("model_id")
            if not model_id:
                self.error.emit("Invalid CivitAI model URL")
                return
            api_url = f"https://civitai.com/api/v1/models/{model_id}"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(api_url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            # Attach selectedVersion if requested in URL
            mv_id = ids.get("model_version_id")
            if mv_id:
                for v in data.get("modelVersions", []):
                    if str(v.get("id")) == mv_id:
                        data["selectedVersion"] = v
                        break
            self.fetched.emit(data)
        except Exception as e:  # noqa: BLE001 - bubble the message
            # Provide detail for 401 to help user debug tokens
            msg = str(e)
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 401:
                msg = f"401 Unauthorized: {msg}"
            self.error.emit(msg)


class FileDownloadWorker(QObject):
    """Stream a file download from CivitAI with progress and cancel support.

    Signals:
        progress(int, int): current bytes, total bytes (0 if unknown)
        finished(str): emitted with save path when done
        error(str): error message
        canceled(): emitted when user canceled and worker stopped
    """

    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)
    canceled = Signal()

    def __init__(
        self,
        url: str,
        save_path: str,
        api_key: Optional[str] = None,
        total_size_bytes: int = 0,
    ) -> None:
        super().__init__()
        self.url = url
        self.save_path = os.path.expanduser(save_path)
        self.api_key = api_key or ""
        self.total_size = max(0, int(total_size_bytes))
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def _headers(self) -> dict:
        h = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _try_download(self, url: str) -> bool:
        try:
            with requests.get(
                url,
                stream=True,
                allow_redirects=True,
                headers=self._headers(),
                timeout=30,
            ) as r:
                r.raise_for_status()
                # Get total from headers if not provided
                if self.total_size == 0:
                    try:
                        self.total_size = int(
                            r.headers.get("content-length", 0)
                        )
                    except Exception:
                        self.total_size = 0
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                with open(self.save_path, "wb") as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._is_cancelled:
                            # best-effort cleanup of partial file
                            try:
                                f.close()
                            except Exception:
                                pass
                            try:
                                if os.path.exists(self.save_path):
                                    os.remove(self.save_path)
                            except Exception:
                                pass
                            self.canceled.emit()
                            return False
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.progress.emit(downloaded, self.total_size)
                self.finished.emit(self.save_path)
                return True
        except requests.HTTPError as http_err:
            # If 401, retry with ?token=...
            status = getattr(
                getattr(http_err, "response", None), "status_code", None
            )
            if status == 401 and self.api_key:
                sep = "&" if "?" in url else "?"
                token_url = f"{url}{sep}token={self.api_key}"
                return self._try_download(token_url)
            self.error.emit(str(http_err))
            return False
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))
            return False

    def run(self) -> None:
        self._try_download(self.url)
