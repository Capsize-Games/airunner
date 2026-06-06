from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Union
from zipfile import ZipFile, ZipInfo


class UnsafeZipPathError(ValueError):
    pass


def _is_symlink(info: ZipInfo) -> bool:
    # ZipInfo stores UNIX mode in the top 16 bits of external_attr.
    mode = (info.external_attr >> 16) & 0o777777
    return stat.S_ISLNK(mode)


def safe_extract_zip(zip_file: ZipFile, dest_dir: Union[str, Path]) -> None:
    """Safely extract a ZipFile into dest_dir, preventing Zip Slip.

    Raises UnsafeZipPathError if a member would escape dest_dir or is a symlink.
    """

    dest_path = Path(dest_dir).resolve()
    dest_path.mkdir(parents=True, exist_ok=True)

    for member in zip_file.infolist():
        name = member.filename

        # Disallow absolute paths and drive letters.
        if name.startswith(("/", "\\")):
            raise UnsafeZipPathError(
                f"Unsafe zip entry (absolute path): {name}"
            )
        if len(name) >= 2 and name[1] == ":" and name[0].isalpha():
            raise UnsafeZipPathError(f"Unsafe zip entry (drive path): {name}")

        # Disallow path traversal.
        parts = Path(name).parts
        if any(part == ".." for part in parts):
            raise UnsafeZipPathError(
                f"Unsafe zip entry (path traversal): {name}"
            )

        # Disallow symlinks.
        if _is_symlink(member):
            raise UnsafeZipPathError(f"Unsafe zip entry (symlink): {name}")

        target_path = (dest_path / name).resolve()
        if (
            not str(target_path).startswith(str(dest_path) + os.sep)
            and target_path != dest_path
        ):
            raise UnsafeZipPathError(
                f"Unsafe zip entry (escapes dest): {name}"
            )

    zip_file.extractall(dest_path)
