"""Manifest helpers for external plugins and extensions."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


LOGGER = logging.getLogger(__name__)
MANIFEST_FILENAME = "airunner-extension.json"
EXTENSION_ALLOWLIST_ENV = "AIRUNNER_ENABLED_EXTENSIONS"
PLUGIN_ALLOWLIST_ENV = "AIRUNNER_ENABLED_PLUGINS"


@dataclass(frozen=True)
class ExtensionManifest:
    """Validated metadata for an external extension or plugin."""

    extension_id: str
    name: str
    version: str
    kind: str
    module_name: str
    entry_path: Path


def load_enabled_extension_ids(env_var: str) -> set[str]:
    """Return the explicitly enabled extension identifiers."""
    raw_value = os.environ.get(env_var, "")
    return {
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    }


def resolve_enabled_manifest(
    extension_dir: Path,
    *,
    default_entry_point: str,
    enabled_ids: set[str],
    expected_kind: str,
) -> Optional[ExtensionManifest]:
    """Return a validated manifest when a directory is explicitly enabled."""
    manifest = load_extension_manifest(
        extension_dir,
        default_entry_point=default_entry_point,
        expected_kind=expected_kind,
    )
    if manifest is None:
        return None
    if manifest.extension_id not in enabled_ids:
        LOGGER.info("Skipping disabled %s: %s", expected_kind, manifest.name)
        return None
    return manifest


def load_extension_manifest(
    extension_dir: Path,
    *,
    default_entry_point: str,
    expected_kind: str,
) -> Optional[ExtensionManifest]:
    """Read and validate a manifest for an external extension directory."""
    data = _read_manifest_data(extension_dir / MANIFEST_FILENAME)
    if data is None:
        return None
    return _build_manifest(
        data,
        extension_dir,
        default_entry_point=default_entry_point,
        expected_kind=expected_kind,
    )


def _read_manifest_data(manifest_path: Path) -> Optional[dict[str, object]]:
    """Read a manifest file if it exists and contains a JSON object."""
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Invalid extension manifest: %s", manifest_path)
        return None
    if isinstance(payload, dict):
        return payload
    LOGGER.warning("Extension manifest must be an object: %s", manifest_path)
    return None


def _build_manifest(
    data: dict[str, object],
    extension_dir: Path,
    *,
    default_entry_point: str,
    expected_kind: str,
) -> Optional[ExtensionManifest]:
    """Build a validated manifest object from raw JSON data."""
    extension_id = _read_required_field(data, "id")
    name = _read_required_field(data, "name")
    version = _read_required_field(data, "version")
    kind = _read_required_field(data, "kind")
    entry_name = _read_optional_field(data, "entry_point") or default_entry_point
    entry_path = _resolve_entry_path(extension_dir, entry_name)
    if None in (extension_id, name, version, kind, entry_path):
        return None
    if kind != expected_kind:
        LOGGER.warning("Unexpected manifest kind for %s", extension_dir)
        return None
    return ExtensionManifest(
        extension_id=extension_id,
        name=name,
        version=version,
        kind=kind,
        module_name=extension_dir.name,
        entry_path=entry_path,
    )


def _read_required_field(
    data: dict[str, object],
    field_name: str,
) -> Optional[str]:
    """Return a required string field from manifest data."""
    value = _read_optional_field(data, field_name)
    if value is not None:
        return value
    LOGGER.warning("Missing manifest field '%s'", field_name)
    return None


def _read_optional_field(
    data: dict[str, object],
    field_name: str,
) -> Optional[str]:
    """Return an optional trimmed string field from manifest data."""
    value = data.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _resolve_entry_path(
    extension_dir: Path,
    entry_name: str,
) -> Optional[Path]:
    """Resolve a manifest entry point and keep it inside the extension root."""
    root_path = extension_dir.resolve()
    candidate = (root_path / entry_name).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        LOGGER.warning("Entry point escapes extension root: %s", extension_dir)
        return None
    if candidate.is_file():
        return candidate
    LOGGER.warning("Missing extension entry point: %s", candidate)
    return None