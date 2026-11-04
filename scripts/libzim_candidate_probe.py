#!/usr/bin/env python3
"""Verify and exercise the staged libzim candidate wheel without network access."""

from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

from runtime_wheel_hardening import checked_filename, checked_relative, verify_record


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_WHEEL_BYTES = 256 * 1024 * 1024
MAX_WHEEL_MEMBER_BYTES = 128 * 1024 * 1024
MAX_WHEEL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_SOURCE_FILE_BYTES = 512 * 1024 * 1024
SOURCE_BUNDLE_RELATIVE = "package/source-bundles/libzim-3.7.0-native-9.3.0"
WHEELHOUSE_RELATIVE = "package/wheelhouse"
SIDECAR_FILENAME = "libzim-3.7.0+capsize.2.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _version_ceiling(binary: Path, prefix: str) -> str | None:
    result = subprocess.run(
        ["readelf", "--version-info", str(binary)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    versions = re.findall(rf"\b{re.escape(prefix)}[0-9.]+", result.stdout)
    if not versions:
        return None
    return max(versions, key=lambda value: tuple(int(part) for part in value.split("_")[1].split(".")))


def _dynamic_info(binary: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["readelf", "-d", str(binary)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "needed": re.findall(r"\(NEEDED\).*?\[([^]]+)\]", result.stdout),
        "runpath": re.findall(r"\((?:RUNPATH|RPATH)\).*?\[([^]]+)\]", result.stdout),
        "glibc_ceiling": _version_ceiling(binary, "GLIBC_"),
        "glibcxx_ceiling": _version_ceiling(binary, "GLIBCXX_"),
    }


def _verify_wheel_archive(archive: zipfile.ZipFile) -> tuple[int, str, str, str, str, str]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise ValueError("wheel contains duplicate ZIP members")
    entries: dict[str, bytes] = {}
    total_uncompressed = 0
    file_names = set()
    directory_names = set()
    for info in infos:
        raw_name = info.filename
        is_directory = info.is_dir()
        name = raw_name[:-1] if is_directory else raw_name
        checked_relative(name)
        if info.flag_bits & 0x1:
            raise ValueError("wheel contains an encrypted ZIP member")
        if info.file_size > MAX_WHEEL_MEMBER_BYTES:
            raise ValueError(f"wheel member exceeds the probe size bound: {name}")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_WHEEL_UNCOMPRESSED_BYTES:
            raise ValueError("wheel uncompressed contents exceed the probe size bound")
        if info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError("wheel contains a symbolic-link member")
        if is_directory:
            directory_names.add(name)
            continue
        file_names.add(name)
        entries[name] = archive.read(info)
    if file_names & directory_names:
        raise ValueError("wheel member is both a file and a directory")
    for name in file_names:
        parts = name.split("/")
        if any("/".join(parts[:index]) in file_names for index in range(1, len(parts))):
            raise ValueError(f"wheel file is an ancestor of another member: {name}")

    record_names = [name for name in file_names if name.endswith(".dist-info/RECORD")]
    metadata_names = [name for name in file_names if name.endswith(".dist-info/METADATA")]
    native_members = [name for name in file_names if name.endswith("/libzim.so.9")]
    extension_members = [
        name for name in file_names
        if name.endswith(".so") and not name.endswith("/libzim.so.9")
    ]
    if len(record_names) != 1:
        raise ValueError("wheel must contain exactly one RECORD")
    if len(metadata_names) != 1:
        raise ValueError("wheel must contain exactly one METADATA file")
    if len(native_members) != 1:
        raise ValueError("wheel must contain exactly one bundled libzim.so.9")
    if len(extension_members) != 1:
        raise ValueError("wheel must contain exactly one Python extension module")
    if record_names[0].rsplit("/", 1)[0] != metadata_names[0].rsplit("/", 1)[0]:
        raise ValueError("wheel RECORD and METADATA must share a dist-info directory")

    verify_record(entries, record_names[0])
    metadata = BytesParser().parsebytes(entries[metadata_names[0]])
    if len(metadata.get_all("Name", [])) != 1 or len(metadata.get_all("Version", [])) != 1:
        raise ValueError("wheel METADATA must contain one Name and one Version field")
    return (
        len(entries) - 1,
        native_members[0],
        hashlib.sha256(entries[native_members[0]]).hexdigest(),
        metadata_names[0],
        extension_members[0],
        hashlib.sha256(entries[extension_members[0]]).hexdigest(),
    )


def _verify_wheel(wheel: Path, manifest_path: Path) -> dict[str, Any]:
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("candidate wheel must be a regular file, not a symlink")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("candidate sidecar must be a regular file, not a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("candidate sidecar schema is unsupported")
    checked_filename(manifest["filename"])
    if manifest_path.resolve() != REPO_ROOT / WHEELHOUSE_RELATIVE / SIDECAR_FILENAME:
        raise ValueError("candidate sidecar is not the reviewed libzim wheel sidecar")
    if wheel.resolve() != REPO_ROOT / WHEELHOUSE_RELATIVE / manifest["filename"]:
        raise ValueError("candidate wheel is not in the reviewed wheelhouse")
    if wheel.name != manifest["filename"]:
        raise ValueError("candidate wheel filename does not match its sidecar")
    if wheel.stat().st_size > MAX_WHEEL_BYTES:
        raise ValueError("candidate wheel exceeds the probe size bound")
    if wheel.stat().st_size != manifest["wheel_size"]:
        raise ValueError("candidate wheel size does not match its sidecar")
    actual_wheel_sha = _sha256(wheel)
    if actual_wheel_sha != manifest["wheel_sha256"]:
        raise ValueError("candidate wheel SHA-256 does not match its sidecar")

    with zipfile.ZipFile(wheel) as archive:
        (
            verified,
            _native_member,
            native_sha,
            metadata_name,
            extension_member,
            extension_sha,
        ) = _verify_wheel_archive(archive)
        if native_sha != manifest["native_libzim_sha256"]:
            raise ValueError("bundled libzim native library does not match the sidecar")
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        if metadata.get_all("Name") != [manifest["distribution"]]:
            raise ValueError("wheel METADATA distribution does not match the sidecar")
        if metadata.get_all("Version") != [manifest["version"]]:
            raise ValueError("wheel METADATA version does not match the sidecar")

    source_manifest_path = _repo_file(manifest["source_bundle_manifest_path"])
    expected_manifest_path = REPO_ROOT / SOURCE_BUNDLE_RELATIVE / "source-manifest.json"
    if source_manifest_path != expected_manifest_path:
        raise ValueError("sidecar points outside the reviewed libzim source bundle")
    source_archive = _repo_file(manifest["source_archive_path"])
    expected_bundle = REPO_ROOT / SOURCE_BUNDLE_RELATIVE
    if not source_archive.is_relative_to(expected_bundle):
        raise ValueError("sidecar source archive is outside the reviewed libzim source bundle")
    if _sha256(source_archive) != manifest["source_archive_sha256"]:
        raise ValueError("wrapper corresponding-source archive hash mismatch")
    if _sha256(source_manifest_path) != manifest["source_bundle_manifest_sha256"]:
        raise ValueError("source bundle manifest hash mismatch")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    wrapper_source = source_manifest["wrapper_source"]
    if wrapper_source["tree_sha"] != manifest["source_tree_sha"]:
        raise ValueError("wrapper source tree does not match the wheel sidecar")
    if wrapper_source["archive_path"] != str(source_archive.relative_to(source_manifest_path.parent)):
        raise ValueError("wrapper source manifest points to a different archive")
    if wrapper_source["archive_sha256"] != manifest["source_archive_sha256"]:
        raise ValueError("wrapper source manifest archive hash does not match the wheel sidecar")
    if wrapper_source["upstream_commit"] != manifest["python_wrapper_upstream_commit"]:
        raise ValueError("wrapper source upstream commit does not match the wheel sidecar")
    if wrapper_source["proposed_tag"] != manifest["python_wrapper_private_release_tag"]:
        raise ValueError("wrapper source proposed tag does not match the wheel sidecar")
    listed_paths: set[str] = set()
    for row in source_manifest["files"]:
        relative = checked_relative(row["path"]).as_posix()
        if relative in listed_paths:
            raise ValueError(f"duplicate source bundle manifest path: {relative}")
        listed_paths.add(relative)
        listed_path = _bundle_file(source_manifest_path.parent, relative)
        if row["bytes"] > MAX_SOURCE_FILE_BYTES or listed_path.stat().st_size != row["bytes"]:
            raise ValueError(f"source bundle file size mismatch for {relative}")
        if _sha256(listed_path) != row["sha256"]:
            raise ValueError(f"source bundle file hash mismatch for {relative}")
    matching_archives = [
        row for row in source_manifest["files"]
        if row["path"] == str(source_archive.relative_to(source_manifest_path.parent))
    ]
    if len(matching_archives) != 1:
        raise ValueError("source bundle manifest must bind the wrapper archive exactly once")
    matching_archive = matching_archives[0]
    if matching_archive["sha256"] != manifest["source_archive_sha256"]:
        raise ValueError("source manifest does not bind the wrapper archive")
    expected_files = listed_paths | {
        "source-manifest.json",
        "BUILDING.md",
        "candidate-build-receipt.json",
    }
    actual_files = set()
    for path in source_manifest_path.parent.rglob("*"):
        if path.is_symlink():
            raise ValueError("source bundle contains a symbolic link")
        if path.is_file():
            actual_files.add(path.relative_to(source_manifest_path.parent).as_posix())
    if actual_files != expected_files:
        raise ValueError(
            "source bundle inventory differs from its explicit manifest: "
            f"unlisted={sorted(actual_files - expected_files)}, "
            f"missing={sorted(expected_files - actual_files)}"
        )
    return {
        "wheel_sha256": actual_wheel_sha,
        "wheel_size": wheel.stat().st_size,
        "record_rows_verified": verified,
        "native_libzim_sha256": native_sha,
        "extension_member": extension_member,
        "extension_sha256": extension_sha,
        "source_tree_sha": manifest["source_tree_sha"],
        "source_bundle_manifest_sha256": manifest["source_bundle_manifest_sha256"],
        "source_archive_sha256": manifest["source_archive_sha256"],
        "version": manifest["version"],
    }


def _repo_file(value: str) -> Path:
    """Resolve a repository-relative artifact path without following links."""
    relative = checked_relative(value)
    return _bundle_file(REPO_ROOT, relative.as_posix())


def _bundle_file(root: Path, relative: str) -> Path:
    """Require a regular file below a bundle root with no symlink components."""
    checked = checked_relative(relative)
    current = root
    for part in checked.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"source bundle path traverses a symlink: {relative}")
    if not current.is_file():
        raise ValueError(f"source bundle file is missing or not regular: {relative}")
    return current


def _exercise_api(synthetic_path: Path) -> dict[str, Any]:
    from libzim.reader import Archive
    from libzim.search import Query, Searcher
    from libzim.writer import Creator, Hint, Item, StringProvider

    class _SyntheticItem(Item):
        def __init__(self, path: str, title: str, content: str) -> None:
            super().__init__()
            self._path = path
            self._title = title
            self._content = content

        def get_path(self) -> str:
            return self._path

        def get_title(self) -> str:
            return self._title

        def get_mimetype(self) -> str:
            return "text/html"

        def get_contentprovider(self) -> StringProvider:
            return StringProvider(self._content)

        def get_hints(self) -> dict[Hint, int]:
            return {Hint.FRONT_ARTICLE: True}

    token = "LIBZIMCANDIDATEPROBE"
    with Creator(synthetic_path).config_indexing(True, "eng") as creator:
        creator.set_mainpath("home")
        creator.add_item(
            _SyntheticItem(
                "home",
                "Candidate probe home",
                f"<html><body><h1>Synthetic ZIM</h1><p>{token}</p></body></html>",
            )
        )
        creator.add_item(
            _SyntheticItem(
                "article",
                "Candidate probe article",
                f"<html><body><p>Secondary page {token}</p></body></html>",
            )
        )
        creator.add_metadata("Title", "Synthetic libzim candidate probe")

    archive = Archive(synthetic_path)
    if archive.entry_count < 2 or not archive.has_fulltext_index:
        raise AssertionError("synthetic ZIM metadata or index is missing")
    main = archive.get_entry_by_path("home")
    content = main.get_item().content.tobytes().decode("utf-8")
    if token not in content:
        raise AssertionError("synthetic ZIM main entry content did not round-trip")
    results = Searcher(archive).search(Query().set_query(token)).getResults(0, 10)
    result_paths = list(results)
    if "home" not in result_paths:
        raise AssertionError("full-text search did not find the synthetic main entry")
    return {
        "entry_count": archive.entry_count,
        "has_fulltext_index": archive.has_fulltext_index,
        "read_path": main.path,
        "search_paths": result_paths,
        "synthetic_token": token,
    }


def _exercise_service_loader(synthetic_path: Path, source_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(source_root))
    missing = []
    for name in ("langchain_core.documents", "bs4", "airunner_common.settings"):
        try:
            present = importlib.util.find_spec(name) is not None
        except ModuleNotFoundError:
            present = False
        if not present:
            missing.append(name)
    if missing:
        return {"status": "not_run", "missing_modules": missing}

    from airunner_services.llm.managers.agent.document_loader import (
        iter_document_batches_from_file,
    )

    batches = list(
        iter_document_batches_from_file(
            str(synthetic_path), lambda _path: {"source": "synthetic candidate probe"}
        )
    )
    documents = [document for batch in batches for document in batch]
    if not documents or not any(
        "LIBZIMCANDIDATEPROBE" in document.page_content for document in documents
    ):
        raise AssertionError("service document loader did not return synthetic article text")
    for document in documents:
        if document.metadata.get("zim_file") != str(synthetic_path):
            raise AssertionError("service loader lost the source archive path")
        if not document.metadata.get("zim_path"):
            raise AssertionError("service loader lost the canonical ZIM article path")
    return {
        "status": "passed",
        "documents": len(documents),
        "metadata": documents[0].metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--service-source-root", type=Path)
    parser.add_argument("--common-source-root", type=Path)
    args = parser.parse_args()

    if args.common_source_root is not None:
        sys.path.insert(0, str(args.common_source_root))
    wheel_record = _verify_wheel(args.wheel, args.manifest)
    installed_version = importlib.metadata.version("libzim")
    if installed_version != wheel_record["version"]:
        raise ValueError("installed libzim version does not match the candidate sidecar")

    import libzim

    extension = Path(libzim.__file__).resolve()
    native = extension.parent / "libzim" / "libzim.so.9"
    if not extension.is_file() or not native.is_file():
        raise FileNotFoundError("installed wrapper extension or bundled native library is absent")
    extension_sha = _sha256(extension)
    native_sha = _sha256(native)
    if extension.name != wheel_record["extension_member"] or extension_sha != wheel_record["extension_sha256"]:
        raise ValueError("imported Python extension does not match the candidate wheel bytes")
    if native_sha != wheel_record["native_libzim_sha256"]:
        raise ValueError("imported native libzim does not match the candidate wheel bytes")
    extension_info = _dynamic_info(extension)
    native_info = _dynamic_info(native)
    for label, info in (("extension", extension_info), ("native library", native_info)):
        if info["glibc_ceiling"] is None or tuple(
            int(part) for part in info["glibc_ceiling"].split("_")[1].split(".")
        ) > (2, 39):
            raise ValueError(f"{label} exceeds the Ubuntu 24.04 glibc symbol ceiling")
        if info["glibcxx_ceiling"] is None or tuple(
            int(part) for part in info["glibcxx_ceiling"].split("_")[1].split(".")
        ) > (3, 4, 32):
            raise ValueError(f"{label} exceeds the reviewed libstdc++ symbol ceiling")

    with tempfile.TemporaryDirectory(prefix="libzim-candidate-probe-") as temp_dir:
        synthetic_path = Path(temp_dir) / "synthetic.zim"
        api = _exercise_api(synthetic_path)
        service = (
            _exercise_service_loader(synthetic_path, args.service_source_root)
            if args.service_source_root is not None
            else {"status": "not_run", "reason": "service source root not supplied"}
        )

    receipt = {
        "schema_version": 1,
        "status": "passed",
        "profile": "libzim-linux-candidate",
        "candidate": wheel_record,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "libc": platform.libc_ver(),
            "extension_path": str(extension),
            "extension_sha256": extension_sha,
            "extension_elf": extension_info,
            "native_path": str(native),
            "native_sha256": native_sha,
            "native_elf": native_info,
        },
        "synthetic_api": api,
        "service_loader": service,
        "exclusions": [
            "real ZIM corpus and private user data",
            "RAG model/embedding execution",
            "full service daemon startup",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
