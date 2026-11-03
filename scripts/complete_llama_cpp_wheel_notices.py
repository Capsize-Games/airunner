"""Complete the reviewed llama.cpp license files in the exact CUDA wheel."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any


WHEEL_NAME = "llama_cpp_python-0.3.21+capsize.3-py3-none-linux_x86_64.whl"
DIST_INFO = "llama_cpp_python-0.3.21+capsize.3.dist-info"
EXPECTED_WHEEL_SHA256 = "ef4d73c5fbdf3731968b1ebd27f609567c1662ade843322a8d690a614abbf3aa"
EXPECTED_WHEEL_SIZE = 155743277
EXPECTED_ARTIFACT_SHA256 = "479dd565f8c0e04a6f438806933f7ef0a60b13a694dbd29d712389c981dfc5c1"
EXPECTED_ARTIFACT_SIZE = 154461319
EXPECTED_BUILD_MANIFEST_SHA256 = "92b38e1ece8a0794fe074dcfeecd2b3062601703c3cf527d052f2ed27aa8f39d"
EXPECTED_BUILD_MANIFEST_SIZE = 5479
WRAPPER_REPOSITORY = "Capsize-Games/llama-cpp-python-maintenance"
WRAPPER_REVISION = "5156c34af6d4920cddc5aba75618b1dd1c23e590"
WRAPPER_MEMBER_PATH = "llama_cpp/__init__.py"
WRAPPER_EVIDENCE_PATH = "packaging/licenses/llama-cpp-python-0.3.21-capsize.3-wheel-provenance/llama_cpp__init__.py"
WRAPPER_MEMBER_GIT_BLOB = "eb05a9600a8fb605600a5a949e844649082cd259"
WRAPPER_MEMBER_SHA256 = "8e6a465ddb2f9a0bb0736627183e9a4f46263e2aa541ee6a42b6402dbdb37ef3"
BACKEND_REPOSITORY = "ggml-org/llama.cpp"
BACKEND_REVISION = "7acb4e8cd2ce21f457d1298e75fad729520d263c"
MAX_WHEEL_SIZE = 1024 * 1024 * 1024
MAX_MANIFEST_SIZE = 256 * 1024
MAX_NOTICE_SIZE = 5 * 1024 * 1024
MAX_MEMBER_COUNT = 20_000
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_NOTICES = {
    "llama.cpp/LICENSE": (
        "LICENSE-llama.cpp.txt",
        "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d",
        1078,
    ),
    "llama.cpp/licenses/LICENSE-jsonhpp": (
        "LICENSE-jsonhpp.txt",
        "c0d068392ea65358b798b8c165103560f06e9e3b38c4ab4e2d8810a7b931af86",
        1075,
    ),
}
BUILD_FIELDS = {
    "wrapper_commit": "d2bcbac46605f11d382426dd88d67e8b5c124cd7",
    "llama_cpp_commit": BACKEND_REVISION,
    "wrapper_patch_sha256": "0f8dca544d67ea72851daab1c6116fdb4b6dc96f72a30bb7dbfde5bc3e91205b",
    "wrapper_version": "0.3.21+capsize.3",
    "cuda_arch": "120a-real",
    "network_during_compile": "none",
    "model_or_gpu_execution": "none",
}


class NoticeWheelError(ValueError):
    """Raised when pinned transformation inputs or wheel bytes are inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NoticeWheelError("transform input manifest repeats a JSON key")
        result[key] = value
    return result


def _safe_member(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
    ):
        raise NoticeWheelError(f"{label} is not a canonical relative path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise NoticeWheelError(f"{label} is not a canonical relative path")
    return PurePosixPath(*parts).as_posix()


def _read_evidence(root: Path, relative: Any, label: str, max_bytes: int) -> bytes:
    safe = _safe_member(relative, label)
    target = root.joinpath(*PurePosixPath(safe).parts)
    current = root
    for part in PurePosixPath(safe).parts:
        current = current / part
        if current.is_symlink():
            raise NoticeWheelError(f"{label} contains a symlink")
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        size = target.stat().st_size
        if not target.is_file() or size > max_bytes:
            raise NoticeWheelError(f"{label} is missing or exceeds its size limit")
        content = target.read_bytes()
    except (OSError, ValueError) as exc:
        raise NoticeWheelError(f"{label} is missing or escapes its evidence root") from exc
    if len(content) != size:
        raise NoticeWheelError(f"{label} changed while being read")
    return content


def _hash_streams_equal(left, right) -> bool:
    while True:
        a = left.read(1024 * 1024)
        b = right.read(1024 * 1024)
        if a != b:
            return False
        if not a:
            return True


def _manifest_inputs(manifest_path: Path) -> tuple[dict[str, Any], bytes, dict[str, bytes]]:
    try:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise NoticeWheelError("transform input manifest is missing or unsafe")
        raw = manifest_path.read_bytes()
        if len(raw) > MAX_MANIFEST_SIZE:
            raise NoticeWheelError("transform input manifest exceeds its size limit")
        manifest = json.loads(raw, object_pairs_hook=_strict_object)
    except NoticeWheelError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NoticeWheelError("transform input manifest is unreadable") from exc

    required = {
        "schema_version",
        "purpose",
        "distribution",
        "input_wheel",
        "producer_artifact",
        "build_manifest",
        "wrapper_source",
        "backend_source",
        "notices",
        "metadata",
    }
    if not isinstance(manifest, dict) or set(manifest) != required or manifest["schema_version"] != 1:
        raise NoticeWheelError("transform input manifest has an unsupported schema")
    if manifest["distribution"] != {"name": "llama_cpp_python", "version": "0.3.21+capsize.3"}:
        raise NoticeWheelError("transform input package identity differs")
    if manifest["purpose"] != "offline-notice-completion-inputs; not source or build provenance for the output wheel":
        raise NoticeWheelError("transform input manifest purpose is invalid")

    wheel = manifest["input_wheel"]
    if wheel != {"filename": WHEEL_NAME, "sha256": EXPECTED_WHEEL_SHA256, "size_bytes": EXPECTED_WHEEL_SIZE}:
        raise NoticeWheelError("compiled wheel is not the reviewed CI input")

    producer = manifest["producer_artifact"]
    expected_producer = {
        "repository": "Capsize-Games/airunner",
        "run_id": 41545665728,
        "artifact_id": 13189084154,
        "name": "llama-cpp-python-cu129-sm120a",
        "archive_sha256": EXPECTED_ARTIFACT_SHA256,
        "archive_size_bytes": EXPECTED_ARTIFACT_SIZE,
        "expires_at": "2026-11-16T23:52:35Z",
    }
    if producer != expected_producer:
        raise NoticeWheelError("producer Actions artifact identity differs from verified run")

    build = manifest["build_manifest"]
    if build != {
        "archive_member": "BUILD-MANIFEST.txt",
        "sha256": EXPECTED_BUILD_MANIFEST_SHA256,
        "size_bytes": EXPECTED_BUILD_MANIFEST_SIZE,
        "expected_fields": BUILD_FIELDS,
    }:
        raise NoticeWheelError("build manifest identity differs from verified CI output")

    wrapper = manifest["wrapper_source"]
    expected_wrapper = {
        "repository": WRAPPER_REPOSITORY,
        "revision": WRAPPER_REVISION,
        "member_path": WRAPPER_MEMBER_PATH,
        "git_blob_oid": WRAPPER_MEMBER_GIT_BLOB,
        "sha256": WRAPPER_MEMBER_SHA256,
        "size_bytes": 80,
        "evidence_path": WRAPPER_EVIDENCE_PATH,
    }
    if not isinstance(expected_wrapper["evidence_path"], str) or wrapper != expected_wrapper:
        raise NoticeWheelError("wrapper Git member identity differs from reviewed private source")

    backend = manifest["backend_source"]
    if backend != {
        "gitlink_path": "vendor/llama.cpp",
        "repository": BACKEND_REPOSITORY,
        "revision": BACKEND_REVISION,
    }:
        raise NoticeWheelError("backend gitlink identity differs from reviewed source")

    metadata = manifest["metadata"]
    if metadata != {
        "metadata_version": "2.4",
        "license_files": ["LICENSE.md", "llama.cpp/LICENSE", "llama.cpp/licenses/LICENSE-jsonhpp"],
        "wrapper_license_sha256": "c479fb11a66a85fed2004a17dd1b3e44a1858c564b167aecb20ff66cb422ed75",
        "wrapper_license_size_bytes": 1069,
    }:
        raise NoticeWheelError("output metadata declaration differs from the reviewed notice set")

    root = manifest_path.parents[3]
    member = _read_evidence(root, wrapper["evidence_path"], "wrapper package member evidence", MAX_NOTICE_SIZE)
    git_blob_oid = hashlib.sha1(b"blob " + str(len(member)).encode("ascii") + b"\0" + member).hexdigest()
    if len(member) != wrapper["size_bytes"] or sha256_bytes(member) != wrapper["sha256"] or git_blob_oid != wrapper["git_blob_oid"]:
        raise NoticeWheelError("wrapper evidence does not match the recorded Git blob")

    rows = manifest["notices"]
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_NOTICES):
        raise NoticeWheelError("transform input has an incomplete backend notice set")
    notices: dict[str, bytes] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "evidence_path",
            "upstream_repository",
            "upstream_revision",
            "upstream_path",
            "wheel_path",
            "sha256",
            "size_bytes",
        }:
            raise NoticeWheelError("transform input notice record has an unsupported schema")
        expected = EXPECTED_NOTICES.get(row.get("wheel_path")) if isinstance(row, dict) else None
        if expected is None:
            raise NoticeWheelError("transform input has an unexpected notice path")
        filename, digest, size = expected
        if (
            row.get("evidence_path") != f"packaging/licenses/llama-cpp-python-0.3.21-capsize.3-wheel-provenance/{filename}"
            or row.get("upstream_repository") != BACKEND_REPOSITORY
            or row.get("upstream_revision") != BACKEND_REVISION
            or row.get("upstream_path") != row["wheel_path"].removeprefix("llama.cpp/")
            or row.get("sha256") != digest
            or row.get("size_bytes") != size
        ):
            raise NoticeWheelError("backend notice provenance differs from reviewed source bytes")
        content = _read_evidence(root, row["evidence_path"], "backend license notice", MAX_NOTICE_SIZE)
        if len(content) != size or sha256_bytes(content) != digest:
            raise NoticeWheelError("backend license notice bytes differ from reviewed hashes")
        notices[row["wheel_path"]] = content
    if set(notices) != set(EXPECTED_NOTICES):
        raise NoticeWheelError("transform input repeats a backend notice path")

    return manifest, raw, {wrapper["member_path"]: member, **notices}


def _verify_build_artifact(manifest: dict[str, Any], artifact_path: Path, input_wheel: Path) -> bytes:
    producer = manifest["producer_artifact"]
    if (
        artifact_path.is_symlink()
        or not artifact_path.is_file()
        or artifact_path.stat().st_size != producer["archive_size_bytes"]
        or sha256_file(artifact_path) != producer["archive_sha256"]
    ):
        raise NoticeWheelError("CI artifact ZIP hash or size differs from the verified artifact record")
    try:
        with zipfile.ZipFile(artifact_path) as artifact:
            names = artifact.namelist()
            if names != ["BUILD-MANIFEST.txt", WHEEL_NAME] or artifact.testzip() is not None:
                raise NoticeWheelError("CI artifact ZIP members or CRC are invalid")
            build_manifest = artifact.read("BUILD-MANIFEST.txt")
            if len(build_manifest) != manifest["build_manifest"]["size_bytes"] or sha256_bytes(build_manifest) != manifest["build_manifest"]["sha256"]:
                raise NoticeWheelError("BUILD-MANIFEST bytes differ from the verified CI receipt")
            fields = {}
            for line in build_manifest.decode("utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    fields[key] = value
            if any(fields.get(key) != value for key, value in BUILD_FIELDS.items()):
                raise NoticeWheelError("BUILD-MANIFEST does not describe the reviewed source/build inputs")
            with artifact.open(WHEEL_NAME) as bundled_wheel, input_wheel.open("rb") as selected_wheel:
                if not _hash_streams_equal(bundled_wheel, selected_wheel):
                    raise NoticeWheelError("selected wheel bytes differ from the exact CI artifact member")
            return build_manifest
    except zipfile.BadZipFile as exc:
        raise NoticeWheelError("CI artifact is not a valid ZIP") from exc


def _record_row(path: str, content: bytes) -> tuple[str, str, str]:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode("ascii").rstrip("=")
    return path, f"sha256={encoded}", str(len(content))


def _read_and_verify_record(source: zipfile.ZipFile, names: list[str], record_name: str) -> list[list[str]]:
    try:
        rows = list(csv.reader(io.StringIO(source.read(record_name).decode("utf-8"))))
    except (KeyError, UnicodeDecodeError, csv.Error) as exc:
        raise NoticeWheelError("input wheel RECORD is unreadable") from exc
    if any(len(row) != 3 for row in rows) or len({row[0] for row in rows}) != len(rows):
        raise NoticeWheelError("input wheel RECORD has malformed or duplicate rows")
    mapping = {row[0]: row for row in rows}
    if set(mapping) != set(names):
        raise NoticeWheelError("input wheel RECORD does not cover exactly its ZIP members")
    for name in names:
        row = mapping[name]
        content = source.read(name)
        if name == record_name:
            if row[1:] != ["", ""]:
                raise NoticeWheelError("input wheel RECORD self-row is invalid")
        elif row != list(_record_row(name, content)):
            raise NoticeWheelError("input wheel RECORD hash or size is invalid")
    return rows


def complete_wheel(input_wheel: Path, artifact_path: Path, input_manifest: Path, output_wheel: Path, receipt_path: Path) -> dict[str, Any]:
    protected_inputs = {input_wheel.resolve(), artifact_path.resolve(), input_manifest.resolve()}
    if output_wheel.resolve() in protected_inputs or receipt_path.resolve() in protected_inputs or output_wheel.resolve() == receipt_path.resolve():
        raise NoticeWheelError("output and receipt paths must be separate from all inputs and each other")
    if output_wheel.exists() or output_wheel.is_symlink() or receipt_path.exists() or receipt_path.is_symlink():
        raise NoticeWheelError("output wheel or receipt already exists")
    manifest, manifest_bytes, evidence = _manifest_inputs(input_manifest)
    wheel_spec = manifest["input_wheel"]
    if (
        input_wheel.name != WHEEL_NAME
        or input_wheel.is_symlink()
        or not input_wheel.is_file()
        or input_wheel.stat().st_size != wheel_spec["size_bytes"]
        or input_wheel.stat().st_size > MAX_WHEEL_SIZE
        or sha256_file(input_wheel) != wheel_spec["sha256"]
    ):
        raise NoticeWheelError("input wheel hash or filename differs from the exact reviewed CI wheel")
    build_manifest = _verify_build_artifact(manifest, artifact_path, input_wheel)
    output_wheel.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if output_wheel.resolve() == input_wheel.resolve():
        raise NoticeWheelError("output wheel must not replace the CI input")
    if output_wheel.parent.resolve() == input_wheel.parent.resolve():
        raise NoticeWheelError("output wheel must use a separate directory")

    metadata_name = f"{DIST_INFO}/METADATA"
    record_name = f"{DIST_INFO}/RECORD"
    wrapper_license_name = f"{DIST_INFO}/licenses/LICENSE.md"
    with zipfile.ZipFile(input_wheel, "r") as source:
        infos = source.infolist()
        names = [_safe_member(info.filename, "input wheel member") for info in infos]
        if len(infos) > MAX_MEMBER_COUNT or len(names) != len(set(names)) or source.testzip() is not None:
            raise NoticeWheelError("input wheel has duplicate members, too many members or a bad CRC")
        original_record_rows = _read_and_verify_record(source, names, record_name)
        if metadata_name not in names or wrapper_license_name not in names:
            raise NoticeWheelError("input wheel is missing METADATA or its wrapper MIT license")
        original_members = {name: source.read(name) for name in names}
        if original_members["llama_cpp/__init__.py"] != evidence["llama_cpp/__init__.py"]:
            raise NoticeWheelError("wheel package member differs from the exact private Git blob")
        wrapper_license = original_members[wrapper_license_name]
        if len(wrapper_license) != 1069 or sha256_bytes(wrapper_license) != "c479fb11a66a85fed2004a17dd1b3e44a1858c564b167aecb20ff66cb422ed75":
            raise NoticeWheelError("wheel wrapper MIT notice differs from the verified source notice")

        metadata = original_members[metadata_name]
        if metadata.count(b"Metadata-Version: 2.1\n") != 1:
            raise NoticeWheelError("input wheel metadata version differs from the reviewed artifact")
        if b"Name: llama_cpp_python\n" not in metadata or b"Version: 0.3.21+capsize.3\n" not in metadata:
            raise NoticeWheelError("input wheel package metadata identity differs")
        if b"License-File:" in metadata:
            raise NoticeWheelError("input wheel unexpectedly already declares License-File headers")
        metadata = metadata.replace(b"Metadata-Version: 2.1\n", b"Metadata-Version: 2.4\n", 1)
        declarations = (
            b"License-File: LICENSE.md\n"
            b"License-File: llama.cpp/LICENSE\n"
            b"License-File: llama.cpp/licenses/LICENSE-jsonhpp\n"
        )
        metadata = metadata.replace(b"\n\n", b"\n" + declarations + b"\n", 1)

        members = {name: data for name, data in original_members.items() if name != record_name}
        members[metadata_name] = metadata
        for wheel_path, content in evidence.items():
            if wheel_path == "llama_cpp/__init__.py":
                continue
            destination = f"{DIST_INFO}/licenses/{wheel_path}"
            if destination in members:
                raise NoticeWheelError("backend license destination already exists")
            members[destination] = content

        rows = [_record_row(name, data) for name, data in sorted(members.items())]
        rows.append((record_name, "", ""))
        record_stream = io.StringIO(newline="")
        csv.writer(record_stream, lineterminator="\n").writerows(rows)
        record = record_stream.getvalue().encode("utf-8")

        output_info = {info.filename: info for info in infos}
        record_info = output_info[record_name]
        fd, staged_name = tempfile.mkstemp(prefix=".notice-wheel-", suffix=".whl", dir=output_wheel.parent)
        os.close(fd)
        staged = Path(staged_name)
        try:
            with zipfile.ZipFile(staged, "w", allowZip64=True) as output:
                output.comment = source.comment
                for name in sorted(members):
                    old = output_info.get(name)
                    if old is None:
                        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = (stat.S_IFREG | 0o644) << 16
                        info.create_system = 3
                    else:
                        info = zipfile.ZipInfo(name, old.date_time)
                        info.compress_type = old.compress_type
                        info.external_attr = old.external_attr
                        info.create_system = old.create_system
                        info.flag_bits = old.flag_bits & ~0x08
                    output.writestr(info, members[name], compress_type=info.compress_type, compresslevel=9)
                output.writestr(record_info, record, compress_type=record_info.compress_type, compresslevel=9)

            with zipfile.ZipFile(staged, "r") as final:
                final_names = [_safe_member(name, "completed wheel member") for name in final.namelist()]
                if len(final_names) != len(set(final_names)) or final.testzip() is not None:
                    raise NoticeWheelError("completed wheel has invalid ZIP structure")
                for name in original_members:
                    if name != record_name and final.read(name) != members[name]:
                        raise NoticeWheelError("an original wheel member changed during notice packaging")
                final_rows = _read_and_verify_record(final, final_names, record_name)
                final_metadata = final.read(metadata_name).decode("utf-8")
                expected_fields = manifest["metadata"]["license_files"]
                actual_fields = [line.removeprefix("License-File: ") for line in final_metadata.splitlines() if line.startswith("License-File: ")]
                if actual_fields != expected_fields:
                    raise NoticeWheelError("completed wheel License-File metadata is incomplete or reordered")
                expected_names = {
                    f"{DIST_INFO}/licenses/{license_path}" for license_path in expected_fields
                }
                actual_license_names = {
                    name for name in final_names if name.startswith(f"{DIST_INFO}/licenses/")
                }
                if actual_license_names != expected_names:
                    raise NoticeWheelError("completed wheel license directory differs from metadata")
                output_member_count = len(final_names)
                output_record_count = len(final_rows)
                preserved_member_count = len(original_members) - 2
                if output_member_count != len(original_members) + 2 or output_record_count != len(original_record_rows) + 2:
                    raise NoticeWheelError("completed wheel member or RECORD row count differs from expected additions")

            os.replace(staged, output_wheel)
        finally:
            staged.unlink(missing_ok=True)

    result = {
        "schema_version": 1,
        "status": "notice-complete-derived-wheel; no source rebuild",
        "distribution": manifest["distribution"],
        "producer_artifact": manifest["producer_artifact"],
        "build_manifest_sha256": manifest["build_manifest"]["sha256"],
        "build_manifest_expected_fields": BUILD_FIELDS,
        "wrapper_source_binding": manifest["wrapper_source"],
        "backend_gitlink": manifest["backend_source"],
        "input_wheel": {
            "filename": input_wheel.name,
            "sha256": wheel_spec["sha256"],
            "size_bytes": input_wheel.stat().st_size,
        },
        "output_wheel": {
            "filename": output_wheel.name,
            "sha256": sha256_file(output_wheel),
            "size_bytes": output_wheel.stat().st_size,
        },
        "input_manifest_sha256": sha256_bytes(manifest_bytes),
        "artifact_zip_sha256": manifest["producer_artifact"]["archive_sha256"],
        "original_zip_member_count": len(original_members),
        "original_record_row_count": len(original_record_rows),
        "output_zip_member_count": output_member_count,
        "output_record_row_count": output_record_count,
        "preserved_original_member_count": preserved_member_count,
        "added_notice_files": [
            {"path": path, "sha256": sha256_bytes(data), "size_bytes": len(data)}
            for path, data in sorted(evidence.items())
            if path != WRAPPER_MEMBER_PATH
        ],
        "metadata": manifest["metadata"],
        "transformer": {
            "file": "scripts/complete_llama_cpp_wheel_notices.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "transform_toolchain": {
            "python_version": sys.version.split()[0],
            "zlib_version": zlib.ZLIB_VERSION,
            "compression_method": "ZIP_DEFLATED",
            "compression_level": 9,
        },
        "runtime_payload": "Original non-METADATA, non-RECORD wheel member bytes were preserved exactly; no source or native payload was rebuilt.",
    }
    receipt_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--build-artifact", required=True, type=Path)
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = complete_wheel(args.input, args.build_artifact, args.input_manifest, args.output, args.receipt)
    except (NoticeWheelError, OSError, zipfile.BadZipFile, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
