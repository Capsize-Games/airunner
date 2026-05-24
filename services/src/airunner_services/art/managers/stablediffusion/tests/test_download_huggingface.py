from airunner.components.art.managers.stablediffusion.download_huggingface import (
    DownloadHuggingface,
    HuggingFaceDownloader,
    download_model,
)


def test_extract_path_from_url():
    d = DownloadHuggingface()
    assert (
        d.extract_path_from_url("https://huggingface.co/owner/repo")
        == "owner/repo"
    )


def test_huggingface_downloader_stub():
    h = HuggingFaceDownloader()
    p = h.download("owner/repo", "v1")
    assert p.endswith("/models/owner/repo/v1/model.safetensors")


def test_download_model_helper():
    p = download_model("owner/repo", "v2")
    assert "/models/owner/repo/v2/model.safetensors" in p
