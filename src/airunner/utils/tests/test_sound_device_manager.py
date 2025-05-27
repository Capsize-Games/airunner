"""
Tests for SoundDeviceManager in airunner.utils.audio.sound_device_manager.
Covers: device index lookup, stream initialization, error handling, read/write, and cleanup.
All sounddevice and numpy dependencies are mocked for headless/CI safety.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np
from airunner.utils.audio.sound_device_manager import SoundDeviceManager


@pytest.fixture
def sdm():
    return SoundDeviceManager()


@patch("sounddevice.query_devices")
def test_get_devices(mock_query, sdm):
    mock_query.return_value = [
        {
            "name": "pulse",
            "index": 0,
            "max_input_channels": 2,
            "max_output_channels": 2,
        },
        {
            "name": "test",
            "index": 1,
            "max_input_channels": 1,
            "max_output_channels": 0,
        },
    ]
    devices = sdm.get_devices()
    assert isinstance(devices, list)
    assert devices[0]["name"] == "pulse"


@patch("sounddevice.query_devices")
@patch("sounddevice.default")
def test_get_input_output_device_index(mock_default, mock_query, sdm):
    mock_query.return_value = [
        {
            "name": "pulse",
            "index": 0,
            "max_input_channels": 2,
            "max_output_channels": 2,
        },
        {
            "name": "test",
            "index": 1,
            "max_input_channels": 1,
            "max_output_channels": 0,
        },
    ]
    mock_default.device = (0, 1)
    # Exact match
    assert sdm.get_input_device_index("pulse") == 0
    # Substring match
    assert sdm.get_input_device_index("pul") == 0
    # Fallback to default
    assert sdm.get_input_device_index("notfound") == 0
    # Output
    assert sdm.get_output_device_index("pulse") == 0
    assert sdm.get_output_device_index("notfound") == 1


@patch("sounddevice.InputStream")
@patch.object(SoundDeviceManager, "get_input_device_index", return_value=2)
def test_initialize_input_stream_success(mock_idx, mock_stream, sdm):
    mock_stream.return_value = MagicMock(start=MagicMock())
    assert sdm.initialize_input_stream(device_name="pulse")
    assert sdm._in_stream is not None
    assert sdm.initialized


# Helper to ensure logger is set up for tests
import logging


def _ensure_logger_for_test():
    logger = logging.getLogger("airunner.utils.audio.sound_device_manager")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


@patch("sounddevice.InputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_input_device_index", return_value=2)
def test_initialize_input_stream_error(mock_idx, mock_stream, sdm):
    _ensure_logger_for_test()
    assert not sdm.initialize_input_stream(device_name="pulse")


@patch("sounddevice.InputStream", side_effect=ImportError)
@patch.object(SoundDeviceManager, "get_input_device_index", return_value=2)
def test_initialize_input_stream_unexpected_error(mock_idx, mock_stream, sdm):
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_input_stream(device_name="pulse")
        mock_log.assert_called()


@patch("sounddevice.InputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_input_device_index", return_value=None)
def test_initialize_input_stream_device_none(mock_idx, mock_stream, sdm):
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_input_stream(device_name="pulse")
        mock_log.assert_called()


@patch("sounddevice.InputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_input_device_index", return_value=None)
def test_initialize_input_stream_device_none_error_branch(mock_idx, mock_stream, sdm):
    # Covers the branch where device_index is None and error is logged
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_input_stream(device_name="pulse")
        mock_log.assert_called_with("Input device 'pulse' not found")


@patch("sounddevice.OutputStream")
@patch.object(SoundDeviceManager, "get_output_device_index", return_value=3)
def test_initialize_output_stream_success(mock_idx, mock_stream, sdm):
    mock_stream.return_value = MagicMock(start=MagicMock())
    assert sdm.initialize_output_stream(device_name="pulse")
    assert sdm._out_stream is not None
    assert sdm.initialized


@patch("sounddevice.OutputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_output_device_index", return_value=3)
def test_initialize_output_stream_error(mock_idx, mock_stream, sdm):
    _ensure_logger_for_test()
    assert not sdm.initialize_output_stream(device_name="pulse")


@patch("sounddevice.OutputStream", side_effect=ImportError)
@patch.object(SoundDeviceManager, "get_output_device_index", return_value=2)
def test_initialize_output_stream_unexpected_error(mock_idx, mock_stream, sdm):
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_output_stream(device_name="pulse")
        mock_log.assert_called()


@patch("sounddevice.OutputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_output_device_index", return_value=None)
def test_initialize_output_stream_device_none(mock_idx, mock_stream, sdm):
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_output_stream(device_name="pulse")
        mock_log.assert_called()


@patch("sounddevice.OutputStream", side_effect=Exception("fail"))
@patch.object(SoundDeviceManager, "get_output_device_index", return_value=None)
def test_initialize_output_stream_device_none_error_branch(mock_idx, mock_stream, sdm):
    # Covers the branch where device_index is None and error is logged
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.initialize_output_stream(device_name="pulse")
        mock_log.assert_called_with("Output device 'pulse' not found")


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_success(mock_out, sdm):
    mock_out.active = True
    mock_out.channels = 1
    mock_out.write = MagicMock()
    arr = np.ones(10, dtype=np.float32)
    sdm._out_stream = mock_out
    assert sdm.write_to_output(arr)
    mock_out.write.assert_called_once()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_amplify_and_convert(mock_out, sdm):
    mock_out.active = True
    mock_out.channels = 2
    mock_out.write = MagicMock()
    arr = np.full(10, 0.01, dtype=np.float32)
    sdm._out_stream = mock_out
    assert sdm.write_to_output(arr)
    mock_out.write.assert_called_once()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_inactive(mock_out, sdm):
    _ensure_logger_for_test()
    mock_out.active = False
    sdm._out_stream = mock_out
    assert not sdm.write_to_output(np.ones(10))


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_error(mock_out, sdm):
    _ensure_logger_for_test()
    mock_out.active = True
    mock_out.channels = 1
    mock_out.write = MagicMock(side_effect=Exception("fail"))
    sdm._out_stream = mock_out
    assert not sdm.write_to_output(np.ones(10))


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_exception(mock_out, sdm):
    mock_out.active = True
    mock_out.channels = 1

    def raise_exception(*a, **k):
        raise Exception("fail")

    mock_out.write = raise_exception
    sdm._out_stream = mock_out
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.write_to_output(np.ones(10))
        mock_log.assert_called()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_none_stream(mock_out, sdm):
    # Covers the branch where _out_stream is None
    sdm._out_stream = None
    assert not sdm.write_to_output(np.ones(10))


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_inactive_stream(mock_out, sdm):
    # Covers the branch where _out_stream is present but not active
    mock_out.active = False
    sdm._out_stream = mock_out
    assert not sdm.write_to_output(np.ones(10))


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_read_from_input_success(mock_in, sdm):
    mock_in.active = True
    mock_in.read = MagicMock(return_value=(np.ones(10), True))
    sdm._in_stream = mock_in
    data, ok = sdm.read_from_input(10)
    assert ok
    assert isinstance(data, np.ndarray)


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_read_from_input_error(mock_in, sdm):
    _ensure_logger_for_test()
    mock_in.active = True
    mock_in.read = MagicMock(side_effect=Exception("fail"))
    sdm._in_stream = mock_in
    data, ok = sdm.read_from_input(10)
    assert not ok
    assert data is None


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_read_from_input_inactive_stream(mock_in, sdm):
    # Covers the branch where _in_stream is present but not active
    mock_in.active = False
    sdm._in_stream = mock_in
    data, ok = sdm.read_from_input(10)
    assert data is None
    assert ok is False


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_read_from_input_none_stream(mock_in, sdm):
    # Covers the branch where _in_stream is None
    sdm._in_stream = None
    data, ok = sdm.read_from_input(10)
    assert data is None
    assert ok is False


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_stop_input_stream(mock_in, sdm):
    mock_in.stop = MagicMock()
    mock_in.close = MagicMock()
    sdm._in_stream = mock_in
    sdm._stop_input_stream()
    mock_in.stop.assert_called_once()
    mock_in.close.assert_called_once()
    assert sdm._in_stream is None


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_stop_output_stream(mock_out, sdm):
    mock_out.stop = MagicMock()
    mock_out.close = MagicMock()
    sdm._out_stream = mock_out
    sdm._stop_output_stream()
    mock_out.stop.assert_called_once()
    mock_out.close.assert_called_once()
    assert sdm._out_stream is None


def test_stop_all_streams(sdm):
    with patch.object(sdm, "_stop_input_stream") as stop_in, patch.object(
        sdm, "_stop_output_stream"
    ) as stop_out:
        sdm.stop_all_streams()
        stop_in.assert_called_once()
        stop_out.assert_called_once()
        assert not sdm.initialized


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_in_stream_property_triggers_init(mock_in, sdm):
    sdm._in_stream = None
    with patch.object(sdm, "initialize_input_stream") as mock_init:
        mock_init.return_value = True
        _ = sdm.in_stream
        mock_init.assert_called_once()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_out_stream_property_triggers_init(mock_out, sdm):
    sdm._out_stream = None
    with patch.object(sdm, "initialize_output_stream") as mock_init:
        mock_init.return_value = True
        _ = sdm.out_stream
        mock_init.assert_called_once()


@patch("sounddevice.query_devices", side_effect=Exception("fail"))
def test_get_devices_error(mock_query, sdm):
    # Should raise and be caught in _get_device_index
    with patch.object(sdm.logger, "error") as mock_log:
        idx = sdm._get_device_index("foo")
        assert idx is None
        mock_log.assert_called()


@patch(
    "sounddevice.query_devices",
    return_value=[
        {
            "name": "pulse",
            "index": 0,
            "max_input_channels": 2,
            "max_output_channels": 2,
        }
    ],
)
def test_get_device_index_no_kind_match(mock_query, sdm):
    # Should return None if no kind matches
    idx = sdm._get_device_index("pulse", kind="nonexistent")
    assert idx is None


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_stop_input_stream_error(mock_in, sdm):
    mock_in.stop = MagicMock(side_effect=Exception("fail"))
    mock_in.close = MagicMock()
    with patch.object(sdm.logger, "error") as mock_log:
        sdm._in_stream = mock_in
        sdm._stop_input_stream()
        mock_log.assert_called()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_stop_output_stream_error(mock_out, sdm):
    mock_out.stop = MagicMock(side_effect=Exception("fail"))
    mock_out.close = MagicMock()
    with patch.object(sdm.logger, "error") as mock_log:
        sdm._out_stream = mock_out
        sdm._stop_output_stream()
        mock_log.assert_called()


@patch.object(SoundDeviceManager, "_out_stream", create=True)
def test_write_to_output_portaudioerror(mock_out, sdm):
    import sounddevice as sd

    mock_out.active = True
    mock_out.channels = 1

    def raise_portaudio(*a, **k):
        raise sd.PortAudioError("fail")

    mock_out.write = raise_portaudio
    sdm._out_stream = mock_out
    with patch.object(sdm.logger, "error") as mock_log:
        assert not sdm.write_to_output(np.ones(10))
        mock_log.assert_called()


@patch.object(SoundDeviceManager, "_in_stream", create=True)
def test_read_from_input_portaudioerror(mock_in, sdm):
    import sounddevice as sd

    mock_in.active = True

    def raise_portaudio(*a, **k):
        raise sd.PortAudioError("fail")

    mock_in.read = raise_portaudio
    sdm._in_stream = mock_in
    with patch.object(sdm.logger, "error") as mock_log:
        data, ok = sdm.read_from_input(10)
        assert not ok
        assert data is None
        mock_log.assert_called()
