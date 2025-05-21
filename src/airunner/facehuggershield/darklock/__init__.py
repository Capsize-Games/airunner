from airunner.facehuggershield.darklock.restrict_os_access import (
    RestrictOSAccess,
)
from airunner.facehuggershield.darklock.restrict_network_access import (
    RestrictNetworkAccess,
)


network = RestrictNetworkAccess()
os = RestrictOSAccess()


def activate(
    whitelisted_operations: list = None,
    whitelisted_filenames: list = None,
    whitelisted_imports: list = None,
    blacklisted_filenames: list = None,
    whitelisted_directories: list = None,
):
    # network.activate(
    #     allowed_port=4222
    # )
    os.activate(
        whitelisted_operations,
        whitelisted_filenames,
        whitelisted_imports,
        blacklisted_filenames,
        whitelisted_directories,
    )


def deactivate():
    network.deactivate()
    os.deactivate()
