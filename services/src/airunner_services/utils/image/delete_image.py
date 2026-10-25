import os
import threading

lock = threading.Lock()


def _default_image_base() -> str:
    """Return the configured image directory for delete confinement."""
    from airunner_common.settings import AIRUNNER_BASE_PATH  # noqa: PLC0415

    return os.path.join(
        os.path.expanduser(str(AIRUNNER_BASE_PATH)),
        "art",
        "other",
        "images",
    )


def _is_within_base(target: str, base: str) -> bool:
    """Return whether resolved target stays inside resolved base."""
    try:
        return os.path.commonpath([target, base]) == base
    except ValueError:
        return False


def delete_image(path, base_dir=None) -> bool:
    """Delete one image file confined to the configured image directory.

    Args:
        path: File to delete.
        base_dir: Directory deletions are confined to. Defaults to the
            configured image path (``{BASE}/art/other/images``).

    Returns:
        True when the file was deleted, False when it was missing,
        not a file, or outside the confined directory.
    """
    with lock:
        try:
            base = os.path.realpath(base_dir or _default_image_base())
            target = os.path.realpath(path)
        except (TypeError, ValueError, OSError):
            return False
        if target == base or not _is_within_base(target, base):
            return False
        if os.path.isfile(target):
            os.remove(target)
            return True
        return False
