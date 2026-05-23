"""Tests for bundled native runtime executable discovery."""

from types import SimpleNamespace

from airunner.runtimes import bundled_runtime_paths
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    resolve_llama_cpp_runtime_settings,
)
from airunner_services.runtimes.whisper_cpp_runtime_settings import (
    resolve_whisper_cpp_runtime_settings,
)


def test_resolve_runtime_executable_prefers_env_override(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLAMA_SERVER_BIN", "~/custom/llama-server")

    executable = bundled_runtime_paths.resolve_runtime_executable(
        "AIRUNNER_LLAMA_SERVER_BIN",
        "llama-server",
    )

    assert executable.endswith("custom/llama-server")


def test_resolve_runtime_executable_uses_bundle_binary(monkeypatch, tmp_path):
    bundled_binary = tmp_path / "bin" / "llama-server"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    monkeypatch.delenv("AIRUNNER_LLAMA_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))

    executable = bundled_runtime_paths.resolve_runtime_executable(
        "AIRUNNER_LLAMA_SERVER_BIN",
        "llama-server",
    )

    assert executable == str(bundled_binary)


def test_resolve_runtime_executable_uses_windows_suffix(
    monkeypatch,
    tmp_path,
):
    bundled_binary = tmp_path / "bin" / "whisper-server.exe"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    monkeypatch.delenv("AIRUNNER_WHISPER_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setattr(bundled_runtime_paths, "IS_WINDOWS", True)

    executable = bundled_runtime_paths.resolve_runtime_executable(
        "AIRUNNER_WHISPER_SERVER_BIN",
        "whisper-server",
    )

    assert executable == str(bundled_binary)


def test_llama_settings_use_bundled_sidecar(monkeypatch, tmp_path):
    bundled_binary = tmp_path / "bin" / "llama-server"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    monkeypatch.delenv("AIRUNNER_LLAMA_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "airunner_services.runtimes.llama_cpp_runtime_settings._load_llm_settings",
        lambda: None,
    )
    monkeypatch.setattr(
        "airunner_services.runtimes.llama_cpp_runtime_settings._load_path_settings",
        lambda: None,
    )

    settings = resolve_llama_cpp_runtime_settings()

    assert settings.executable == str(bundled_binary)


def test_whisper_settings_use_bundled_sidecar(monkeypatch, tmp_path):
    bundled_binary = tmp_path / "bin" / "whisper-server"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    monkeypatch.delenv("AIRUNNER_WHISPER_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "airunner_services.runtimes.whisper_cpp_runtime_settings._load_path_settings",
        lambda: None,
    )

    settings = resolve_whisper_cpp_runtime_settings()

    assert settings.executable == str(bundled_binary)


def test_whisper_settings_ignore_non_ggml_bins(monkeypatch, tmp_path):
    bundled_binary = tmp_path / "bin" / "whisper-server"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    model_dir = tmp_path / "text" / "models" / "stt" / "legacy"
    model_dir.mkdir(parents=True)
    (model_dir / "model.bin").write_text("model")
    monkeypatch.delenv("AIRUNNER_WHISPER_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "airunner_services.runtimes.whisper_cpp_runtime_settings._load_path_settings",
        lambda: SimpleNamespace(
            base_path=str(tmp_path),
            stt_model_path=str(model_dir),
        ),
    )

    settings = resolve_whisper_cpp_runtime_settings()

    assert settings.model_path is None
    assert settings.model_id is None


def test_whisper_settings_prefer_ggml_bins(monkeypatch, tmp_path):
    bundled_binary = tmp_path / "bin" / "whisper-server"
    bundled_binary.parent.mkdir(parents=True)
    bundled_binary.write_text("binary")
    model_dir = tmp_path / "text" / "models" / "stt"
    model_dir.mkdir(parents=True)
    (model_dir / "model.bin").write_text("legacy")
    ggml_path = model_dir / "ggml-base.en.bin"
    ggml_path.write_text("ggml")
    monkeypatch.delenv("AIRUNNER_WHISPER_SERVER_BIN", raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "airunner_services.runtimes.whisper_cpp_runtime_settings._load_path_settings",
        lambda: SimpleNamespace(
            base_path=str(tmp_path),
            stt_model_path=str(model_dir),
        ),
    )

    settings = resolve_whisper_cpp_runtime_settings()

    assert settings.model_path == str(ggml_path)
    assert settings.model_id == "ggml-base.en.bin"