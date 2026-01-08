import os
import re
import sys
import urllib
import ipaddress
import socket
import uuid
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QInputDialog
from PySide6.QtCore import QProcess


class PathManager:
    """
    Handles path and script management logic for MainWindow.
    """

    def __init__(self, path_settings, logger=None):
        self.path_settings = path_settings
        self.logger = logger
        if self.logger:
            self.logger.debug("PathManager initialized.")

    def set_path_settings(self, main_window, key, val):
        if self.logger:
            self.logger.debug(f"Setting path: {key} = {val}")
        main_window.update_path_settings(key, val)

    def reset_paths(self, main_window):
        if self.logger:
            self.logger.info("Resetting all paths to defaults.")
        main_window.reset_path_settings()

    def restart(self, main_window):
        if self.logger:
            self.logger.info("Restarting application.")
        main_window.save_state()
        main_window.close()
        QProcess.startDetached(sys.executable, sys.argv)

    def download_url(self, url, save_path):
        if self.logger:
            self.logger.info(f"Downloading URL: {url} to {save_path}")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only http/https URLs are allowed")

        hostname = (parsed.hostname or "").strip().strip("[]")
        if hostname:
            try:
                ip = ipaddress.ip_address(hostname)
                ips = [ip]
            except ValueError:
                try:
                    infos = socket.getaddrinfo(hostname, None)
                    ips = [ipaddress.ip_address(info[4][0]) for info in infos]
                except Exception:
                    ips = []

            if ips and any(
                a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast
                for a in ips
            ) and os.environ.get("AIRUNNER_ALLOW_PRIVATE_URLS") != "1":
                raise ValueError(
                    "Refusing to download from private/loopback hosts. "
                    "Set AIRUNNER_ALLOW_PRIVATE_URLS=1 to override."
                )

        timeout = (5, 30)
        max_bytes = int(os.environ.get("AIRUNNER_MAX_DOWNLOAD_BYTES", str(20 * 1024 * 1024)))
        sniff_bytes = 1024 * 1024

        tmp_name = f".download-{uuid.uuid4().hex}.tmp"
        tmp_path = os.path.join(save_path, tmp_name)
        downloaded = 0
        sniff = bytearray()

        try:
            with requests.get(url, timeout=timeout, stream=True) as response:
                response.raise_for_status()

                with open(tmp_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise ValueError(
                                f"Download exceeded limit ({max_bytes} bytes)"
                            )
                        file.write(chunk)
                        if len(sniff) < sniff_bytes:
                            take = min(len(chunk), sniff_bytes - len(sniff))
                            sniff.extend(chunk[:take])

            try:
                soup = BeautifulSoup(bytes(sniff), "html.parser")
                title = soup.title.string if soup.title else url
            except Exception:
                title = url
            title_words = str(title).split()[:10]
            filename = "_".join(title_words) + ".html"
            filename = re.sub(r"[^\w\-_]", "_", filename)
            final_path = os.path.join(save_path, filename)
            os.replace(tmp_path, final_path)
            if self.logger:
                self.logger.debug(f"Downloaded and saved as: {final_path}")
            return filename
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def download_pdf(self, url, save_path):
        if self.logger:
            self.logger.info(f"Downloading PDF: {url} to {save_path}")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only http/https URLs are allowed")

        hostname = (parsed.hostname or "").strip().strip("[]")
        if hostname:
            try:
                ip = ipaddress.ip_address(hostname)
                ips = [ip]
            except ValueError:
                try:
                    infos = socket.getaddrinfo(hostname, None)
                    ips = [ipaddress.ip_address(info[4][0]) for info in infos]
                except Exception:
                    ips = []

            if ips and any(
                a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast
                for a in ips
            ) and os.environ.get("AIRUNNER_ALLOW_PRIVATE_URLS") != "1":
                raise ValueError(
                    "Refusing to download from private/loopback hosts. "
                    "Set AIRUNNER_ALLOW_PRIVATE_URLS=1 to override."
                )

        timeout = (5, 60)
        max_bytes = int(os.environ.get("AIRUNNER_MAX_DOWNLOAD_BYTES", str(50 * 1024 * 1024)))

        filename = os.path.basename(parsed.path or "") or "download.pdf"
        filename = re.sub(r"[^\w\-.]", "_", filename)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        tmp_name = f".download-{uuid.uuid4().hex}.tmp"
        tmp_path = os.path.join(save_path, tmp_name)
        final_path = os.path.join(save_path, filename)
        downloaded = 0

        try:
            with requests.get(url, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                with open(tmp_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise ValueError(
                                f"Download exceeded limit ({max_bytes} bytes)"
                            )
                        file.write(chunk)
            os.replace(tmp_path, final_path)
            if self.logger:
                self.logger.debug(f"Downloaded and saved as: {final_path}")
            return filename
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def on_navigate_to_url(self, main_window, _data=None):
        if self.logger:
            self.logger.info("Navigating to URL via dialog.")
        url, ok = QInputDialog.getText(
            main_window, "Browse Web", "Enter your URL:"
        )
        if ok:
            try:
                result = urllib.parse.urlparse(url)
                is_url = result.scheme in {"http", "https"} and bool(result.netloc)
            except ValueError:
                is_url = False
            if is_url:
                if url.lower().endswith(".pdf"):
                    filepath = os.path.expanduser(self.path_settings.pdf_path)
                    filename = self.download_pdf(url, filepath)
                else:
                    filepath = os.path.expanduser(
                        self.path_settings.webpages_path
                    )
                    filename = self.download_url(url, filepath)
            elif os.path.isfile(url):
                filepath = os.path.dirname(url)
                filename = os.path.basename(url)
            else:
                if self.logger:
                    self.logger.error(f"Invalid URL or file path")
                return
            if self.logger:
                self.logger.debug(
                    f"Updating chatbot with file: {os.path.join(filepath, filename)}"
                )
            main_window.update_chatbot(
                "target_files", [os.path.join(filepath, filename)]
            )
            main_window.api.llm.reload_rag(main_window.chatbot.target_files)
            from airunner.components.llm.managers.llm_request import LLMRequest
            from airunner.enums import LLMActionType

            main_window.api.llm.send_request(
                action=LLMActionType.PERFORM_RAG_SEARCH,
                prompt="Summarize the text and provide a synopsis of the content. Be concise and informative.",
                llm_request=LLMRequest.from_default(),
            )
