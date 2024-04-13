import os


def default_hf_cache_dir():
    default_home = os.path.join(os.path.expanduser("~"), ".cache")
    hf_cache_home = os.path.expanduser(
        os.getenv(
            "HF_HOME",
            os.path.join(os.getenv("XDG_CACHE_HOME", default_home), "huggingface"),
        )
    )
    default_cache_path = os.path.join(hf_cache_home, "hub")
    HUGGINGFACE_HUB_CACHE = os.getenv("HUGGINGFACE_HUB_CACHE", default_cache_path)
    return HUGGINGFACE_HUB_CACHE
