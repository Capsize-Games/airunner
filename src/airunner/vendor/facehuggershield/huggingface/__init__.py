from typing import List, Optional
import airunner.vendor.facehuggershield.defendatron
from airunner.vendor.facehuggershield.huggingface.set_environment_variables import (
    set_huggingface_environment_variables,
)

print("Activating facehugger shield...")


def activate(
    nullscream_blacklist: Optional[List[str]] = None,
    nullscream_whitelist: Optional[List[str]] = None,
    nullscream_function_blacklist: Optional[List[str]] = None,
    activate_shadowlogger: bool = True,
    activate_darklock: bool = True,
    activate_nullscream: bool = True,
    show_stdout: bool = True,
    # darklock properties
    darklock_os_whitelisted_operations: List = None,
    darklock_os_whitelisted_filenames: List = None,
    darklock_os_whitelisted_modules: List = None,
    darklock_os_whitelisted_directories: List = None,
    darklock_os_allow_network: bool = False,
    darklock_allowed_network_port: int = None,
):
    """
    Activate FacehuggerShield security protections.
    
    Args:
        nullscream_blacklist: Modules to block (return noop versions).
        nullscream_whitelist: Modules to allow even if in blacklist.
        nullscream_function_blacklist: Specific functions to block.
        activate_shadowlogger: Enable log interception.
        activate_darklock: Enable OS/network restrictions.
        activate_nullscream: Enable module blocking.
        show_stdout: Show shadowed logs to stdout.
        darklock_os_whitelisted_operations: OS operations to allow.
        darklock_os_whitelisted_filenames: Files to allow access to.
        darklock_os_whitelisted_modules: Modules allowed to perform OS operations.
        darklock_os_whitelisted_directories: Directories to allow file operations in.
        darklock_os_allow_network: If True, allow network on specific port only.
        darklock_allowed_network_port: Port to allow if allow_network=True.
    """
    nullscream_blacklist = nullscream_blacklist or [
        "huggingface_hub.commands",
        "huggingface_hub.commands._cli_utils",
        "huggingface_hub.templates",
        "huggingface_hub._commit_api",
        "huggingface_hub._commit_scheduler",
        "huggingface_hub._inference_endpoints",
        "huggingface_hub._login",
        "huggingface_hub._snapshot_download",
        "huggingface_hub._space_api",
        "huggingface_hub._tensorboard_logger",
        "huggingface_hub._webhooks_payload",
        "huggingface_hub._webhooks_server",
        "huggingface_hub.community",
        "huggingface_hub.fastai_utils",
        "huggingface_hub.file_download",
        "huggingface_hub.hf_api",
        "huggingface_hub.inference_api",
        "huggingface_hub.repocard",
        "huggingface_hub.repocard_data",
        "huggingface_hub.utils._gitcredential",
        "huggingface_hub.utils._headers",
        "huggingface_hub.utils._telemetry",
        "huggingface_hub.utils._cache_manager",
        "transformers.utils.hub.PushToHubMixin",
        "transformers.tools.agents",
        "transformers",
    ]
    nullscream_whitelist = nullscream_whitelist or []
    nullscream_function_blacklist = nullscream_function_blacklist or []
    set_huggingface_environment_variables(
        allow_downloads=False,
    )
    airunner.vendor.facehuggershield.defendatron.activate(
        nullscream_blacklist=nullscream_blacklist,
        nullscream_whitelist=nullscream_whitelist,
        nullscream_function_blacklist=nullscream_function_blacklist,
        activate_shadowlogger=activate_shadowlogger,
        activate_darklock=activate_darklock,
        activate_nullscream=activate_nullscream,
        show_stdout=show_stdout,
        darklock_os_whitelisted_operations=darklock_os_whitelisted_operations,
        darklock_os_whitelisted_filenames=darklock_os_whitelisted_filenames,
        darklock_os_whitelisted_modules=darklock_os_whitelisted_modules,
        darklock_os_whitelisted_directories=darklock_os_whitelisted_directories,
        darklock_os_allow_network=darklock_os_allow_network,
        darklock_allowed_network_port=darklock_allowed_network_port,
    )
