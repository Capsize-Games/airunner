import sys


PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_BSD = "bsd"
PLATFORM_DARWIN = "darwin"
PLATFORM_UNKNOWN = "unknown"


def get_platform_name() -> str:
    """Return the normalized AIRunner platform name for this process."""
    if sys.platform.startswith("win"):
        return PLATFORM_WINDOWS
    elif sys.platform.startswith("darwin"):
        return PLATFORM_DARWIN
    elif sys.platform.startswith("linux"):
        return PLATFORM_LINUX
    elif sys.platform.startswith(
        ("dragonfly", "freebsd", "netbsd", "openbsd", "bsd")
    ):
        return PLATFORM_BSD
    else:
        return PLATFORM_UNKNOWN


__platform__ = get_platform_name()


def is_linux() -> bool:
    """Return whether this process is running on Linux."""
    return __platform__ == PLATFORM_LINUX


def is_bsd() -> bool:
    """Return whether this process is running on BSD."""
    return __platform__ == PLATFORM_BSD


def is_darwin() -> bool:
    """Return whether this process is running on macOS."""
    return __platform__ == PLATFORM_DARWIN


def is_windows() -> bool:
    """Return whether this process is running on Windows."""
    return __platform__ == PLATFORM_WINDOWS
