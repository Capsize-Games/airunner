import logging

import airunner.vendor.facehuggershield.shadowlogger
import airunner.vendor.facehuggershield.darklock
import airunner.vendor.facehuggershield.nullscream
from airunner.vendor.facehuggershield.defendatron.nullscream_tracker import (
    NullscreamTracker,
)


nullscream_tracker = NullscreamTracker()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def activate(
    # Nullscream properties
    nullscream_blacklist: list = None,
    nullscream_whitelist: list = None,
    nullscream_function_blacklist: list = None,
    # darklock properites
    darklock_os_whitelisted_operations: list = None,
    darklock_os_whitelisted_filenames: list = None,
    darklock_os_whitelisted_modules: list = None,
    # darklock_os_blacklisted_filenames: list = None,
    darklock_os_whitelisted_directories: list = None,
    darklock_os_allow_network: bool = False,
    activate_shadowlogger: bool = False,
    activate_darklock: bool = False,
    activate_nullscream: bool = False,
    # Shadowlogger properties
    show_stdout: bool = True,
):
    logger.info("Activating defendatron")
    if activate_shadowlogger:
        logger.info("Activating shadowlogger")
        airunner.vendor.facehuggershield.shadowlogger.manager.activate(
            show_stdout=show_stdout,
            trackers=[nullscream_tracker],
        )

    if activate_darklock:
        logger.info("Activating darklock")
        airunner.vendor.facehuggershield.darklock.activate(
            whitelisted_modules=darklock_os_whitelisted_modules,
            allow_network=darklock_os_allow_network,  # Pass allow_network
            # whitelisted_operations=darklock_os_whitelisted_operations, # Not used by darklock.activate
            # whitelisted_files=darklock_os_whitelisted_filenames, # Not used by darklock.activate
            whitelisted_directories=darklock_os_whitelisted_directories,
        )

    if activate_nullscream:
        logger.info("Activating nullscream")
        airunner.vendor.facehuggershield.nullscream.activate(
            blacklist=nullscream_blacklist,
            whitelist=nullscream_whitelist,
            function_blacklist=nullscream_function_blacklist,
        )


def deactivate(
    # Nullscream properties
    nullscream_blacklist: list = None,
):
    airunner.vendor.facehuggershield.shadowlogger.manager.deactivate()
    airunner.vendor.facehuggershield.darklock.manager.deactivate()
    airunner.vendor.facehuggershield.nullscream.manager.deactivate(
        blacklist=nullscream_blacklist,
    )
