from airunner.facehuggershield.darklock.restrict_os_access import (
    RestrictOSAccess,
)
from airunner.facehuggershield.darklock.restrict_network_access import (
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
):
    """
    Activates the DarkLock OS access restrictions.

    Args:
        whitelisted_modules: A list of modules that are allowed to be imported.
        allow_network: Whether to allow network access.
        whitelisted_operations: (Not used by RestrictOSAccess) A list of OS operations that are allowed.
        whitelisted_files: (Not used by RestrictOSAccess) A list of files that are allowed to be accessed.
        whitelisted_directories: A list of directories that are allowed to be accessed.
    """
    os.activate(
        whitelisted_directories=whitelisted_directories,
        whitelisted_modules=whitelisted_modules,
        allow_network=allow_network,
    )


def deactivate():
    network.deactivate()
    os.deactivate()
