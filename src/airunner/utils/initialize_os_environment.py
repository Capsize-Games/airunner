import os


def initialize_os_environment():
    hf_cache_path = ""
    if hf_cache_path != "":
        # check if hf_cache_path exists
        if os.path.exists(hf_cache_path):
            os.unsetenv("HUGGINGFACE_HUB_CACHE")
            os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_path

