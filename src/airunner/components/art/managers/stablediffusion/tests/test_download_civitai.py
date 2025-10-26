
from airunner.components.art.managers.stablediffusion.download_civitai import (
    CivitAIDownloader,
    download_model,
)


def test_civitai_downloader_returns_path():
    d = CivitAIDownloader()
    path = d.download("123", "v1")
    assert path.endswith("/models/123/v1/model.safetensors")


def test_download_model_helper():
    path = download_model("99", "v2")
    assert "/models/99/v2/model.safetensors" in path
