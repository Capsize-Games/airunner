"""Relocated speech data stays paired with the selected bundle executable."""

from pathlib import Path

import pytest

from airunner_services.runtimes.espeak_cli_renderer import (
    EspeakCliRenderer,
    EspeakRenderError,
)
from airunner_services.runtimes.espeak_runtime_paths import (
    ESPEAK_EXECUTABLE,
    resolve_espeak_runtime_paths,
)


def _bundle(root: Path) -> tuple[Path, Path]:
    binary = root / "bin/espeak-ng"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"fixture binary")
    binary.chmod(0o755)
    data = root / "share/espeak-ng-data"
    data.mkdir(parents=True)
    for name in ("phontab", "phonindex", "phondata", "intonations"):
        (data / name).write_bytes(b"fixture data")
    return binary, data


def test_host_selection_keeps_fixed_path_and_ignores_path_search(monkeypatch):
    monkeypatch.delenv("AIRUNNER_BUNDLE_ROOT", raising=False)
    monkeypatch.setenv("PATH", "/untrusted")
    assert resolve_espeak_runtime_paths().command_prefix() == [ESPEAK_EXECUTABLE]


def test_bundle_selection_passes_data_before_voice_catalogue(tmp_path, monkeypatch):
    binary, data = _bundle(tmp_path)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    renderer = EspeakCliRenderer()
    assert renderer._command_prefix() == [str(binary), f"--path={data.parent}"]


def test_missing_bundle_is_lazy_and_never_uses_host_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    renderer = EspeakCliRenderer(popen=lambda *_a, **_k: pytest.fail("must not spawn"))
    assert renderer.voice_ids is None
    with pytest.raises(EspeakRenderError) as error:
        renderer.catalogue()
    assert error.value.code == "tts_backend_unavailable"


@pytest.mark.parametrize("escaped", ["binary", "data", "resource"])
def test_bundle_rejects_external_symlink(tmp_path, monkeypatch, escaped):
    bundle = tmp_path / "bundle"
    binary, data = _bundle(bundle)
    outside = tmp_path / "outside"
    outside.mkdir()
    if escaped == "binary":
        target = outside / "engine"
        target.write_bytes(b"outside")
        target.chmod(0o755)
        binary.unlink()
        binary.symlink_to(target)
    elif escaped == "data":
        import shutil

        shutil.move(str(data), outside / "data")
        data.symlink_to(outside / "data", target_is_directory=True)
    else:
        target = outside / "phontab"
        target.write_bytes(b"outside")
        (data / "phontab").unlink()
        (data / "phontab").symlink_to(target)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(bundle))
    with pytest.raises(OSError):
        resolve_espeak_runtime_paths().command_prefix()
