#!/usr/bin/env python3
"""Build deterministic, hash-bound runtime wheel hardening candidates.

This helper never downloads, installs, imports, or loads a wheel. Inputs must
already be present in a caller-managed directory and match the reviewed SHA256.
ELF edits are delegated to the separately reviewed Patchelf binary.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile


EPOCH = (1980, 1, 1, 0, 0, 0)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def checked_relative(value: str) -> PurePosixPath:
    if (
        not isinstance(value, str) or not value or "\\" in value
        or "\x00" in value or ":" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"unsafe archive path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe archive path: {value!r}")
    return path


def checked_filename(value: str) -> str:
    """Require one wheel filename within its caller-selected directory."""
    path = checked_relative(value)
    if len(path.parts) != 1 or not value.endswith(".whl"):
        raise ValueError("wheel filename must be a single .whl filename")
    return value


def runpath_info(readelf: str, path: Path) -> tuple[str | None, list[str], list[str], list[str]]:
    output = subprocess.check_output([readelf, "-d", str(path)], text=True, stderr=subprocess.STDOUT, timeout=60)
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", output)
    soname = re.findall(r"\(SONAME\).*?\[([^]]+)\]", output)
    rpath = re.findall(r"\(RPATH\).*?\[([^]]*)\]", output)
    runpath = re.findall(r"\(RUNPATH\).*?\[([^]]*)\]", output)
    if rpath and runpath:
        raise ValueError(f"ELF has both RPATH and RUNPATH: {path}")
    kind = "RPATH" if rpath else "RUNPATH" if runpath else None
    values = (rpath or runpath)
    return kind, (values[0].split(":") if values else []), needed, soname


def rewrite_record(entries: dict[str, bytes], record_path: str) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name in sorted(entries):
        if name == record_path:
            writer.writerow((name, "", ""))
            continue
        data = entries[name]
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        writer.writerow((name, f"sha256={digest}", str(len(data))))
    return output.getvalue().encode("utf-8")


def verify_record(entries: dict[str, bytes], record_path: str) -> None:
    rows = csv.reader(io.StringIO(entries[record_path].decode("utf-8")))
    seen: set[str] = set()
    for name, digest, size in rows:
        if name in seen:
            raise ValueError(f"duplicate RECORD entry {name}")
        seen.add(name)
        if name not in entries:
            raise ValueError(f"RECORD references missing member {name}")
        if name == record_path:
            if digest or size:
                raise ValueError("RECORD self row must have empty hash and size")
            continue
        data = entries[name]
        expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        if digest != expected or size != str(len(data)):
            raise ValueError(f"invalid RECORD row for {name}")
    if seen != set(entries):
        raise ValueError(f"RECORD membership mismatch: unrecorded={sorted(set(entries)-seen)}")


def zip_info(name: str, original: zipfile.ZipInfo | None = None) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, EPOCH)
    if original is not None:
        info.compress_type = original.compress_type
        info.create_system = original.create_system
        info.external_attr = original.external_attr
        info.internal_attr = original.internal_attr
        info.flag_bits = original.flag_bits & ~0x08
        info.extra = b""
        info.comment = b""
    else:
        info.compress_type = zipfile.ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
    return info


def transform_one(spec: dict, input_dir: Path, output_dir: Path, patchelf: str, readelf: str,
                  license_root: Path) -> dict:
    source = input_dir / checked_filename(spec["source_filename"])
    candidate_filename = checked_filename(spec["candidate_filename"])
    if source.is_symlink() or not source.is_file() or hash_file(source) != spec["source_sha256"]:
        raise ValueError(f"source wheel missing or hash mismatch: {source}")
    source_infos: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(source) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"source wheel CRC failure at {bad}")
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("source wheel has duplicate ZIP members")
        for info in infos:
            checked_relative(info.filename.removesuffix("/") if info.is_dir() else info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("source wheel contains a symbolic link")
        source_infos = {i.filename: i for i in infos}
        entries = {name: archive.read(name) for name in source_infos if not name.endswith("/")}

    source_records = [n for n in entries if n.endswith(".dist-info/RECORD")]
    if len(source_records) != 1:
        raise ValueError("source wheel must contain exactly one RECORD")
    verify_record(entries, source_records[0])

    top_dirs = {n.split("/", 1)[0] for n in entries}
    dist_infos = [n for n in top_dirs if n.endswith(".dist-info")]
    if len(dist_infos) != 1:
        raise ValueError(f"expected one dist-info directory, got {dist_infos}")
    old_dist = dist_infos[0]
    new_dist = old_dist.replace(spec["old_dist_version_token"], spec["new_dist_version_token"], 1)
    if new_dist == old_dist or not new_dist.endswith(".dist-info"):
        raise ValueError(f"invalid dist-info version rewrite {old_dist} -> {new_dist}")

    exclusions = set(spec.get("exclude_members", []))
    if not exclusions.issubset(entries):
        raise ValueError(f"excluded wheel members missing: {sorted(exclusions-set(entries))}")
    for item in spec.get("excluded_member_hashes", []):
        name = item["path"]
        if name not in exclusions or sha256(entries[name]) != item["sha256"]:
            raise ValueError(f"excluded source member hash mismatch: {name}")
    for name in exclusions:
        entries.pop(name)

    renamed: dict[str, bytes] = {}
    for name, data in entries.items():
        checked_relative(name)
        new_name = new_dist + name[len(old_dist):] if name.startswith(old_dist + "/") else name
        if new_name.endswith(".dist-info/METADATA"):
            text = data.decode("utf-8")
            text, count = re.subn(r"(?m)^Version: .+$", "Version: " + spec["new_version"], text, count=1)
            if count != 1:
                raise ValueError("could not uniquely update METADATA Version")
            data = text.encode("utf-8")
        renamed[new_name] = data

    for patch in spec.get("elf_patches", []):
        member = patch["path"]
        if member not in renamed:
            raise ValueError(f"patch member missing: {member}")
        expected = patch["expected_before"]
        with tempfile.TemporaryDirectory(prefix="wheel-hardening-") as td:
            elf = Path(td) / "member.so"
            elf.write_bytes(renamed[member])
            kind, paths, needed, soname = runpath_info(readelf, elf)
            for key, actual in (("kind", kind), ("paths", paths), ("needed", needed), ("soname", soname)):
                if actual != expected[key]:
                    raise ValueError(f"pre-patch {member} {key} mismatch: {actual!r}")
            desired = patch["expected_after_paths"]
            command = [patchelf]
            if kind == "RPATH":
                command.append("--force-rpath")
            command.extend(("--set-rpath", ":".join(desired), str(elf)))
            subprocess.check_call(command, timeout=90)
            after_kind, after_paths, after_needed, after_soname = runpath_info(readelf, elf)
            if after_kind != kind or after_paths != desired or after_needed != needed or after_soname != soname:
                raise ValueError(f"post-patch ELF validation failed: {member}")
            if any(p.startswith("/") for p in after_paths):
                raise ValueError(f"absolute runtime path remains in {member}: {after_paths}")
            renamed[member] = elf.read_bytes()
            if patch.get("expected_after_sha256") and sha256(renamed[member]) != patch["expected_after_sha256"]:
                raise ValueError(f"post-patch member hash differs from reviewed reference: {member}")

    for extra in spec.get("license_extras", []):
        src = (license_root / extra["source_path"]).resolve()
        root = license_root.resolve()
        if root not in src.parents or not src.is_file() or hash_file(src) != extra["sha256"]:
            raise ValueError(f"license extra missing or hash mismatch: {src}")
        dst = str(checked_relative(extra["wheel_path"]))
        if dst in renamed:
            raise ValueError(f"license extra overwrites existing member: {dst}")
        renamed[dst] = src.read_bytes()

    record_names = [n for n in renamed if n.endswith(".dist-info/RECORD")]
    if len(record_names) != 1:
        raise ValueError(f"expected one RECORD, got {record_names}")
    record_path = record_names[0]
    renamed[record_path] = rewrite_record(renamed, record_path)
    verify_record(renamed, record_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / candidate_filename
    with zipfile.ZipFile(destination, "x", allowZip64=True, compresslevel=9) as archive:
        for name in sorted(renamed):
            original_name = name.replace(new_dist, old_dist, 1) if name.startswith(new_dist + "/") else name
            info = zip_info(name, source_infos.get(original_name))
            archive.writestr(info, renamed[name], compress_type=info.compress_type, compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"candidate CRC failure at {bad}")
        actual = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
    verify_record(actual, record_path)
    digest = hash_file(destination)
    if spec.get("expected_candidate_sha256") and digest != spec["expected_candidate_sha256"]:
        raise ValueError(f"candidate hash differs from reviewed local reference: {digest}")
    return {"filename": destination.name, "sha256": digest, "size_bytes": destination.stat().st_size,
            "source_sha256": spec["source_sha256"], "record_verified": True,
            "zip_crc_verified": True, "members": len(actual), "excluded_members": sorted(exclusions),
            "patchelf_sha256": hash_file(Path(patchelf))}


def verify_patchelf_sources(source: Path, source_files: list[dict]) -> dict[str, str]:
    """Bind the compiler translation unit and both repository headers."""
    expected_names = {"patchelf.cc", "patchelf.h", "elf.h"}
    if {item["path"] for item in source_files} != {f"src/{name}" for name in expected_names}:
        raise ValueError("Patchelf source closure must include its two exact headers")
    if len(source_files) != 3 or source.name != "patchelf.cc":
        raise ValueError("invalid Patchelf source closure")
    verified = {}
    for item in source_files:
        relative = checked_relative(item["path"])
        path = source.parent / relative.name
        if path.is_symlink() or not path.is_file() or hash_file(path) != item["sha256"]:
            raise ValueError(f"Patchelf source missing or SHA256 mismatch: {relative}")
        verified[relative.as_posix()] = item["sha256"]
    return verified


def build_patchelf(source: Path, expected_source_sha256: str, compiler: str,
                   flags: list[str], output_dir: Path, source_files: list[dict]) -> tuple[Path, dict]:
    """Compile the reviewed standalone Patchelf source with the pinned flags."""
    if not source.is_file() or hash_file(source) != expected_source_sha256:
        raise ValueError(f"Patchelf source missing or SHA256 mismatch: {source}")
    verified_sources = verify_patchelf_sources(source, source_files)
    compiler_path = shutil.which(compiler)
    if not compiler_path:
        raise ValueError(f"compiler not found: {compiler}")
    version = subprocess.check_output([compiler_path, "--version"], text=True, timeout=30).splitlines()[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = output_dir / "patchelf-reviewed"
    command = [compiler_path, *flags, str(source), "-o", str(binary)]
    subprocess.check_call(command, timeout=600)
    if verify_patchelf_sources(source, source_files) != verified_sources:
        raise ValueError("Patchelf source changed during compilation")
    receipt = {
        "source_path": source.name,
        "source_sha256": hash_file(source),
        "source_files": verified_sources,
        "compiler": compiler_path,
        "compiler_version": version,
        "build_command": command,
        "network_during_build": False,
        "binary_sha256": hash_file(binary),
    }
    return binary, receipt


def select_artifacts(data: dict, selected: list[str] | None) -> list[dict]:
    """Select explicit distributions without silently ignoring unknown names."""
    artifacts = data["artifacts"]
    known = {item["distribution"] for item in artifacts}
    if len(known) != len(artifacts):
        raise ValueError("hardening manifest repeats a distribution")
    if selected is None:
        return artifacts
    if len(set(selected)) != len(selected) or set(selected) - known:
        raise ValueError("hardening selection is duplicated or unknown")
    return [item for item in artifacts if item["distribution"] in selected]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--license-root", type=Path, default=Path("."))
    parser.add_argument("--patchelf-source", type=Path, required=True,
                        help="src/patchelf.cc from the exact reviewed Patchelf checkout")
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--distribution", action="append",
                        help="transform only these explicitly selected distributions")
    args = parser.parse_args()
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise SystemExit("unsupported input schema")
    artifacts = select_artifacts(data, args.distribution)
    tool_dir = args.output_dir / ".tool-build"
    patchelf, builder_receipt = build_patchelf(
        args.patchelf_source,
        data["patchelf"]["source_file_sha256"],
        args.compiler,
        data["patchelf"]["build_flags"],
        tool_dir,
        data["source_repository"]["source_files"],
    )
    results = [transform_one(s, args.input_dir, args.output_dir, patchelf, args.readelf, args.license_root)
               for s in artifacts]
    report = {"schema_version": 1, "status": "candidate-only; not installed/imported/loaded",
              "patchelf_builder_receipt": builder_receipt, "artifacts": results}
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
