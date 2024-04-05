import os
from urllib.parse import urlparse

import requests
from json.decoder import JSONDecodeError
from PySide6.QtCore import QThread
from airunner.aihandler.stablediffusion.download_worker import DownloadWorker
from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
from huggingface_hub import hf_hub_download


class DownloadHuggingface(
    MediatorMixin
):
    def __init__(self):
        MediatorMixin.__init__(self)
        super().__init__()
        self.thread = None
        self.worker = None
        self.file_name = None

    def download_model(self, url, callback=None):
        path = self.extract_path_from_url(url)
        hf_hub_download(repo_id=path, filename="config.json")

    def extract_path_from_url(self, url) -> str:
        parsed_url = urlparse(url)
        return parsed_url.path.lstrip('/')  # remove leading slash

    def stop_download(self):
        if self.worker:
            self.worker.cancel()
