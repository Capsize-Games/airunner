"""Unit tests for the x4 tile batch extraction helpers.

_process_one_tile_batch, _process_and_paste_batch, and
_handle_tile_batch_error were extracted to keep
_process_all_tile_batches within the long-function threshold. These
tests pin the error taxonomy, the OOM state re-order, and the
paste wiring.
"""

from unittest.mock import MagicMock

import pytest

from airunner_services.application_exceptions import InterruptedException
from airunner_services.art.managers.stablediffusion.x4_upscale_mixins.x4_upscaling_tiling_mixin import (
    X4UpscalingTilingMixin,
)


def _make_obj():
    obj = X4UpscalingTilingMixin.__new__(X4UpscalingTilingMixin)
    obj.logger = MagicMock()
    obj._is_out_of_memory = MagicMock(return_value=False)
    obj._handle_oom = MagicMock(return_value=None)
    obj._process_tile_batch = MagicMock(return_value=[])
    obj._paste_tiles_into_output = MagicMock(return_value=5)
    return obj


ARGS = ("bs", "ts", "red", "img", 10)


def test_handle_error_interrupted_reraises():
    obj = _make_obj()
    obj._is_out_of_memory.return_value = True
    with pytest.raises(InterruptedException):
        obj._handle_tile_batch_error(InterruptedException("stop"), 0, *ARGS)


def test_handle_error_oom_returns_reordered_state():
    obj = _make_obj()
    obj._is_out_of_memory.return_value = True
    obj._handle_oom.return_value = (
        2, 256, 1, ["tiles"], 9, 3, "out"
    )
    state = obj._handle_tile_batch_error(
        RuntimeError("oom"), 0, "bs", "ts", "red", "img", 10
    )
    assert state == ("out", 2, 256, 1, ["tiles"], 9, 3)


def test_handle_error_oom_without_recovery_raises():
    obj = _make_obj()
    obj._is_out_of_memory.return_value = True
    obj._handle_oom.return_value = None
    with pytest.raises(RuntimeError, match="boom"):
        obj._handle_tile_batch_error(
            RuntimeError("boom"), 0, "bs", "ts", "red", "img", 10
        )


def test_handle_error_plain_reraises():
    obj = _make_obj()
    with pytest.raises(ValueError, match="bad"):
        obj._handle_tile_batch_error(
            ValueError("bad"), 0, "bs", "ts", "red", "img", 10
        )


def test_process_and_paste_returns_progress():
    obj = _make_obj()
    batch = [{"box": (0, 0, 1, 1)}]
    out = obj._process_and_paste_batch(
        "out", batch, "p", "n", 20, 7.5, 0.3, 2, 9
    )
    assert out == 5
    obj._process_tile_batch.assert_called_once()
    obj._paste_tiles_into_output.assert_called_once()
