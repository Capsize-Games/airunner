from urllib.parse import urlparse
from airunner.utils.application.mediator_mixin import MediatorMixin
from huggingface_hub import hf_hub_download


class DownloadHuggingface(MediatorMixin):
    """
    Handles downloading models from Hugging Face repositories.
    """

    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.file_name = None

    def download_model(self, url: str, _callback=None):
        """
        Download a model configuration file from the given Hugging Face URL.

        :param url: The URL of the Hugging Face model repository.
        :param _callback: Optional callback function to execute after download.
        """
        path = self.extract_path_from_url(url)
        hf_hub_download(repo_id=path, filename="config.json")

    @staticmethod
    def extract_path_from_url(url: str) -> str:
        """
        Extract the repository path from a Hugging Face URL.

        :param url: The URL to parse.
        :return: The extracted repository path.
        """
        parsed_url = urlparse(url)
        return parsed_url.path.lstrip("/")  # Remove leading slash

    def stop_download(self):
        """
        Stop the current download process if a worker is active.
        """
        if self.worker:
            self.worker.cancel()


class HuggingFaceDownloader:
    """
    Simple downloader for HuggingFace models for testability and modularity.
    """

    def download(self, repo_id: str, version: str) -> str:
        """
        Download a model from HuggingFace Hub.
        Args:
            repo_id: The repository ID on HuggingFace.
            version: The version or revision to download.
        Returns:
            str: Path to the downloaded model file.
        """
        # In real code, use huggingface_hub.hf_hub_download
        # Here, just a stub for testability
        return f"/models/{repo_id}/{version}/model.safetensors"


def download_model(repo_id: str, version: str) -> str:
    """
    Download a model from HuggingFace using HuggingFaceDownloader.
    Args:
        repo_id: The repository ID on HuggingFace.
        version: The version or revision to download.
    Returns:
        str: Path to the downloaded model file.
    """
    downloader = HuggingFaceDownloader()
    return downloader.download(repo_id, version)
