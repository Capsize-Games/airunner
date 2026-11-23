"""Stage exact NVIDIA toolchain members privately for local Triton validation.

The staged output is restricted to an ignored `.headlesscode` directory or
`/tmp`. It is never a wheelhouse or release input. No vendor executable is run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_triton_external_toolchain_subset import (
    WheelError,
    _check_zip_inventory,
    _hash_member,
    _verify_record,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "package" / "triton-external-toolchain-subset.json"
DEFAULT_NOTICE_DIR = ROOT / "packaging" / "licenses" / "triton-3.7.1-supplement"
EXPECTED_RECIPE_SHA256 = "ff68281c53526986f054b52d66211dd6f771085e0e0230331430698a7e953958"


def _hash_bytes(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _copy_member(
    source: zipfile.ZipFile,
    inventory: dict[str, zipfile.ZipInfo],
    member: dict[str, Any],
    target: Path,
    *,
    executable: bool = False,
) -> dict[str, Any]:
    name = member["path"]
    info = inventory.get(name)
    if info is None:
        raise WheelError("pinned source wheel member is missing")
    digest, size = _hash_member(source, info)
    if digest != member["sha256"] or size != member["size_bytes"]:
        raise WheelError("pinned source wheel member digest changed")
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open(info, "r") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)
    os.chmod(target, 0o755 if executable else 0o644)
    return {"path": target.as_posix(), "sha256": digest, "size_bytes": size}


def _license_documents(notices: dict[str, Any]) -> list[dict[str, str]]:
    cuda = next(item for item in notices["components"] if item["name"] == "NVIDIA CUDA header/toolchain assets")
    cupti = next(item for item in notices["components"] if item["name"] == "CUPTI/NVPerf")
    docs: list[dict[str, str]] = []
    for eula in cuda["official_eulas"]:
        release = eula["release"]
        stem = f"CUDA-{release}-EULA"
        docs.extend(
            [
                {
                    "source": f"{stem}.pdf",
                    "sha256": eula["pdf_sha256"],
                    "official_source_url": eula["url"],
                },
                {
                    "source": f"{stem}.txt",
                    "sha256": eula["text_sha256"],
                    "official_source_url": eula["url"],
                },
            ]
        )
    docs.extend(
        [
            {
                "source": "CUPTI-12.8.1-copyright-and-licenses.html",
                "sha256": cupti["document_sha256"],
                "official_source_url": cupti["official_source_url"],
            },
            {
                "source": "CUPTI-12.8.1-copyright-and-licenses.txt",
                "sha256": cupti["text_sha256"],
                "official_source_url": cupti["official_source_url"],
            },
        ]
    )
    return docs


def stage_toolchain(
    source_wheel: Path,
    output_dir: Path,
    *,
    recipe_path: Path = DEFAULT_RECIPE,
    notice_dir: Path = DEFAULT_NOTICE_DIR,
) -> dict[str, Any]:
    recipe_bytes = recipe_path.read_bytes()
    if hashlib.sha256(recipe_bytes).hexdigest() != EXPECTED_RECIPE_SHA256:
        raise WheelError("subset recipe is not the reviewed version")
    recipe = json.loads(recipe_bytes)
    source_spec = recipe["source"]
    if source_wheel.name != source_spec["original_wheel_filename"]:
        raise WheelError("source wheel filename does not match the reviewed Triton wheel")
    source_sha256, _ = _hash_bytes(source_wheel)
    if source_sha256 != source_spec["original_wheel_sha256"]:
        raise WheelError("source wheel digest does not match the reviewed Triton wheel")

    resolved_output = output_dir.resolve()
    private_root = (ROOT / ".headlesscode").resolve()
    temp_root = Path("/tmp").resolve()
    if not (resolved_output.is_relative_to(private_root) or resolved_output.is_relative_to(temp_root)):
        raise WheelError("staging output must be under ignored .headlesscode or /tmp")
    if resolved_output.exists():
        raise WheelError("staging output already exists")

    notes = json.loads((notice_dir / "source-notices.json").read_text(encoding="utf-8"))
    staged: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(source_wheel, "r") as archive:
            inventory = _check_zip_inventory(archive)
            _verify_record(archive, inventory)

            tools = recipe["external_toolchain"]["tools"]
            for tool in tools:
                staged.append(
                    {
                        **_copy_member(
                            archive,
                            inventory,
                            next(x for x in recipe["subset"]["exclude_members"] if x["path"] == tool["path"]),
                            output_dir / "bin" / tool["name"],
                            executable=True,
                        ),
                        "env": tool["env"],
                        "version": tool["version"],
                        "source_member": tool["path"],
                        "official_archive_url": tool["official_archive_url"],
                    }
                )

            header_members = [
                item for item in recipe["subset"]["exclude_members"]
                if item["path"].startswith("triton/backends/nvidia/include/")
            ]
            if len(header_members) != 154:
                raise WheelError("recipe does not enumerate the reviewed CUDA header set")
            for header in header_members:
                rel = header["path"].removeprefix("triton/backends/nvidia/include/")
                staged.append(
                    {
                        **_copy_member(archive, inventory, header, output_dir / "include" / rel),
                        "source_member": header["path"],
                    }
                )

            cupti = recipe["external_toolchain"]["cupti"]
            if len(cupti["required_files"]) != 9:
                raise WheelError("recipe does not enumerate the reviewed CUPTI payload")
            for library in cupti["required_files"]:
                staged.append(
                    {
                        **_copy_member(
                            archive,
                            inventory,
                            library,
                            output_dir / "lib" / "cupti" / Path(library["path"]).name,
                        ),
                        "source_member": library["path"],
                    }
                )

            libdevice = recipe["subset"]["retain_members"][0]
            staged.append(
                {
                    **_copy_member(
                        archive,
                        inventory,
                        libdevice,
                        output_dir / "lib" / "libdevice.10.bc",
                    ),
                    "source_member": libdevice["path"],
                    "redistribution_basis": "CUDA 13.1 EULA Attachment A lists Linux libdevice.10.bc",
                }
            )

        license_files: list[dict[str, Any]] = []
        for document in _license_documents(notes):
            source = notice_dir / document["source"]
            digest, size = _hash_bytes(source)
            if digest != document["sha256"]:
                raise WheelError("official license document hash does not match the review record")
            target = output_dir / "share" / "licenses" / "nvidia" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            os.chmod(target, 0o644)
            license_files.append(
                {
                    "path": target.relative_to(output_dir).as_posix(),
                    "sha256": digest,
                    "size_bytes": size,
                    "official_source_url": document["official_source_url"],
                }
            )

        receipt = {
            "schema_version": 1,
            "status": "private local staging only; not a package, wheelhouse, or release input",
            "source_wheel": source_spec["original_wheel_filename"],
            "source_wheel_sha256": source_sha256,
            "upstream_source_commit": source_spec["upstream_commit"],
            "staged_file_count": len(staged),
            "staged_files": staged,
            "license_documents": license_files,
            "rights_and_scope": [
                "NVIDIA CUDA EULA 13.1 sections 1.1.1 and 1.1.2(4) cover SDK install/use and internal-use developer tools; this staging is private and excluded from distribution.",
                "EULA 13.1 Attachment A identifies libdevice.10.bc as redistributable; no redistribution of the excluded tool/header/CUPTI payloads is authorized by this staging receipt.",
                "CUPTI 12.8.1 copyright and license text is preserved; this receipt does not decide which limited-purpose agreement applies.",
            ],
            "external_paths": {
                "TRITON_PTXAS_PATH": "bin/ptxas",
                "TRITON_PTXAS_BLACKWELL_PATH": "bin/ptxas-blackwell",
                "TRITON_CUOBJDUMP_PATH": "bin/cuobjdump",
                "TRITON_NVDISASM_PATH": "bin/nvdisasm",
                "TRITON_CUDACRT_PATH": "include",
                "TRITON_CUDART_PATH": "include",
                "TRITON_CUPTI_LIB_PATH": "lib/cupti",
                "TRITON_LIBDEVICE_PATH": "lib/libdevice.10.bc",
            },
        }
        receipt_path = output_dir / "local-staging-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return receipt
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-wheel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--notice-dir", type=Path, default=DEFAULT_NOTICE_DIR)
    args = parser.parse_args(argv)
    try:
        receipt = stage_toolchain(
            args.source_wheel,
            args.output_dir,
            recipe_path=args.recipe,
            notice_dir=args.notice_dir,
        )
    except (OSError, json.JSONDecodeError, KeyError, StopIteration, WheelError, zipfile.BadZipFile) as error:
        print(f"Private Triton toolchain staging: {error}", file=sys.stderr)
        return 1
    print(json.dumps({key: value for key, value in receipt.items() if key not in {"staged_files", "license_documents", "rights_and_scope"}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
