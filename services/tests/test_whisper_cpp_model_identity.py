"""STT bootstrap and download identity for the whisper.cpp GGML backend."""

from __future__ import annotations

from pathlib import Path

import pytest

from airunner_services.database.bootstrap.whisper import (
    UnsupportedWhisperModelError,
    WHISPER_FILES,
    get_whisper_cpp_model_spec,
)
from airunner_services.downloads import huggingface_download_worker as worker_mod
from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)
from airunner_services.model_management.model_registry import (
    ModelRegistry,
    ModelType,
)


def test_registered_whisper_backend_and_bootstrap_share_pinned_ggml_identity():
    model, = ModelRegistry().list_models(model_type=ModelType.SPEECH_TO_TEXT)
    spec = get_whisper_cpp_model_spec()

    assert model.runtime_backend == "whisper.cpp"
    assert model.preferred_runtime_format == "ggml"
    assert spec.repo_id == "ggerganov/whisper.cpp"
    assert spec.filename == "ggml-large-v3.bin"
    assert spec.revision == "c521a4b02f422512d734391fdf08bb08c0862f68"
    assert spec.sha256 == (
        "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845"
        "dfa11fb23594d1e2"
    )
    assert spec.size_bytes == 3_095_033_483
    assert WHISPER_FILES == {spec.repo_id: [spec.filename]}


@pytest.mark.parametrize(
    ("repo_id", "filenames", "env", "message"),
    [
        (
            "Systran/faster-distil-whisper-large-v3",
            None,
            {},
            "not supported by the whisper.cpp GGML runtime",
        ),
        (
            "ggerganov/whisper.cpp",
            ["model.bin"],
            {},
            "outside the pinned GGML model",
        ),
        (
            None,
            None,
            {"AIRUNNER_DEFAULT_STT_HF_PATH": "Systran/faster-distil-whisper-large-v3"},
            "not supported by the whisper.cpp GGML runtime",
        ),
        (
            "ggerganov/whisper.cpp",
            None,
            {"AIRUNNER_DEFAULT_STT_HF_PATH": "Systran/faster-distil-whisper-large-v3"},
            "Configured STT repository",
        ),
        (
            None,
            None,
            {"AIRUNNER_DEFAULT_STT_MODEL_FILENAME": "model.bin"},
            "not supported by the registered whisper.cpp model",
        ),
    ],
)
def test_incompatible_explicit_stt_identity_fails_before_download(
    repo_id, filenames, env, message, monkeypatch
):
    for name in (
        "AIRUNNER_DEFAULT_STT_HF_PATH",
        "AIRUNNER_DEFAULT_STT_MODEL_FILENAME",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(UnsupportedWhisperModelError, match=message):
        get_whisper_cpp_model_spec(repo_id=repo_id, filenames=filenames)


def test_worker_rejects_ctranslate2_repo_before_setting_or_network(
    tmp_path: Path, monkeypatch
):
    worker = HuggingFaceDownloadWorker()
    failures = []
    monkeypatch.setattr(worker, "emit_signal", lambda signal, payload: failures.append(payload))
    monkeypatch.setattr(
        worker_mod,
        "get_setting",
        lambda *args, **kwargs: pytest.fail("must reject before reading saved credentials"),
    )
    monkeypatch.setattr(
        worker,
        "_download_file",
        lambda *args, **kwargs: pytest.fail("must reject before starting a download"),
    )

    worker._download_model(
        repo_id="Systran/faster-distil-whisper-large-v3",
        model_type="stt",
        output_dir=str(tmp_path),
        missing_files=["ggml-large-v3.bin"],
    )

    assert len(failures) == 1
    assert "not supported by the whisper.cpp GGML runtime" in failures[0]["error"]
    assert not list(tmp_path.iterdir())


def test_worker_pins_whisper_revision():
    spec = get_whisper_cpp_model_spec()
    assert HuggingFaceDownloadWorker._resolve_bootstrap_revision(spec.repo_id) == (
        spec.revision
    )


@pytest.mark.parametrize("missing_files", [None, ["ggml-large-v3.bin"]])
def test_download_thread_receives_exact_whisper_size_revision_and_digest(
    tmp_path: Path, monkeypatch, missing_files
):
    worker = HuggingFaceDownloadWorker()
    captured = []
    monkeypatch.setattr(worker, "emit_signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        worker_mod,
        "get_setting",
        lambda *args, **kwargs: pytest.fail("public STT file must not read an API token"),
    )
    monkeypatch.setattr(worker, "_wait_for_completion", lambda count: False)
    monkeypatch.setattr(worker, "_cleanup_temp_files", lambda: None)

    class ThreadStub:
        def __init__(self, *, target, args, kwargs, daemon):
            captured.append({"target": target, "args": args, "kwargs": kwargs, "daemon": daemon})

        def start(self):
            return None

    monkeypatch.setattr(worker_mod.threading, "Thread", ThreadStub)
    spec = get_whisper_cpp_model_spec()

    worker._download_model(
        repo_id=spec.repo_id,
        model_type="stt",
        output_dir=str(tmp_path),
        missing_files=missing_files,
    )

    assert len(captured) == 1
    call = captured[0]
    assert call["args"][0:3] == (spec.repo_id, spec.filename, spec.size_bytes)
    assert call["kwargs"] == {
        "revision": spec.revision,
        "expected_sha256": spec.sha256,
    }
    assert call["args"][-1] == ""


def test_custom_local_whisper_model_path_remains_supported(
    tmp_path: Path, monkeypatch
):
    from airunner_services.runtimes.whisper_cpp_runtime_settings import (
        resolve_whisper_cpp_runtime_settings,
    )

    model = tmp_path / "custom-local-ggml.bin"
    model.write_bytes(b"local user-selected model fixture")
    monkeypatch.setenv("AIRUNNER_WHISPER_MODEL_PATH", str(model))
    settings = resolve_whisper_cpp_runtime_settings(path_settings=object())
    assert settings.model_path == str(model)
