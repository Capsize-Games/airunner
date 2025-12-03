from airunner.vendor.facehuggershield.darklock.restrict_os_access import (
    RestrictOSAccess,
)
from airunner.vendor.facehuggershield.darklock.restrict_network_access import (
    RestrictNetworkAccess,
)


network = RestrictNetworkAccess()
os = RestrictOSAccess()  # Do NOT call os.activate() here!

# WARNING: Do NOT call os.activate() at import/module level. Only call it from your main application entry point after all imports are complete.


def activate(
    whitelisted_modules: list = None,
    allow_network: bool = False,
    whitelisted_operations: list = None,  # This parameter is not used by RestrictOSAccess.activate
    whitelisted_files: list = None,  # This parameter is not used by RestrictOSAccess.activate
    whitelisted_directories: list = None,
    allowed_network_port: int = None,
):
    """
    Activates the DarkLock OS and network access restrictions.

    Args:
        whitelisted_modules: A list of modules that are allowed to be imported.
        allow_network: Whether to allow network access. If False, network is completely blocked.
                       If True, network is restricted to localhost on allowed_network_port only.
        whitelisted_operations: (Not used by RestrictOSAccess) A list of OS operations that are allowed.
        whitelisted_files: (Not used by RestrictOSAccess) A list of files that are allowed to be accessed.
        whitelisted_directories: A list of directories that are allowed to be accessed.
        allowed_network_port: The port to allow network access on (only used if allow_network=True).
    """
    # Activate OS restrictions
    os.activate(
        whitelisted_directories=whitelisted_directories,
        whitelisted_modules=whitelisted_modules,
        allow_network=allow_network,
    )
    
    # Activate network restrictions unless explicitly allowing network access
    if not allow_network:
        # Block all network access
        network.activate(allowed_port=None)
    elif allowed_network_port:
        # Allow only specific port on localhost
        network.activate(allowed_port=allowed_network_port)


def deactivate():
    network.deactivate()
    os.deactivate()
