import os
import re
import sys
import urllib
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
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string if soup.title else url
        title_words = title.split()[:10]
        filename = "_".join(title_words) + ".html"
        filename = re.sub(r"[^\w\-_]", "_", filename)
        save_path = os.path.join(save_path, filename)
        with open(save_path, "wb") as file:
            file.write(response.content)
        if self.logger:
            self.logger.debug(f"Downloaded and saved as: {save_path}")
        return filename

    def download_pdf(self, url, save_path):
        if self.logger:
            self.logger.info(f"Downloading PDF: {url} to {save_path}")
        response = requests.get(url)
        filename = url.split("/")[-1]
        save_path = os.path.join(save_path, filename)
        with open(save_path, "wb") as file:
            file.write(response.content)
        if self.logger:
            self.logger.debug(f"Downloaded and saved as: {save_path}")
        return filename

    def on_navigate_to_url(self, main_window, _data=None):
        if self.logger:
            self.logger.info("Navigating to URL via dialog.")
        url, ok = QInputDialog.getText(
            main_window, "Browse Web", "Enter your URL:"
        )
        if ok:
            try:
                result = urllib.parse.urlparse(url)
                is_url = all([result.scheme, result.netloc])
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
