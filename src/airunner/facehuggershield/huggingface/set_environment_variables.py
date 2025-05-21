import os
from .settings import (
    HF_HUB_DISABLE_TELEMETRY,
    HF_HOME,
    HF_ENDPOINT,
    HF_INFERENCE_ENDPOINT,
    HF_HUB_DOWNLOAD_TIMEOUT,
    HF_HUB_ETAG_TIMEOUT,
    HF_HUB_DISABLE_PROGRESS_BARS,
    HF_HUB_DISABLE_SYMLINKS_WARNING,
    HF_HUB_DISABLE_EXPERIMENTAL_WARNING,
    HF_ASSETS_CACHE,
    HF_TOKEN,
    HF_HUB_VERBOSITY,
    HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD,
    HF_HUB_DISABLE_IMPLICIT_TOKEN,
    HF_ALLOW_DOWNLOADS,
    HF_DATASETS_OFFLINE,
    TRANSFORMERS_OFFLINE,
    DIFFUSERS_VERBOSITY,
    HF_HUB_OFFLINE
)


def set_huggingface_environment_variables(
    allow_downloads: bool = None,
    allow_remote_inference: bool = None
):
    """
    Set the environment variables for the Hugging Face Hub.
    :param allow_downloads:
    :param allow_remote_inference:
    :return:
    """
    print("Setting Hugging Face environment variables")
    allow_downloads = HF_ALLOW_DOWNLOADS if allow_downloads is None else allow_downloads

    if allow_downloads:
        os.environ["HF_ALLOW_DOWNLOADS"] = "1"

    os.environ["HF_HUB_DISABLE_TELEMETRY"] = HF_HUB_DISABLE_TELEMETRY
    os.environ["HF_HUB_OFFLINE"] = HF_HUB_OFFLINE
    os.environ["HF_HOME"] = HF_HOME
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT
    os.environ["HF_INFERENCE_ENDPOINT"] = HF_INFERENCE_ENDPOINT
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = HF_HUB_DISABLE_PROGRESS_BARS
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = HF_HUB_DISABLE_SYMLINKS_WARNING
    os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = HF_HUB_DISABLE_EXPERIMENTAL_WARNING
    os.environ["HF_ASSETS_CACHE"] = HF_ASSETS_CACHE
    os.environ["HF_TOKEN"] = HF_TOKEN
    os.environ["HF_HUB_VERBOSITY"] = HF_HUB_VERBOSITY
    os.environ["HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD"] = HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = HF_HUB_DOWNLOAD_TIMEOUT
    os.environ["HF_HUB_ETAG_TIMEOUT"] = HF_HUB_ETAG_TIMEOUT
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = HF_HUB_DISABLE_IMPLICIT_TOKEN
    os.environ["HF_DATASETS_OFFLINE"] = HF_DATASETS_OFFLINE
    os.environ["TRANSFORMERS_OFFLINE"] = TRANSFORMERS_OFFLINE
    os.environ["DIFFUSERS_VERBOSITY"] = DIFFUSERS_VERBOSITY
