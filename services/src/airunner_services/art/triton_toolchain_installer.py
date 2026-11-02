"""Stage reviewed NVIDIA CUDA inputs in a private local directory.

The downloaded CUDA developer tools and headers are for local use only. This
script never adds them to wheels, source bundles, or release artifacts. It
verifies NVIDIA's pinned redistribution metadata and archive hashes, extracts
only reviewed regular-file members, and emits an environment mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import resources
import os
import platform
import shutil
import shlex
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


MANIFEST_SHA256 = "129344f0ae7605070a0460b3dc908419c673a0a94dc33b8f56a26490eb80aef6"
REDIST_BASE = "https://developer.download.nvidia.com/compute/cuda/redist/"


class StageError(ValueError):
    """Input failed a fixed source or safe-staging check."""


def _source_manifest() -> dict[str, Any]:
    payload = resources.files("airunner_services.art").joinpath(
        "data/triton_external_toolchain_sources.json"
    ).read_bytes()
    if hashlib.sha256(payload).hexdigest() != MANIFEST_SHA256:
        raise StageError("packaged NVIDIA source manifest digest is not reviewed")
    value = json.loads(payload)
    if value.get("schema_version") != 1:
        raise StageError("packaged NVIDIA source manifest is unsupported")
    return value


def _pins() -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    manifest = _source_manifest()
    archives = {(x["release"], x["component"]): {k:v for k,v in x.items() if k not in ("release", "component")} for x in manifest["archives"]}
    return manifest["redistributions"], archives


REDISTRIBUTIONS, ARCHIVES = _pins()



def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _allowed_private_path(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        raise StageError("staging paths must be absolute")
    current = Path(expanded.anchor)
    for part in expanded.parts[1:]:
        if part in {"", "."}:
            continue
        current = current / part
        if current.is_symlink():
            raise StageError("staging paths cannot traverse symbolic links")
    resolved = expanded.resolve(strict=False)
    allowed = (
        (Path.home() / ".cache" / "airunner").resolve(),
        Path("/tmp").resolve(),
    )
    if not any(
        resolved.is_relative_to(root)
        and (resolved != root or root == allowed[0])
        for root in allowed
    ):
        raise StageError("output and archive cache must be in a private AIRunner cache or /tmp")
    return resolved


def _ensure_private_directory(path: Path, *, create: bool = True) -> Path:
    """Create or validate an owner-only directory below an approved root."""
    target = _allowed_private_path(path)
    home_cache_root = (Path.home() / ".cache" / "airunner").resolve()
    tmp_root = Path("/tmp").resolve()
    if target.is_relative_to(home_cache_root):
        base = Path.home().resolve()
        parts = (".cache", "airunner", *target.relative_to(home_cache_root).parts)
        private_from_index = 1
    elif target.is_relative_to(tmp_root):
        base = tmp_root
        parts = target.relative_to(tmp_root).parts
        private_from_index = 0
        tmp_stat = base.stat()
        if not stat.S_ISDIR(tmp_stat.st_mode) or not tmp_stat.st_mode & stat.S_ISVTX:
            raise StageError("/tmp must be a real sticky-bit directory")
    else:
        raise StageError("private directory is outside the reviewed staging roots")

    current = base
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise StageError("private cache directories cannot be symbolic links")
        try:
            current_stat = current.stat(follow_symlinks=False)
        except FileNotFoundError:
            if not create:
                raise StageError("private directory does not exist") from None
            current.mkdir(mode=0o700)
            current_stat = current.stat(follow_symlinks=False)
        if not stat.S_ISDIR(current_stat.st_mode):
            raise StageError("private cache path component must be a directory")
        if current_stat.st_uid != os.getuid():
            raise StageError("private cache directories must belong to the current user")
        if index >= private_from_index and current_stat.st_mode & 0o077:
            raise StageError("private cache directories must be owner-only")
    return target


def _validate_private_cache_file(path: Path) -> None:
    """Require cached inputs to be owner-owned regular private files."""
    if path.is_symlink():
        raise StageError("private toolchain cache files cannot be symbolic links")
    try:
        file_stat = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise StageError("private toolchain cache file cannot be inspected") from exc
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_uid != os.getuid():
        raise StageError("private toolchain cache entries must be owner-owned regular files")
    if file_stat.st_mode & 0o077:
        raise StageError("private toolchain cache files must be owner-only")


def _validate_download_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
    if (
        parsed.scheme != "https"
        or parsed.hostname != "developer.download.nvidia.com"
        or parsed.username is not None
        or parsed.password is not None
        or not valid_port
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/compute/cuda/redist/")
    ):
        raise StageError("refusing a URL outside the pinned NVIDIA redistribution endpoint")
    return parsed


class _PinnedNvidiaRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate redirect targets before urllib connects to them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_download_url(urllib.parse.urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(
    url: str,
    destination: Path,
    *,
    expected_size: int | None = None,
    max_size: int | None = None,
) -> None:
    _validate_download_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".nvidia-fetch-", dir=destination.parent)
    temp_path = Path(temp_name)
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "AIRunner-local-toolchain-stager/1"}
        )
        with os.fdopen(descriptor, "wb") as writer:
            opener = urllib.request.build_opener(_PinnedNvidiaRedirectHandler())
            with opener.open(request, timeout=60) as response:
                _validate_download_url(response.geturl())
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if expected_size is not None and size > expected_size:
                        raise StageError("download exceeded the NVIDIA-published size")
                    if max_size is not None and size > max_size:
                        raise StageError("download exceeded its configured metadata bound")
                    writer.write(chunk)
        if expected_size is not None and size != expected_size:
            raise StageError("download size differs from NVIDIA's published size")
        try:
            os.link(temp_path, destination)
        except FileExistsError:
            raise StageError("refusing to overwrite an existing archive cache file") from None
    finally:
        temp_path.unlink(missing_ok=True)


def _metadata(redistribution: str, cache_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pin = REDISTRIBUTIONS[redistribution]
    target = cache_dir / f"redistrib_{redistribution}.json"
    if not target.exists():
        _fetch(pin["url"], target, max_size=64 * 1024)
    _validate_private_cache_file(target)
    digest, size = _sha256(target)
    if digest != pin["sha256"] or size > 64 * 1024:
        raise StageError("NVIDIA redistribution metadata does not match the reviewed digest")
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StageError("NVIDIA redistribution metadata is invalid") from exc
    if document.get("release_label") != redistribution:
        raise StageError("NVIDIA redistribution release label changed")
    return document, {"url": pin["url"], "sha256": digest, "size_bytes": size}


def _archive(
    redistribution: str,
    component: str,
    metadata: dict[str, Any],
    cache_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    spec = ARCHIVES[(redistribution, component)]
    component_data = metadata.get(component)
    platform_data = component_data.get("linux-x86_64") if isinstance(component_data, dict) else None
    if not isinstance(component_data, dict) or not isinstance(platform_data, dict):
        raise StageError("NVIDIA metadata lacks the selected Linux component")
    if (
        component_data.get("version") != spec["version"]
        or platform_data.get("relative_path") != spec["relative_path"]
        or platform_data.get("sha256") != spec["sha256"]
        or int(platform_data.get("size", -1)) != spec["size_bytes"]
    ):
        raise StageError("selected NVIDIA archive differs from the reviewed publisher metadata")
    url = REDIST_BASE + spec["relative_path"]
    path = cache_dir / Path(spec["relative_path"]).name
    if not path.exists():
        _fetch(url, path, expected_size=spec["size_bytes"])
    _validate_private_cache_file(path)
    digest, size = _sha256(path)
    if digest != spec["sha256"] or size != spec["size_bytes"]:
        raise StageError("NVIDIA archive digest or size does not match publisher metadata")
    return path, {"url": url, **spec}


def _safe_member_name(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name:
        return False
    return all(part not in ("", ".", "..") for part in name.split("/"))


def _create_private_parents(directory: Path) -> None:
    """Create missing staging descendants without changing existing modes."""
    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        current = current.parent
    for path in reversed(missing):
        path.mkdir(mode=0o700)


def _copy_tar_member(
    archive_path: Path,
    member_name: str,
    destination: Path,
    expected: dict[str, Any],
    *,
    executable: bool = False,
) -> dict[str, Any]:
    with tarfile.open(archive_path, mode="r:xz") as archive:
        candidates = [member for member in archive.getmembers() if member.name == member_name]
        if len(candidates) != 1:
            raise StageError("pinned regular member is missing or duplicated in NVIDIA archive")
        member = candidates[0]
        if not member.isfile() or not _safe_member_name(member.name):
            raise StageError("selected archive member is not a safe regular file")
        if member.size != expected["size_bytes"]:
            raise StageError("selected file size differs from reviewed Triton bytes")
        source = archive.extractfile(member)
        if source is None:
            raise StageError("selected NVIDIA archive member cannot be read")
        _create_private_parents(destination.parent)
        digest = hashlib.sha256()
        size = 0
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(destination, flags, 0o700 if executable else 0o600)
        try:
            with source, os.fdopen(descriptor, "wb") as writer:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    digest.update(chunk)
                    writer.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    actual = digest.hexdigest()
    if size != expected["size_bytes"] or actual != expected["sha256"]:
        destination.unlink(missing_ok=True)
        raise StageError("selected file hash differs from reviewed Triton member")
    return {"path": destination.as_posix(), "sha256": actual, "size_bytes": size}


def _copy_archive_license(
    archive_path: Path,
    member_name: str,
    destination: Path,
) -> dict[str, Any]:
    """Preserve a license file from an archive verified against NVIDIA's hash."""
    with tarfile.open(archive_path, mode="r:xz") as archive:
        candidates = [member for member in archive.getmembers() if member.name == member_name]
        if len(candidates) != 1:
            raise StageError("NVIDIA archive license member is missing or duplicated")
        member = candidates[0]
        if not member.isfile() or not _safe_member_name(member.name):
            raise StageError("NVIDIA archive license is not a safe regular file")
        if member.size > 1024 * 1024:
            raise StageError("NVIDIA archive license exceeds its size bound")
        source = archive.extractfile(member)
        if source is None:
            raise StageError("NVIDIA archive license cannot be read")
        _create_private_parents(destination.parent)
        digest = hashlib.sha256()
        size = 0
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            with source, os.fdopen(descriptor, "wb") as writer:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    digest.update(chunk)
                    writer.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    if size != member.size:
        destination.unlink(missing_ok=True)
        raise StageError("NVIDIA archive license size changed during read")
    return {
        "path": destination.as_posix(),
        "source_member": member_name,
        "sha256": digest.hexdigest(),
        "size_bytes": size,
    }


def _copy_notice(
    source: Path,
    destination: Path,
    sha256: str,
    official_source_url: str,
) -> dict[str, Any]:
    digest, size = _sha256(source)
    if digest != sha256:
        raise StageError("reviewed NVIDIA license/notice document changed")
    _create_private_parents(destination.parent)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)
    os.chmod(destination, 0o600)
    return {
        "path": destination.as_posix(),
        "official_source_url": official_source_url,
        "sha256": digest,
        "size_bytes": size,
    }


def _copy_notice_bytes(
    payload: bytes,
    destination: Path,
    sha256: str,
    official_source_url: str,
) -> dict[str, Any]:
    digest = hashlib.sha256(payload).hexdigest()
    if digest != sha256:
        raise StageError("reviewed NVIDIA license/notice document changed")
    _create_private_parents(destination.parent)
    with destination.open("xb") as writer:
        writer.write(payload)
    os.chmod(destination, 0o600)
    return {
        "path": destination.as_posix(),
        "official_source_url": official_source_url,
        "sha256": digest,
        "size_bytes": len(payload),
    }


def stage_external_toolchain(
    output_dir: Path,
    *,
    archive_cache: Path | None = None,
) -> dict[str, Any]:
    from .triton_runtime import load_policy

    recipe = load_policy()
    recipe_sha256 = recipe["candidate"]["recipe_sha256"]
    output = _allowed_private_path(output_dir)
    cache = _allowed_private_path(archive_cache or (output.parent / "nvidia-archive-cache"))
    private_root = (Path.home() / ".cache" / "airunner").resolve()
    tmp_root = Path("/tmp").resolve()
    if output in (private_root, tmp_root) or cache in (private_root, tmp_root):
        raise StageError("staging output and archive cache must be child directories")
    if cache.is_relative_to(output):
        raise StageError("archive cache cannot be inside the staging output directory")
    if output.exists():
        raise StageError("refusing to overwrite an existing private staging directory")
    if output.parent == tmp_root:
        tmp_stat = tmp_root.stat()
        if not stat.S_ISDIR(tmp_stat.st_mode) or not tmp_stat.st_mode & stat.S_ISVTX:
            raise StageError("/tmp must be a real sticky-bit directory")
    else:
        _ensure_private_directory(output.parent)
    _ensure_private_directory(cache)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        output_stat = output.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(output_stat.st_mode)
            or output_stat.st_uid != os.getuid()
            or output_stat.st_mode & 0o077
        ):
            raise StageError("staging output directory must be private to the current user")
        metadata_by_release: dict[str, dict[str, Any]] = {}
        metadata_receipts: dict[str, dict[str, Any]] = {}
        for release in REDISTRIBUTIONS:
            metadata_by_release[release], metadata_receipts[release] = _metadata(release, cache)

        archive_specs: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
        for pair in ARCHIVES:
            archive_specs[pair] = _archive(
                pair[0], pair[1], metadata_by_release[pair[0]], cache
            )

        tools = recipe["tools"]
        tool_outputs = {
            "ptxas": (
                "12.8.1",
                "cuda_nvcc",
                "cuda_nvcc-linux-x86_64-12.8.93-archive/bin/ptxas",
                "bin/ptxas",
            ),
            "ptxas-blackwell": (
                "13.1.0",
                "cuda_nvcc",
                "cuda_nvcc-linux-x86_64-13.1.80-archive/bin/ptxas",
                "bin/ptxas-blackwell",
            ),
            "cuobjdump": (
                "13.1.0",
                "cuda_cuobjdump",
                "cuda_cuobjdump-linux-x86_64-13.1.80-archive/bin/cuobjdump",
                "bin/cuobjdump",
            ),
            "nvdisasm": (
                "13.1.0",
                "cuda_nvdisasm",
                "cuda_nvdisasm-linux-x86_64-13.1.80-archive/bin/nvdisasm",
                "bin/nvdisasm",
            ),
        }
        outputs: list[dict[str, Any]] = []
        for tool in tools:
            name = tool["name"]
            release, component, member, relative = tool_outputs[name]
            archive_path, _archive_receipt = archive_specs[(release, component)]
            staged = _copy_tar_member(
                archive_path,
                member,
                output / relative,
                {"sha256": tool["sha256"], "size_bytes": tool["size_bytes"]},
                executable=True,
            )
            outputs.append({"env": tool["env"], **staged})

        header = recipe["headers"]["required_files"][0]
        cudart_archive, _ = archive_specs[("13.1.0", "cuda_cudart")]
        outputs.append({
            "env": "TRITON_CUDACRT_PATH",
            **_copy_tar_member(
                cudart_archive,
                "cuda_cudart-linux-x86_64-13.1.80-archive/include/cuda.h",
                output / "include/cuda.h",
                {"sha256": header["sha256"], "size_bytes": header["size_bytes"]},
            ),
        })

        cupti_archive, _ = archive_specs[("12.8.1", "cuda_cupti")]
        cupti_root = "cuda_cupti-linux-x86_64-12.8.90-archive/lib/"
        for spec in recipe["cupti"]["required_files"]:
            basename = Path(spec["path"]).name
            source_name = "libcupti.so.2025.1.1" if basename in {
                "libcupti.so", "libcupti.so.12"
            } else basename
            staged = _copy_tar_member(
                cupti_archive,
                cupti_root + source_name,
                output / "lib/cupti" / basename,
                spec,
            )
            outputs.append({"env": "TRITON_CUPTI_LIB_PATH", **staged})

        license_receipts = []
        source_manifest = _source_manifest()
        for notice in source_manifest["notices"]:
            filename = notice["filename"]
            resource = resources.files("airunner_services.art").joinpath(
                "data/triton_external_toolchain_notices", filename
            )
            license_receipts.append(
                _copy_notice_bytes(
                    resource.read_bytes(),
                    output / "share/licenses/nvidia" / filename,
                    notice["sha256"],
                    notice["official_source_url"],
                )
            )

        archive_license_receipts = []
        for (release, component), (archive_path, archive_receipt) in archive_specs.items():
            archive_name = Path(archive_receipt["relative_path"]).name.removesuffix(
                ".tar.xz"
            )
            source_member = f"{archive_name}/LICENSE"
            license_name = f"{component}-{archive_receipt['version']}-LICENSE.txt"
            archive_license_receipts.append(
                {
                    **_copy_archive_license(
                        archive_path,
                        source_member,
                        output
                        / "share/licenses/nvidia/archive-components"
                        / license_name,
                    ),
                    "official_archive_url": archive_receipt["url"],
                    "archive_sha256": archive_receipt["sha256"],
                }
            )

        env = {
            "TRITON_PTXAS_PATH": str(output / "bin/ptxas"),
            "TRITON_PTXAS_BLACKWELL_PATH": str(output / "bin/ptxas-blackwell"),
            "TRITON_CUOBJDUMP_PATH": str(output / "bin/cuobjdump"),
            "TRITON_NVDISASM_PATH": str(output / "bin/nvdisasm"),
            "TRITON_CUDACRT_PATH": str(output / "include"),
            "TRITON_CUDART_PATH": str(output / "include"),
            "TRITON_CUPTI_LIB_PATH": str(output / "lib/cupti"),
        }
        (output / "triton-env.sh").write_text(
            "\n".join(f"export {key}={shlex.quote(value)}" for key, value in env.items()) + "\n",
            encoding="utf-8",
        )
        os.chmod(output / "triton-env.sh", 0o600)
        receipt = {
            "schema_version": 1,
            "scope": "private local-use NVIDIA developer inputs; do not redistribute",
            "recipe_sha256": recipe_sha256,
            "redistribution_metadata": metadata_receipts,
            "archives": [
                archive_receipt
                for _path, archive_receipt in archive_specs.values()
            ],
            "staged_file_count": len(outputs),
            "staged_files": outputs,
            "license_and_notice_files": license_receipts,
            "archive_license_files": archive_license_receipts,
            "environment": env,
            "checks": {
                "publisher_archive_sha256_and_sizes_verified": True,
                "selected_member_sha256_and_sizes_verified": True,
                "only_selected_regular_members_extracted": True,
                "vendor_executables_run": False,
            },
            "license_scope": [
                (
                    "CUDA EULA 12.8.1/13.1 reviewed; local installation/use only "
                    "for these nonredistributable developer tools and headers."
                ),
                (
                    "These bytes are not included in a wheel, source bundle, CI "
                    "artifact, or release asset."
                ),
                (
                    "CUPTI 12.8.1 notices are retained; no claim is made about "
                    "the applicable limited-purpose CUPTI grant."
                ),
            ],
        }
        receipt_path = output / "local-toolchain-receipt.json"
        receipt["receipt_path"] = str(receipt_path)
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(receipt_path, 0o600)
        return receipt
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def cached_toolchain_environment() -> dict[str, str]:
    """Locate existing private inputs without creating or downloading anything.

    Callers must still validate every selected file against the runtime policy.
    The receipt and shell file are deliberately not used as executable inputs.
    """
    target = (
        Path.home() / ".cache" / "airunner" / "triton"
        / "external-toolchain" / MANIFEST_SHA256
    )
    _ensure_private_directory(target, create=False)
    for relative in ("bin", "include", "lib/cupti"):
        _ensure_private_directory(target / relative, create=False)
    files = {
        "TRITON_PTXAS_PATH": target / "bin/ptxas",
        "TRITON_PTXAS_BLACKWELL_PATH": target / "bin/ptxas-blackwell",
        "TRITON_CUOBJDUMP_PATH": target / "bin/cuobjdump",
        "TRITON_NVDISASM_PATH": target / "bin/nvdisasm",
    }
    for path in files.values():
        _validate_private_cache_file(path)
    _validate_private_cache_file(target / "include/cuda.h")
    from airunner_services.art.triton_runtime import load_policy

    for spec in load_policy()["cupti"]["required_files"]:
        _validate_private_cache_file(target / "lib/cupti" / Path(spec["path"]).name)
    return {
        **{name: str(path) for name, path in files.items()},
        "TRITON_CUDACRT_PATH": str(target / "include"),
        "TRITON_CUDART_PATH": str(target / "include"),
        "TRITON_CUPTI_LIB_PATH": str(target / "lib/cupti"),
    }


def install_private_toolchain(destination: Path | None = None) -> dict[str, Any]:
    """Explicitly download and stage inputs into a private user cache."""
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise StageError("the reviewed external toolchain targets Linux x86_64 only")
    cache_root = Path.home() / ".cache" / "airunner"
    cache_root = _ensure_private_directory(cache_root)
    target = destination or (
        cache_root / "triton" / "external-toolchain" / MANIFEST_SHA256
    )
    resolved = _allowed_private_path(target)
    private_root = cache_root.resolve()
    if not resolved.is_relative_to(private_root):
        raise StageError("operator destination must be inside the private AIRunner cache")
    relative_parent = resolved.parent.relative_to(private_root)
    current = private_root
    for part in relative_parent.parts:
        current = current / part
        if current.exists():
            if current.is_symlink() or not current.is_dir():
                raise StageError("private toolchain cache parent must be a real directory")
            if current.stat().st_uid != os.getuid() or current.stat().st_mode & 0o077:
                raise StageError("private toolchain cache parents must be owner-only directories")
        else:
            current.mkdir(mode=0o700)
    return stage_external_toolchain(
        resolved, archive_cache=resolved.parent / "nvidia-archive-cache"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--install",
        action="store_true",
        help="download and stage into the private per-user cache",
    )
    mode.add_argument(
        "--output-dir",
        type=Path,
        help="explicit private staging destination (downloads reviewed inputs)",
    )
    parser.add_argument("--archive-cache", type=Path)
    args = parser.parse_args(argv)
    if args.install and args.archive_cache is not None:
        parser.error("--archive-cache can only be used with --output-dir")
    try:
        receipt = (
            install_private_toolchain()
            if args.install
            else stage_external_toolchain(
                args.output_dir,
                archive_cache=args.archive_cache,
            )
        )
    except (
        OSError,
        StageError,
        tarfile.TarError,
        urllib.error.URLError,
    ) as exc:
        print(f"Private Triton toolchain staging failed: {exc}", file=sys.stderr)
        return 1
    print("Private local-use Triton toolchain staged. Not redistributable.")
    for name, value in receipt["environment"].items():
        print(f"{name}={value}")
    print(f"Receipt: {receipt['receipt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
