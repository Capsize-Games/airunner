"""PostgreSQL driver selection and native plugin-path confinement."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any


class PostgreSQLRuntimeError(RuntimeError):
    """The PostgreSQL native runtime cannot be confined safely."""


def _drivername(db_url: Any) -> str:
    """Return a SQLAlchemy URL's driver name without importing its DBAPI."""
    value = getattr(db_url, "drivername", None)
    if isinstance(value, str):
        return value.lower()
    return str(db_url).split(":", 1)[0].lower()


def is_postgresql_url(db_url: Any) -> bool:
    """Return whether ``db_url`` targets a PostgreSQL dialect."""
    return _drivername(db_url).split("+", 1)[0] in {"postgres", "postgresql"}


def normalize_postgresql_url(db_url: Any) -> Any:
    """Select Psycopg 3 for driverless PostgreSQL URLs.

    Explicit driver names are preserved. This lets the full Linux profile
    support the conventional ``postgresql://`` form without depending on
    SQLAlchemy's legacy psycopg2 default.
    """
    if _drivername(db_url) not in {"postgres", "postgresql"}:
        return db_url

    from sqlalchemy.engine import make_url

    url = make_url(db_url)
    return url.set(drivername="postgresql+psycopg")


def _assert_safe_ancestry(path: Path) -> None:
    """Reject symlink redirects and writable unprotected ancestors."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise PostgreSQLRuntimeError(
                f"PostgreSQL runtime path contains a symlink: {current}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise PostgreSQLRuntimeError(
                f"PostgreSQL runtime path component is not a directory: {current}"
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o022 and not mode & stat.S_ISVTX:
            raise PostgreSQLRuntimeError(
                f"PostgreSQL runtime path has an unprotected writable ancestor: {current}"
            )


def _create_safe_directory_chain(path: Path) -> None:
    """Create missing components one at a time with private defaults."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                # Re-read below and reject a raced-in symlink or file.
                pass
            metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(
            metadata.st_mode
        ):
            raise PostgreSQLRuntimeError(
                f"PostgreSQL runtime path component is not a real directory: {current}"
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o022 and not mode & stat.S_ISVTX:
            raise PostgreSQLRuntimeError(
                f"PostgreSQL runtime path has an unprotected writable ancestor: {current}"
            )


def _ensure_directory(path: Path, *, private: bool, label: str) -> None:
    """Create or validate a directory without changing existing modes."""
    _assert_safe_ancestry(path)
    try:
        _create_safe_directory_chain(path)
        _assert_safe_ancestry(path)
        metadata = path.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise PostgreSQLRuntimeError(f"{label} must be a real directory")
        uid = os.geteuid()
        if metadata.st_uid not in {0, uid}:
            raise PostgreSQLRuntimeError(
                f"{label} must be owned by root or the service user"
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if metadata.st_uid == uid and uid != 0:
            if private and mode & 0o077:
                raise PostgreSQLRuntimeError(
                    f"service-owned {label} must have private permissions"
                )
            if mode & 0o022:
                raise PostgreSQLRuntimeError(
                    f"service-owned {label} cannot be group/world writable"
                )
        elif mode & 0o022:
            raise PostgreSQLRuntimeError(
                f"root-owned {label} cannot be group/world writable"
            )
    except PostgreSQLRuntimeError:
        raise
    except OSError as exc:
        raise PostgreSQLRuntimeError(
            f"cannot create or verify {label}: {exc}"
        ) from exc


def _plugin_directory(runtime_root: str | Path | None) -> Path:
    if runtime_root is None:
        configured_root = os.environ.get("AIRUNNER_RUNTIME_ROOT")
        if configured_root is not None:
            runtime_root = configured_root
        else:
            from airunner_common.settings import AIRUNNER_BASE_PATH

            runtime_root = Path(AIRUNNER_BASE_PATH) / "runtime"

    root = Path(os.path.expanduser(str(runtime_root)))
    if not root.is_absolute():
        raise PostgreSQLRuntimeError(
            "PostgreSQL runtime root must be absolute"
        )
    if ".." in root.parts:
        raise PostgreSQLRuntimeError(
            "PostgreSQL runtime root cannot contain parent traversal"
        )
    root = Path(os.path.abspath(root))

    # Keep the potentially shared runtime root unchanged. Only this dedicated
    # private child is created or inspected for the SASL plugin search path.
    _ensure_directory(root, private=False, label="PostgreSQL runtime root")
    private_root = root / "postgresql-runtime"
    _ensure_directory(
        private_root,
        private=True,
        label="PostgreSQL private runtime directory",
    )
    return private_root / "sasl-empty"


def _ensure_empty_plugin_directory(path: Path) -> Path:
    text = str(path)
    if os.pathsep in text or "=" in text:
        raise PostgreSQLRuntimeError(
            "SASL plugin path must be one directory without list delimiters"
        )

    try:
        _ensure_directory(
            path.parent,
            private=True,
            label="PostgreSQL private runtime directory",
        )
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass

        _assert_safe_ancestry(path)
        metadata = path.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise PostgreSQLRuntimeError(
                "SASL plugin path must be a real directory, not a symlink"
            )

        uid = os.geteuid()
        if metadata.st_uid not in {0, uid}:
            raise PostgreSQLRuntimeError(
                "SASL plugin directory must be owned by root or the service user"
            )

        mode = stat.S_IMODE(metadata.st_mode)
        if metadata.st_uid == uid and uid != 0:
            if mode & 0o077:
                raise PostgreSQLRuntimeError(
                    "service-owned SASL plugin directory must be private"
                )
        elif mode & 0o022:
            raise PostgreSQLRuntimeError(
                "root-owned SASL plugin directory cannot be group/world writable"
            )

        if any(path.iterdir()):
            raise PostgreSQLRuntimeError("SASL plugin directory must be empty")
    except PostgreSQLRuntimeError:
        raise
    except OSError as exc:
        raise PostgreSQLRuntimeError(
            f"cannot create or verify the SASL plugin directory: {exc}"
        ) from exc

    return path


def configure_postgresql_runtime(
    db_url: Any,
    *,
    runtime_root: str | Path | None = None,
) -> Path | None:
    """Confine Psycopg and Cyrus SASL before PostgreSQL DBAPI loading.

    SQLite and other database URLs are left untouched. PostgreSQL URLs fail
    closed under setuid/setgid execution because Cyrus SASL ignores
    ``SASL_PATH`` when real and effective identities differ.
    """
    if not is_postgresql_url(db_url):
        return None

    if os.getuid() != os.geteuid() or os.getgid() != os.getegid():
        raise PostgreSQLRuntimeError(
            "PostgreSQL requires equal real/effective UID and GID for SASL_PATH"
        )

    path = _ensure_empty_plugin_directory(_plugin_directory(runtime_root))

    # Replace inherited values rather than append to them: Cyrus SASL accepts
    # path lists, and any extra host directory could load an unreviewed module.
    os.environ["SASL_PATH"] = str(path)
    os.environ["PSYCOPG_IMPL"] = "python"
    return path


__all__ = [
    "PostgreSQLRuntimeError",
    "configure_postgresql_runtime",
    "is_postgresql_url",
    "normalize_postgresql_url",
]
