"""Pinned embedded Python runtime helpers for AIRunner bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PINS_RELATIVE_PATH = Path("native/embedded_python/python_runtime_pins.env")


@dataclass(frozen=True)
class EmbeddedPythonRuntime:
    """Pinned download metadata for one embedded Python runtime."""

    target_platform: str
    version: str
    release_tag: str
    base_url: str
    asset_name: str

    @property
    def download_url(self) -> str:
        """Return the fully qualified download URL for the runtime."""
        return f"{self.base_url}/{self.release_tag}/{self.asset_name}"


def pins_file_path() -> Path:
    """Return the repository path for the embedded Python pin file."""
    return Path(__file__).resolve().parents[3] / PINS_RELATIVE_PATH


def load_pins(path: Path | None = None) -> dict[str, str]:
    """Load key-value pins from the embedded Python pin file."""
    pins_path = path or pins_file_path()
    values: dict[str, str] = {}
    for line in pins_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def asset_key_for_platform(target_platform: str) -> str:
    """Return the pin-file key for one target platform."""
    asset_keys = {
        "linux": "AIRUNNER_PYTHON_LINUX_ASSET",
        "windows": "AIRUNNER_PYTHON_WINDOWS_ASSET",
    }
    try:
        return asset_keys[target_platform]
    except KeyError as error:
        raise ValueError(f"Unsupported target platform: {target_platform}") from error


def get_embedded_python_runtime(
    target_platform: str,
    path: Path | None = None,
) -> EmbeddedPythonRuntime:
    """Return the pinned embedded Python runtime for one platform."""
    pins = load_pins(path)
    return EmbeddedPythonRuntime(
        target_platform=target_platform,
        version=pins["AIRUNNER_PYTHON_VERSION"],
        release_tag=pins["AIRUNNER_PYTHON_RELEASE_TAG"],
        base_url=pins["AIRUNNER_PYTHON_RELEASE_BASE_URL"],
        asset_name=pins[asset_key_for_platform(target_platform)],
    )