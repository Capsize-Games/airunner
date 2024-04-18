import os

####################################################################################################
# Set Hugging Face environment variables
####################################################################################################
from airunner.settings import (
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
    HF_HUB_OFFLINE,
    HF_DATASETS_OFFLINE,
    TRANSFORMERS_OFFLINE,
    DIFFUSERS_VERBOSITY,
    DEFAULT_HF_INFERENCE_ENDPOINT,
    DEFAULT_HF_HUB_OFFLINE,
    DEFAULT_HF_ENDPOINT,
    DEFAULT_HF_DATASETS_OFFLINE,
    DEFAULT_TRANSFORMERS_OFFLINE,
    TRUST_REMOTE_CODE,
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
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = HF_HUB_DISABLE_TELEMETRY

    """
    Conditionally set environment variables which are used 
    to control the ability of the Hugging Face Hub and other
    related services to access the internet.

    We set environment variables so that we can ensure the applications
    are not overridden from any other source.
    """
    hf_hub_offline = HF_HUB_OFFLINE if not allow_downloads else DEFAULT_HF_HUB_OFFLINE
    hf_datasets_offline = HF_DATASETS_OFFLINE if not allow_downloads else DEFAULT_HF_DATASETS_OFFLINE
    transformers_offline = TRANSFORMERS_OFFLINE if not allow_downloads else DEFAULT_TRANSFORMERS_OFFLINE
    hf_endpoint = HF_ENDPOINT if not allow_downloads else DEFAULT_HF_ENDPOINT
    hf_inf_endpoint = HF_INFERENCE_ENDPOINT if not allow_downloads else DEFAULT_HF_INFERENCE_ENDPOINT
    os.environ["HF_ENDPOINT"] = hf_endpoint
    os.environ["HF_DATASETS_OFFLINE"] = hf_datasets_offline
    os.environ["TRANSFORMERS_OFFLINE"] = transformers_offline
    os.environ["HF_INFERENCE_ENDPOINT"] = hf_inf_endpoint
    os.environ["HF_HUB_OFFLINE"] = hf_hub_offline

    """
    Set the remaining environment variables for the Hugging Face Hub.
    """
    os.environ["HF_HOME"] = HF_HOME
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
    os.environ["DIFFUSERS_VERBOSITY"] = DIFFUSERS_VERBOSITY
    os.environ["TRUST_REMOTE_CODE"] = TRUST_REMOTE_CODE


set_huggingface_environment_variables()