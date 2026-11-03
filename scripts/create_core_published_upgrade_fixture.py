#!/usr/bin/env python3
"""Build a synthetic database from the published CORE Debian migration set."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

_EXPECTED_PACKAGE = "airunner"
_EXPECTED_VERSION = "6.1.3-3"
_EXPECTED_DEB_SHA256 = (
    "60c07b5c2e8701b9f07309ee10be0327b5ef5ae908464fc370619bcfe4e4b87c"
)
_EXPECTED_MIGRATION_COUNT = 87
_EXPECTED_BASELINE_HEADS = ("a7c93f2e1b4d", "d951d2fd378d")
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
_FIXTURE_PAYLOAD = "synthetic-published-core-upgrade-data-v1"
_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
_MAX_SELECTED_BYTES = 16 * 1024 * 1024
_MAX_SELECTED_FILES = 1200
_PACKAGE_ROOTS = (
    PurePosixPath("usr/lib/python3/dist-packages/airunner_common"),
    PurePosixPath("usr/lib/python3/dist-packages/airunner_services"),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_member(name: str) -> PurePosixPath:
    """Normalize one archive member name and reject path escape forms."""
    member = PurePosixPath(name)
    while member.parts and member.parts[0] in {".", ""}:
        member = PurePosixPath(*member.parts[1:])
    if member.is_absolute() or not member.parts or ".." in member.parts:
        raise ValueError(f"unsafe Debian archive path: {name!r}")
    return member


def _is_selected_member(member: PurePosixPath) -> bool:
    return any(
        member == root or root in member.parents for root in _PACKAGE_ROOTS
    )


def _read_member_content(
    archive: tarfile.TarFile, info: tarfile.TarInfo
) -> bytes:
    """Read one regular member under per-file bounds."""
    if not info.isfile() or info.issym() or info.islnk():
        raise ValueError(f"non-regular selected source member: {info.name}")
    if info.size < 0 or info.size > 2 * 1024 * 1024:
        raise ValueError(
            f"selected source member size exceeds bound: {info.name}"
        )
    stream = archive.extractfile(info)
    if stream is None:
        raise ValueError(f"cannot read selected source member: {info.name}")
    content = stream.read(info.size + 1)
    if len(content) != info.size:
        raise ValueError(f"selected source member size mismatch: {info.name}")
    return content


def _read_archive_sources(
    deb_path: Path,
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    """Read bounded package members from the hash-pinned .deb archive."""
    result = subprocess.run(
        ["dpkg-deb", "--fsys-tarfile", str(deb_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if len(result.stdout) > _MAX_ARCHIVE_BYTES:
        raise ValueError("published Debian data archive exceeds size bound")

    sources: dict[str, bytes] = {}
    inventory: list[dict[str, Any]] = []
    total_bytes = 0
    with tarfile.open(
        fileobj=io.BytesIO(result.stdout), mode="r:*"
    ) as archive:
        for info in archive:
            if info.name in {".", "./"}:
                continue
            member = _canonical_member(info.name)
            if not _is_selected_member(member):
                continue
            if info.isdir():
                continue
            if len(sources) >= _MAX_SELECTED_FILES:
                raise ValueError(
                    "published package source file count exceeds bound"
                )
            total_bytes += info.size
            if total_bytes > _MAX_SELECTED_BYTES:
                raise ValueError("selected package source bytes exceed bound")
            key = member.as_posix()
            if key in sources:
                raise ValueError(f"duplicate package source member: {key}")
            content = _read_member_content(archive, info)
            sources[key] = content
            inventory.append(
                {
                    "path": key,
                    "size_bytes": len(content),
                    "sha256": _sha256_bytes(content),
                }
            )

    required = {
        "usr/lib/python3/dist-packages/airunner_services/__init__.py",
        "usr/lib/python3/dist-packages/airunner_services/database/alembic.ini",
        "usr/lib/python3/dist-packages/airunner_services/database/alembic/env.py",
        "usr/lib/python3/dist-packages/airunner_common/__init__.py",
    }
    missing = sorted(required - sources.keys())
    if missing:
        raise ValueError(
            f"published package source is missing required files: {missing}"
        )
    migration_prefix = "usr/lib/python3/dist-packages/airunner_services/database/alembic/versions/"
    revisions = [
        name
        for name in sources
        if name.startswith(migration_prefix) and name.endswith(".py")
    ]
    if len(revisions) != _EXPECTED_MIGRATION_COUNT:
        raise ValueError(
            f"published migration count differs: {len(revisions)} != {_EXPECTED_MIGRATION_COUNT}"
        )
    inventory.sort(key=lambda item: item["path"])
    return sources, inventory


def _extract_sources(sources: dict[str, bytes], root: Path) -> Path:
    """Write only previously verified package members under a fresh root."""
    if (
        root.is_symlink()
        or not root.is_dir()
        or next(root.iterdir(), None) is not None
    ):
        raise FileExistsError(
            f"baseline source directory is not a fresh directory: {root}"
        )
    for name, content in sources.items():
        member = PurePosixPath(name)
        target = root.joinpath(*member.parts[4:])
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"source member escapes temporary tree: {name}")
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"duplicate extracted source path: {target}")
        target.write_bytes(content)
        target.chmod(0o600)
    package_root = root / "airunner_services"
    return package_root


def _revision_parents(value: object, path: Path) -> tuple[str, ...]:
    """Normalize and validate one Alembic down_revision value."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple) and all(
        isinstance(parent, str) for parent in value
    ):
        return value
    raise ValueError(f"invalid migration parent field: {path.name}")


def _revision_fields(path: Path) -> tuple[str, tuple[str, ...]]:
    """Parse one migration's literal revision identifiers without imports."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid migration source file: {path}")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in {
                "revision",
                "down_revision",
            }:
                continue
            try:
                values[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    revision = values.get("revision")
    if not isinstance(revision, str):
        raise ValueError(f"invalid migration revision: {path.name}")
    return revision, _revision_parents(values.get("down_revision"), path)


def _graph_heads(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Require a closed graph and return its sorted heads."""
    all_parents = {parent for parents in graph.values() for parent in parents}
    missing_parents = all_parents - graph.keys()
    if missing_parents:
        raise ValueError(
            f"migration graph references missing revisions: {sorted(missing_parents)}"
        )
    return tuple(
        sorted(revision for revision in graph if revision not in all_parents)
    )


def _migration_graph_digest(graph: dict[str, tuple[str, ...]]) -> str:
    """Hash normalized revision-parent data in stable order."""
    canonical = json.dumps(
        [
            {"revision": revision, "parents": list(graph[revision])}
            for revision in sorted(graph)
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def _migration_graph(package_root: Path) -> tuple[tuple[str, ...], str]:
    """Read revision metadata without importing or executing migration modules."""
    revisions_dir = package_root / "database/alembic/versions"
    graph: dict[str, tuple[str, ...]] = {}
    for path in sorted(revisions_dir.glob("*.py")):
        revision, parents = _revision_fields(path)
        if revision in graph:
            raise ValueError(f"duplicate migration revision: {path.name}")
        graph[revision] = parents
    heads = _graph_heads(graph)
    if heads != _EXPECTED_BASELINE_HEADS:
        raise ValueError(f"published migration heads differ: {heads!r}")
    return heads, _migration_graph_digest(graph)


def _insert_synthetic_data(database: Path) -> dict[str, Any]:
    """Insert synthetic retained application data and a migration marker."""
    payload = json.dumps(
        [
            {
                "name": "Synthetic User",
                "role": "user",
                "content": "published-upgrade-marker-v1",
            },
            {
                "name": "AIRunner",
                "role": "user",
                "content": "synthetic conversation fixture",
            },
        ],
        separators=(",", ":"),
    )
    connection = sqlite3.connect(database, timeout=15)
    try:
        columns = {
            row[1]: {
                "notnull": bool(row[3]),
                "default": row[4],
                "pk": bool(row[5]),
            }
            for row in connection.execute("PRAGMA table_info(conversations)")
        }
        required = {"value", "chatbot_name", "user_name"}
        if not required.issubset(columns):
            raise ValueError(
                "published baseline lacks expected conversations schema"
            )
        values: dict[str, object] = {
            "value": payload,
            "chatbot_name": "Synthetic AIRunner",
            "user_name": "Synthetic User",
            "title": "published-baseline-upgrade-marker-v1",
            "summary": "Synthetic retained conversation summary.",
            "status": "synthetic",
        }
        for name, column in columns.items():
            if (
                column["pk"]
                or not column["notnull"]
                or column["default"] is not None
            ):
                continue
            if name not in values:
                raise ValueError(
                    f"unsupported required conversation column: {name}"
                )
        selected = [name for name in values if name in columns]
        placeholders = ", ".join("?" for _ in selected)
        quoted = ", ".join(f'"{name}"' for name in selected)
        cursor = connection.execute(
            f"INSERT INTO conversations ({quoted}) VALUES ({placeholders})",
            [values[name] for name in selected],
        )
        row_id = int(cursor.lastrowid)
        connection.execute(
            "CREATE TABLE core_upgrade_fixture "
            "(marker TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO core_upgrade_fixture(marker, payload) VALUES (?, ?)",
            ("synthetic-marker", _FIXTURE_PAYLOAD),
        )
        connection.commit()
    finally:
        connection.close()
    return {
        "conversation_id": row_id,
        "conversation_title": "published-baseline-upgrade-marker-v1",
        "conversation_summary": "Synthetic retained conversation summary.",
        "conversation_payload": payload,
        "fixture_payload": _FIXTURE_PAYLOAD,
    }


def _checkpoint_database(database: Path) -> None:
    connection = sqlite3.connect(database, timeout=15)
    try:
        result = connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        if result is not None and result[0] != 0:
            raise RuntimeError(
                "baseline fixture SQLite WAL checkpoint was busy"
            )
        mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
        if mode is None or mode[0].lower() != "delete":
            raise RuntimeError(
                "baseline fixture journal mode did not become DELETE"
            )
    finally:
        connection.close()
    if any(
        database.with_name(database.name + suffix).exists()
        for suffix in ("-wal", "-shm")
    ):
        raise RuntimeError("baseline fixture SQLite sidecar remains")


def _run_published_migrations(
    package_root: Path,
    source_root: Path,
    database: Path,
    data_root: Path,
) -> None:
    """Run the archived migration environment in a credential-free child."""
    null_keyring = source_root / "test-null-keyring"
    null_keyring.mkdir(mode=0o700)
    (null_keyring / "keyring.py").write_text(
        'raise ImportError("keyring disabled for synthetic migration fixture")\n',
        encoding="utf-8",
    )
    env_keys = (
        "PATH",
        "HOME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "HF_HUB_OFFLINE",
        "HF_DATASETS_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "CUDA_VISIBLE_DEVICES",
    )
    child_env = {key: os.environ[key] for key in env_keys if key in os.environ}
    database_url = f"sqlite:///{database.as_posix()}"
    child_env.update(
        {
            "AIRUNNER_BASE_PATH": str(data_root),
            "AIRUNNER_USER_DATA_PATH": str(data_root),
            "AIRUNNER_DATA_DIR": str(data_root / "data"),
            "AIRUNNER_DATABASE_URL": database_url,
            "DATABASE_URL": database_url,
            "AIRUNNER_MIGRATION_RUNNING": "1",
            "PYTHONPATH": os.pathsep.join(
                (str(null_keyring), str(source_root))
            ),
            "PYTHONNOUSERSITE": "1",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--migrate-only",
            "--package-root",
            str(package_root),
            "--source-root",
            str(source_root),
            "--expected-heads",
            ",".join(_EXPECTED_BASELINE_HEADS),
            "--database-url",
            database_url,
            "--base-path",
            str(data_root),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        env=child_env,
    )
    if result.returncode:
        detail = (result.stdout + "\n" + result.stderr)[-6000:]
        raise RuntimeError(f"published migration subprocess failed: {detail}")


def create_fixture(
    deb_path: Path,
    output_dir: Path,
    data_root: Path,
    source_sha: str,
    expected_deb_sha256: str,
) -> dict[str, Any]:
    """Build and record a fixture using the exact published baseline code."""
    if not _SOURCE_SHA.fullmatch(source_sha):
        raise ValueError(
            "candidate source SHA must be 40 lowercase hex characters"
        )
    if expected_deb_sha256 != _EXPECTED_DEB_SHA256:
        raise ValueError(
            "expected Debian baseline digest is not the reviewed pin"
        )
    if not deb_path.is_file() or deb_path.is_symlink():
        raise ValueError("published baseline package must be a regular file")
    deb_sha = _sha256_bytes(deb_path.read_bytes())
    if deb_sha != expected_deb_sha256:
        raise ValueError("published baseline package digest mismatch")
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"fixture output already exists: {output_dir}")
    if data_root.exists() or data_root.is_symlink():
        raise FileExistsError(
            f"migration data path already exists: {data_root}"
        )
    output_dir.mkdir(mode=0o700, parents=True)
    data_root.mkdir(mode=0o700)
    database = output_dir / "airunner.db"
    database_url = f"sqlite:///{database.as_posix()}"
    os.environ["AIRUNNER_BASE_PATH"] = str(data_root)
    os.environ["AIRUNNER_USER_DATA_PATH"] = str(data_root)
    os.environ["AIRUNNER_DATA_DIR"] = str(data_root / "data")
    os.environ["AIRUNNER_DATABASE_URL"] = database_url
    os.environ["DATABASE_URL"] = database_url
    os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"

    sources, inventory = _read_archive_sources(deb_path)
    source_payload = json.dumps(
        inventory, sort_keys=True, separators=(",", ":")
    ).encode()
    migration_prefix = "usr/lib/python3/dist-packages/airunner_services/database/alembic/versions/"
    migration_inventory = [
        item
        for item in inventory
        if item["path"].startswith(migration_prefix)
        and item["path"].endswith(".py")
    ]
    migration_payload = json.dumps(
        migration_inventory, sort_keys=True, separators=(",", ":")
    ).encode()
    with tempfile.TemporaryDirectory(
        prefix="airunner-published-source-"
    ) as temporary:
        source_root = Path(temporary)
        package_root = _extract_sources(sources, source_root)
        heads, graph_sha = _migration_graph(package_root)
        _run_published_migrations(
            package_root, source_root, database, data_root
        )

    connection = sqlite3.connect(database, timeout=15)
    try:
        actual_heads = tuple(
            row[0]
            for row in connection.execute(
                "SELECT version_num FROM alembic_version ORDER BY version_num"
            )
        )
    finally:
        connection.close()
    if actual_heads != heads:
        raise RuntimeError(
            f"baseline fixture heads differ after migration: {actual_heads!r}"
        )
    retained = _insert_synthetic_data(database)
    _checkpoint_database(database)

    record: dict[str, Any] = {
        "schema_version": 1,
        "fixture_kind": "published_prior_debian_schema",
        "fixture_payload": retained["fixture_payload"],
        "source_sha": source_sha,
        "baseline_package": {
            "package": _EXPECTED_PACKAGE,
            "version": _EXPECTED_VERSION,
            "filename": deb_path.name,
            "sha256": deb_sha,
            "source_revision": None,
            "source_identity_note": "The published Debian metadata does not bind this package to a source commit.",
        },
        "package_source_inventory": {
            "file_count": len(inventory),
            "sha256": _sha256_bytes(source_payload),
        },
        "migration_source_inventory": {
            "file_count": len(migration_inventory),
            "sha256": _sha256_bytes(migration_payload),
            "revision_count": _EXPECTED_MIGRATION_COUNT,
            "graph_sha256": graph_sha,
            "heads_before_candidate_upgrade": list(heads),
            "files": migration_inventory,
        },
        "database_filename": database.name,
        "database_sha256": _sha256_bytes(database.read_bytes()),
        "synthetic_conversation": {
            "id": retained["conversation_id"],
            "title": retained["conversation_title"],
            "summary": retained["conversation_summary"],
            "payload": retained["conversation_payload"],
        },
        "limitations": [
            "The database is synthetic and was created by the exact migration files in the hash-pinned published baseline package.",
            "The source package's optional keyring integration was explicitly unavailable; no credentials or real keyring were used.",
            "No production database, model, or model download was used.",
        ],
    }
    (output_dir / "fixture.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--migrate-only", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--expected-heads")
    parser.add_argument("--database-url")
    parser.add_argument("--base-path", type=Path)
    parser.add_argument("--baseline-deb", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--expected-deb-sha256")
    args = parser.parse_args()
    if args.migrate_only:
        if any(
            value is None
            for value in (
                args.package_root,
                args.source_root,
                args.expected_heads,
                args.database_url,
                args.base_path,
            )
        ):
            parser.error(
                "--migrate-only requires package root, source root, heads, database URL, and base path"
            )
        package_root = args.package_root.resolve()
        source_root = args.source_root.resolve()
        if not package_root.is_relative_to(source_root):
            parser.error(
                "package root must be inside the temporary source root"
            )
        os.environ["AIRUNNER_BASE_PATH"] = str(args.base_path)
        os.environ["AIRUNNER_USER_DATA_PATH"] = str(args.base_path)
        os.environ["AIRUNNER_DATA_DIR"] = str(args.base_path / "data")
        os.environ["AIRUNNER_DATABASE_URL"] = args.database_url
        os.environ["DATABASE_URL"] = args.database_url
        os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"
        import airunner_common
        import airunner_services
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from airunner_services.database.secret_store import keyring_available

        if Path(airunner_services.__file__).resolve().parent != package_root:
            raise RuntimeError(
                "baseline service imports did not resolve to verified archive files"
            )
        if (
            Path(airunner_common.__file__).resolve().parent
            != source_root / "airunner_common"
        ):
            raise RuntimeError(
                "baseline common imports did not resolve to verified archive files"
            )
        if keyring_available():
            raise RuntimeError(
                "test keyring isolation did not disable the optional backend"
            )
        expected_heads = tuple(sorted(args.expected_heads.split(",")))
        config = Config(str(package_root / "database/alembic.ini"))
        config.set_main_option(
            "script_location", str(package_root / "database/alembic")
        )
        config.set_main_option("sqlalchemy.url", args.database_url)
        graph = ScriptDirectory.from_config(config)
        if tuple(sorted(graph.get_heads())) != expected_heads:
            raise RuntimeError(
                "loaded baseline Alembic graph differs from the verified AST graph"
            )
        command.upgrade(config, "heads")
        return 0

    if any(
        value is None
        for value in (
            args.baseline_deb,
            args.output_dir,
            args.base_path,
            args.source_sha,
            args.expected_deb_sha256,
        )
    ):
        parser.error(
            "baseline-deb, output-dir, base-path, source-sha, and expected-deb-sha256 are required"
        )
    record = create_fixture(
        args.baseline_deb,
        args.output_dir,
        args.base_path,
        args.source_sha,
        args.expected_deb_sha256,
    )
    summary = {
        "fixture_kind": record["fixture_kind"],
        "source_sha": record["source_sha"],
        "database_sha256": record["database_sha256"],
        "baseline_package": record["baseline_package"],
        "migration_source_inventory": {
            key: record["migration_source_inventory"][key]
            for key in (
                "file_count",
                "sha256",
                "revision_count",
                "graph_sha256",
                "heads_before_candidate_upgrade",
            )
        },
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
