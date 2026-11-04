"""Load explicitly reviewed vendor license documents into a bundle.

Vendor documents and extracted text are kept as separate provenance records.
They are not distribution wheel RECORD entries and this module never fetches
the listed URLs or imports third-party packages.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlsplit


_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")
_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
_MAX_PACKAGE_BYTES = 64 * 1024 * 1024
_MAX_ALL_BYTES = 128 * 1024 * 1024
_MAX_MANIFESTS = 256
_MAX_DOCUMENTS_PER_MANIFEST = 32


class VendorNoticeSupplementError(ValueError):
    """A vendor notice manifest or its files are unsafe or inconsistent."""


def _fail(message: str) -> None:
    raise VendorNoticeSupplementError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("vendor notice manifest has duplicate JSON keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail(f"vendor notice manifest has invalid JSON constant: {value}")


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _safe_relative(value: Any, label: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
    ):
        _fail(f"{label} is unsafe")
    pieces = value.split("/")
    if any(piece in {"", ".", ".."} for piece in pieces):
        _fail(f"{label} contains path traversal")
    return PurePosixPath(*pieces)


def _safe_repo_file(
    repo_root: Path,
    value: Any,
    label: str,
    *,
    max_bytes: int,
) -> tuple[PurePosixPath, bytes]:
    relative = _safe_relative(value, label)
    candidate = repo_root.joinpath(*relative.parts)
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            _fail(f"{label} contains a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as exc:
        raise VendorNoticeSupplementError(
            f"{label} escapes the repository or is missing"
        ) from exc
    if not candidate.is_file():
        _fail(f"{label} is not a regular file")
    try:
        size = candidate.stat().st_size
        if size > max_bytes:
            _fail(f"{label} exceeds its size limit")
        content = candidate.read_bytes()
    except OSError as exc:
        raise VendorNoticeSupplementError(f"{label} cannot be read") from exc
    if len(content) != size:
        _fail(f"{label} changed while being read")
    return relative, content


def _keys(
    value: Any,
    required: set[str],
    optional: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    keys = set(value)
    if not required.issubset(keys) or keys - required - optional:
        _fail(f"{label} has missing or unknown JSON keys")
    return value


def _string(value: Any, label: str, *, max_length: int = 4000) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > max_length
        or any(ord(char) < 0x20 and char not in "\n\t" for char in value)
    ):
        _fail(f"{label} is invalid")
    return value


def _date(value: Any) -> str:
    text = _string(value, "vendor document retrieved_date", max_length=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise VendorNoticeSupplementError(
            "vendor document retrieved_date must be YYYY-MM-DD"
        ) from exc
    if parsed.isoformat() != text:
        _fail("vendor document retrieved_date must be YYYY-MM-DD")
    return text


def _official_url(value: Any) -> str:
    url = _string(value, "vendor document official_source_url", max_length=2048)
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise VendorNoticeSupplementError(
            "vendor document official_source_url is invalid"
        ) from exc
    if (
        parsed.scheme != "https"
        or parsed.query
        or parsed.fragment
        or "?" in url
        or "#" in url
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.netloc != parsed.hostname
        or "%" in parsed.path
        or "\\" in parsed.path
        or any(part in {"", ".", ".."} for part in parsed.path.split("/")[1:])
    ):
        _fail(
            "vendor document official_source_url is not an allowed canonical HTTPS URL"
        )
    if parsed.hostname == "docs.nvidia.com":
        if parsed.path.startswith("/cuda/archive/") or re.fullmatch(
            r"/deeplearning/nccl/archives/nccl_[0-9]+/pdf/NCCL-SLA\.pdf",
            parsed.path,
        ):
            return url
        _fail("vendor document URL is outside the allowed NVIDIA archives")
    if parsed.hostname == "github.com":
        match = re.fullmatch(
            r"/NVIDIA/(nvshmem|nccl)/blob/([0-9a-fA-F]{40})/"
            r"(License\.txt|LICENSE\.txt|ThirdPartyNotices\.txt)",
            parsed.path,
        )
        if match is None:
            _fail("vendor document URL is outside the allowed NVIDIA source files")
        return url
    _fail("vendor document official_source_url host is not allowed")


def _file_manifest(value: Any, label: str) -> dict[str, Any]:
    record = _keys(
        value,
        {"path", "sha256", "size_bytes"},
        set(),
        label,
    )
    _safe_relative(record["path"], f"{label} path")
    if not isinstance(record["sha256"], str) or not _HEX_RE.fullmatch(
        record["sha256"]
    ):
        _fail(f"{label} SHA-256 is invalid")
    if (
        not isinstance(record["size_bytes"], int)
        or isinstance(record["size_bytes"], bool)
        or record["size_bytes"] <= 0
        or record["size_bytes"] > _MAX_DOCUMENT_BYTES
    ):
        _fail(f"{label} size is invalid")
    return record


def _vendor_document(value: Any) -> dict[str, Any]:
    document = _keys(
        value,
        {
            "publisher",
            "product",
            "release_scope",
            "official_source_url",
            "retrieved_date",
            "document_path",
            "document_sha256",
            "document_size_bytes",
            "text_path",
            "text_sha256",
            "text_size_bytes",
        },
        set(),
        "vendor_document",
    )
    publisher = _string(
        document["publisher"], "vendor document publisher", max_length=256
    )
    if "nvidia" not in publisher.casefold() or re.search(
        r"https?://|file://", publisher, re.IGNORECASE
    ):
        _fail("vendor document publisher is not NVIDIA")
    product = _string(document["product"], "vendor document product", max_length=512)
    scope = _string(
        document["release_scope"], "vendor document release_scope", max_length=4000
    )
    if re.search(r"https?://|file://", product + "\n" + scope, re.IGNORECASE):
        _fail("vendor product or release_scope contains a URL")
    official_url = _official_url(document["official_source_url"])
    retrieved = _date(document["retrieved_date"])
    original = _file_manifest(
        {
            "path": document["document_path"],
            "sha256": document["document_sha256"],
            "size_bytes": document["document_size_bytes"],
        },
        "vendor document original file",
    )
    text = _file_manifest(
        {
            "path": document["text_path"],
            "sha256": document["text_sha256"],
            "size_bytes": document["text_size_bytes"],
        },
        "vendor document text file",
    )
    return {
        "publisher": publisher,
        "product": product,
        "release_scope": scope,
        "official_source_url": official_url,
        "retrieved_date": retrieved,
        "document": original,
        "text": text,
    }


def _manifest_record(
    manifest_bytes: bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        data = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except VendorNoticeSupplementError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise VendorNoticeSupplementError(
            "vendor notice manifest is invalid JSON"
        ) from exc
    top = _keys(
        data,
        {"distribution", "version", "exact_pin", "selected_wheel_sha256"},
        {"vendor_document", "vendor_documents"},
        "vendor notice manifest",
    )
    if ("vendor_document" in top) == ("vendor_documents" in top):
        _fail("vendor notice manifest must contain vendor_document or vendor_documents")
    name = top["distribution"]
    version = top["version"]
    exact_pin = top["exact_pin"]
    wheel_sha = top["selected_wheel_sha256"]
    if (
        not isinstance(name, str)
        or not _NAME_RE.fullmatch(name)
        or not isinstance(version, str)
        or not _VERSION_RE.fullmatch(version)
        or not isinstance(exact_pin, str)
        or exact_pin != f"{name}=={version}"
        or not isinstance(wheel_sha, str)
        or not _HEX_RE.fullmatch(wheel_sha)
    ):
        _fail("vendor notice package identity is invalid")
    if "vendor_document" in top:
        raw_docs = [top["vendor_document"]]
    else:
        raw_docs = top["vendor_documents"]
        if not isinstance(raw_docs, list) or not raw_docs:
            _fail("vendor_documents must be a non-empty list")
    if len(raw_docs) > _MAX_DOCUMENTS_PER_MANIFEST:
        _fail("vendor notice manifest has too many documents")
    docs = [_vendor_document(item) for item in raw_docs]
    urls = [item["official_source_url"] for item in docs]
    if len(urls) != len(set(urls)):
        _fail("vendor notice manifest repeats an official source URL")
    return top, docs


def _locked_packages(packages: Iterable[Any]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    try:
        iterator = iter(packages)
    except TypeError as exc:
        raise VendorNoticeSupplementError("locked packages are invalid") from exc
    for package in iterator:
        name = getattr(package, "name", None)
        version = getattr(package, "version", None)
        hashes = getattr(package, "hashes", None)
        if (
            not isinstance(name, str)
            or not _NAME_RE.fullmatch(name)
            or not isinstance(version, str)
            or not _VERSION_RE.fullmatch(version)
            or not isinstance(hashes, (tuple, list, set, frozenset))
        ):
            _fail("locked package identity is invalid")
        normalized = _normalized_name(name)
        if normalized in selected:
            _fail("locked packages repeat a distribution")
        checked_hashes: set[str] = set()
        for item in hashes:
            if not isinstance(item, str):
                _fail("locked package hash is invalid")
            value = item.removeprefix("sha256:")
            if not _HEX_RE.fullmatch(value):
                _fail("locked package hash is invalid")
            checked_hashes.add(value)
        if not checked_hashes:
            _fail("locked package has no hashes")
        selected[normalized] = (version, checked_hashes)
    return selected


def _read_manifest(
    root: Path,
    manifest_text: Any,
) -> tuple[str, bytes, dict[str, Any], list[dict[str, Any]]]:
    relative = _safe_relative(manifest_text, "vendor notice manifest path")
    full, content = _safe_repo_file(
        root,
        relative.as_posix(),
        "vendor notice manifest",
        max_bytes=_MAX_MANIFEST_BYTES,
    )
    data, docs = _manifest_record(content)
    return full.as_posix(), content, data, docs


def _package_payloads(
    root: Path, destination: PurePosixPath, slug: str, manifest_path: str,
    manifest_sha: str, documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, bytes]], int]:
    """Validate original documents and assemble one package's notice payloads."""
    records: list[dict[str, Any]] = []
    files: list[tuple[str, bytes]] = []
    seen_outputs: set[str] = set()
    seen_source_paths: set[str] = set()
    package_total = 0
    for index, document in enumerate(documents, start=1):
        doc_rel, doc_bytes = _safe_repo_file(
            root,
            document["document"]["path"],
            "vendor original document",
            max_bytes=_MAX_DOCUMENT_BYTES,
        )
        text_rel, text_bytes = _safe_repo_file(
            root,
            document["text"]["path"],
            "vendor extracted text",
            max_bytes=_MAX_DOCUMENT_BYTES,
        )
        current_source_paths = {doc_rel.as_posix(), text_rel.as_posix()}
        if seen_source_paths.intersection(current_source_paths):
            _fail("vendor notice source file path is duplicated")
        seen_source_paths.update(current_source_paths)
        for label, item, content, relative in (
            ("document", document["document"], doc_bytes, doc_rel),
            ("text", document["text"], text_bytes, text_rel),
        ):
            if (
                len(content) != item["size_bytes"]
                or hashlib.sha256(content).hexdigest() != item["sha256"]
            ):
                _fail(f"vendor {label} differs from reviewed manifest")

        same_file = doc_rel == text_rel
        if same_file and doc_bytes != text_bytes:
            _fail("vendor document and text paths disagree")
        payloads = [("document", doc_rel, doc_bytes)]
        if not same_file:
            payloads.append(("text", text_rel, text_bytes))
        for role, relative, content in payloads:
            basename = relative.name
            if len(documents) == 1:
                output_name = basename
            else:
                output_name = f"{index:02d}-{basename}"
            bundle_path = (
                destination / slug / "vendor-supplements" / output_name
            ).as_posix()
            if bundle_path in seen_outputs:
                _fail("vendor notice output path is duplicated")
            seen_outputs.add(bundle_path)
            package_total += len(content)
            if package_total > _MAX_PACKAGE_BYTES:
                _fail("vendor notice supplements exceed package size limit")
            files.append((bundle_path, content))
            record = {
                "source_path": f"vendor-supplements/{output_name}",
                "bundle_path": bundle_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
                "manifest_path": manifest_path,
                "manifest_sha256": manifest_sha,
                "supplement_path": relative.as_posix(),
                "provenance": "reviewed-vendor-license-supplement",
                "content_role": (
                    ["original_vendor_document", "extracted_text"]
                    if same_file
                    else role
                ),
                "vendor_document": {
                    "publisher": document["publisher"],
                    "product": document["product"],
                    "release_scope": document["release_scope"],
                    "official_source_url": document["official_source_url"],
                    "retrieved_date": document["retrieved_date"],
                    "document_path": document["document"]["path"],
                    "document_sha256": document["document"]["sha256"],
                    "document_size_bytes": document["document"]["size_bytes"],
                    "text_path": document["text"]["path"],
                    "text_sha256": document["text"]["sha256"],
                    "text_size_bytes": document["text"]["size_bytes"],
                },
            }
            records.append(record)
    return records, files, package_total


def load_vendor_notice_supplements(
    spec: dict[str, Any],
    repo_root: Path,
    packages: Iterable[Any],
    bundle_dest: str,
) -> dict[str, tuple[list[dict[str, Any]], list[tuple[str, bytes]]]]:
    """Load locked vendor license documents and text from explicit manifests.

    The result maps normalized ``distribution==version`` pins to provenance
    records and ``(bundle_path, bytes)`` payloads. URLs are allowlisted metadata
    only; no network requests are made.
    """
    if not isinstance(spec, dict):
        _fail("vendor notice specification is invalid")
    notices = spec.get("dependency_notices", {})
    if not isinstance(notices, dict):
        _fail("dependency_notices configuration must be an object")
    manifest_paths = notices.get("vendor_supplements", [])
    if not isinstance(manifest_paths, list):
        _fail("vendor notice supplement configuration must be a list")
    if len(manifest_paths) > _MAX_MANIFESTS:
        _fail("vendor notice supplement configuration has too many manifests")
    if not manifest_paths:
        return {}

    root_input = Path(repo_root)
    if root_input.is_symlink():
        _fail("repository root is a symlink")
    try:
        root = root_input.resolve(strict=True)
    except OSError as exc:
        raise VendorNoticeSupplementError("repository root is missing") from exc
    if not root.is_dir():
        _fail("repository root is not a directory")
    destination = _safe_relative(str(bundle_dest), "vendor notice output directory")
    selected = _locked_packages(packages)
    seen_manifests: set[str] = set()
    seen_distributions: set[str] = set()
    result: dict[str, tuple[list[dict[str, Any]], list[tuple[str, bytes]]]] = {}
    all_total = 0

    for manifest_text in manifest_paths:
        manifest_path, manifest_bytes, top, documents = _read_manifest(
            root, manifest_text
        )
        if manifest_path in seen_manifests:
            _fail("vendor notice manifest path is duplicated")
        seen_manifests.add(manifest_path)
        normalized = _normalized_name(top["distribution"])
        if normalized in seen_distributions:
            _fail("vendor notice manifests repeat a distribution")
        seen_distributions.add(normalized)
        locked = selected.get(normalized)
        if locked is None:
            continue
        version, hashes = locked
        if (
            top["version"] != version
            or top["exact_pin"] != f"{top['distribution']}=={version}"
        ):
            _fail(f"vendor notice manifest version differs from lock: {normalized}")
        if top["selected_wheel_sha256"] not in hashes:
            _fail(f"vendor notice wheel hash is not selected by lock: {normalized}")

        slug = f"{normalized}-{version}"
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        records, files, package_total = _package_payloads(
            root, destination, slug, manifest_path, manifest_sha, documents
        )
        all_total += package_total
        if all_total > _MAX_ALL_BYTES:
            _fail("vendor notice supplements exceed total size limit")

        if not records:
            _fail(f"vendor notice manifest contains no documents: {normalized}")
        result[f"{normalized}=={version}"] = (records, files)

    return dict(sorted(result.items()))
