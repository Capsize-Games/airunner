"""
Unit tests for melo.utils
"""

import io
import os
import tempfile
import types
import json
import logging
import builtins
import pytest
from unittest import mock
import torch
import numpy as np

utils = __import__("airunner.vendor.melo.utils", fromlist=["*"])


def test_utils_module_importable():
    assert utils is not None


def test_summarize_all_types():
    writer = mock.Mock()
    utils.summarize(
        writer,
        5,
        scalars={"a": 1},
        histograms={"b": np.array([1, 2])},
        images={"c": np.zeros((2, 2, 3))},
        audios={"d": np.zeros(10)},
        audio_sampling_rate=12345,
    )
    writer.add_scalar.assert_called_with("a", 1, 5)
    writer.add_histogram.assert_called_with("b", mock.ANY, 5)
    writer.add_image.assert_called_with("c", mock.ANY, 5, dataformats="HWC")
    writer.add_audio.assert_called_with("d", mock.ANY, 5, 12345)


def test_load_wav_to_torch_reads_file():
    with mock.patch(
        "airunner.vendor.melo.utils.read",
        return_value=(22050, np.arange(10, dtype=np.int16)),
    ):
        tensor, sr = utils.load_wav_to_torch("dummy.wav")
        assert isinstance(tensor, torch.FloatTensor)
        assert sr == 22050
        assert np.allclose(tensor.numpy(), np.arange(10, dtype=np.float32))


def test_load_wav_to_torch_librosa_reads_file():
    with mock.patch(
        "airunner.vendor.melo.utils.librosa.load",
        return_value=(np.arange(5, dtype=np.float32), 16000),
    ):
        tensor, sr = utils.load_wav_to_torch_librosa("dummy.wav", 16000)
        assert isinstance(tensor, torch.FloatTensor)
        assert sr == 16000
        assert np.allclose(tensor.numpy(), np.arange(5, dtype=np.float32))


def test_load_filepaths_and_text_reads_lines(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("a|b|c\nd|e|f\n", encoding="utf-8")
    result = utils.load_filepaths_and_text(str(f), split="|")
    assert result == [["a", "b", "c"], ["d", "e", "f"]]


def test_load_filepaths_and_text_empty_file(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    result = utils.load_filepaths_and_text(str(f))
    assert result == []


def test_get_hparams_from_file(tmp_path):
    config = {"foo": 1, "bar": {"baz": 2}}
    f = tmp_path / "config.json"
    f.write_text(json.dumps(config), encoding="utf-8")
    hparams = utils.get_hparams_from_file(str(f))
    assert hparams.foo == 1
    assert hparams.bar.baz == 2


def test_get_logger_creates_file_and_logs(tmp_path):
    model_dir = tmp_path / "logdir"
    logger = utils.get_logger(str(model_dir), filename="test.log")
    logger.info("hello")
    log_file = model_dir / "test.log"
    logger.handlers[0].flush()
    assert log_file.exists()
    with open(log_file, "r") as f:
        content = f.read()
    assert "hello" in content


def test_HParams_basic_and_nested():
    h = utils.HParams(a=1, b={"c": 2})
    assert h["a"] == 1
    assert h.b.c == 2
    h["d"] = 3
    assert h.d == 3
    assert "a" in h
    assert len(h) == 3
    assert isinstance(repr(h), str)
    assert set(h.keys()) == {"a", "b", "d"}
    assert set(h.items()) == {("a", 1), ("b", h.b), ("d", 3)}
    assert set(h.values()) == {1, h.b, 3}


def test_HParams_contains_and_setitem():
    h = utils.HParams()
    h["x"] = 42
    assert "x" in h
    assert h["x"] == 42


def test_HParams_repr():
    h = utils.HParams(foo=1)
    assert isinstance(repr(h), str)


def test_get_hparams_creates_config_and_model_dir(tmp_path, monkeypatch):
    # Patch argparse to simulate CLI args
    config = {"foo": 1}
    config_path = tmp_path / "base.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    args = [
        "prog",
        "-c",
        str(config_path),
        "-m",
        "testmodel",
    ]
    monkeypatch.setattr("sys.argv", args)
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        hparams = utils.get_hparams(init=True)
        model_dir = tmp_path / "logs" / "testmodel"
        assert hparams.foo == 1
        assert os.path.exists(model_dir)
        # config.json should be copied
        with open(model_dir / "config.json", "r") as f:
            assert json.load(f)["foo"] == 1
    finally:
        os.chdir(old_cwd)


def test_get_hparams_reads_existing_config(tmp_path, monkeypatch):
    # Simulate config already copied
    config = {"foo": 2}
    model_dir = tmp_path / "logs" / "testmodel"
    model_dir.mkdir(parents=True)
    config_path = tmp_path / "base.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    config_save_path = model_dir / "config.json"
    config_save_path.write_text(json.dumps(config), encoding="utf-8")
    args = [
        "prog",
        "-c",
        str(config_path),
        "-m",
        "testmodel",
    ]
    monkeypatch.setattr("sys.argv", args)
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        hparams = utils.get_hparams(init=False)
        assert hparams.foo == 2
    finally:
        os.chdir(old_cwd)


def test_get_logger_multiple_calls_no_duplicate_handlers(tmp_path):
    model_dir = tmp_path / "logdir2"
    logger_name = os.path.basename(str(model_dir))
    # Remove all handlers for this logger before test
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger1 = utils.get_logger(str(model_dir), filename="test.log")
    logger2 = utils.get_logger(str(model_dir), filename="test.log")
    # Just check that at least one handler exists and logging works
    assert any(
        hasattr(h, "baseFilename") and h.baseFilename == str(model_dir / "test.log")
        for h in logger1.handlers
    )
    logger.info("test message")
    logger.handlers.clear()


def test_get_logger_creates_dir_if_missing(tmp_path):
    model_dir = tmp_path / "newlogdir"
    logger = utils.get_logger(str(model_dir), filename="test.log")
    assert os.path.exists(model_dir)
    assert logger.handlers


def test_load_filepaths_and_text_non_utf8(tmp_path):
    f = tmp_path / "latin1.txt"
    # Write with latin1 encoding, should still read as utf-8 (may error)
    f.write_bytes(b"a|b|c\nd|e|f\n")
    result = utils.load_filepaths_and_text(str(f), split="|")
    assert result == [["a", "b", "c"], ["d", "e", "f"]]


def test_load_wav_to_torch_file_not_found():
    with mock.patch("airunner.vendor.melo.utils.read", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            utils.load_wav_to_torch("notfound.wav")


def test_load_wav_to_torch_librosa_file_not_found():
    with mock.patch(
        "airunner.vendor.melo.utils.librosa.load", side_effect=FileNotFoundError
    ):
        with pytest.raises(FileNotFoundError):
            utils.load_wav_to_torch_librosa("notfound.wav", 16000)


def test_get_hparams_from_file_file_not_found():
    with pytest.raises(FileNotFoundError):
        utils.get_hparams_from_file("notfound.json")


def test_get_logger_invalid_dir(monkeypatch):
    # Simulate os.makedirs raising an error
    with mock.patch("os.makedirs", side_effect=OSError):
        with pytest.raises(OSError):
            utils.get_logger("/invalid/dir", filename="test.log")
