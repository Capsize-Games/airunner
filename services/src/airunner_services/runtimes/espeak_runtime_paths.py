"""Select fixed host or bundle-owned eSpeak executable and voice data."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


ESPEAK_EXECUTABLE = "/usr/bin/espeak-ng"


@dataclass(frozen=True)
class EspeakRuntimePaths:
    """Executable and optional voice data selected for one renderer."""

    executable: str
    data_dir: Path | None = None
    bundle_root: Path | None = None

    def command_prefix(self) -> list[str]:
        """Validate bundle-owned files lazily, without invoking the engine."""
        if self.bundle_root is not None:
            binary = Path(self.executable)
            if (
                not binary.is_file()
                or not os.access(binary, os.X_OK)
                or not binary.resolve().is_relative_to(self.bundle_root)
            ):
                raise OSError("Bundled speech executable is unavailable")
        if self.data_dir is None:
            return [self.executable]
        data = self.data_dir.resolve()
        if (
            not data.is_dir()
            or (
                self.bundle_root is not None
                and not data.is_relative_to(self.bundle_root)
            )
        ):
            raise OSError("Speech voice data is unavailable")
        for filename in ("phontab", "phonindex", "phondata", "intonations"):
            resource = data / filename
            if not resource.is_file() or not resource.resolve().is_relative_to(data):
                raise OSError("Speech voice data is incomplete")
        # The CLI processes --voices immediately; set its data path first.
        return [self.executable, f"--path={data.parent}"]


def resolve_espeak_runtime_paths(
    executable: str | None = None,
    data_dir: str | Path | None = None,
) -> EspeakRuntimePaths:
    """Resolve once without PATH search, file writes or process startup."""
    if executable is not None:
        return EspeakRuntimePaths(executable, Path(data_dir) if data_dir else None)
    root = os.environ.get("AIRUNNER_BUNDLE_ROOT", "").strip()
    if root:
        bundle = Path(root).expanduser().resolve()
        if data_dir is not None:
            raise ValueError("Bundled speech data cannot be overridden")
        return EspeakRuntimePaths(
            str(bundle / "bin/espeak-ng"), bundle / "share/espeak-ng-data", bundle
        )
    return EspeakRuntimePaths(ESPEAK_EXECUTABLE, Path(data_dir) if data_dir else None)
