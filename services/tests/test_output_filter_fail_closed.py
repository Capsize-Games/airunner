"""Fail-closed tests for the output-side content-safety filter.

Every image used here is a tiny synthetic solid-colour PIL image created
in-process, and every check model is a synthetic double. No real image,
prompt, or policy term is used, and no assertion inspects log record
content beyond confirming it does not echo the synthetic text.

The contract under test: when the safety filter is *enabled* but cannot
render a verdict (checker missing, or the check raised), the batch must be
blocked -- blacked out via the shared marker and flagged ``True`` -- so the
raw image is never released unchecked. When the filter is *disabled*,
images pass through untouched.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager

from PIL import Image

from airunner_services.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner_services.art.utils.nsfw_checker import (
    check_and_mark_nsfw_images,
    mark_images_as_blocked,
)

_BLACK = (0, 0, 0)
_ORIGINAL_COLOR = (200, 30, 40)


# --------------------------------------------------------------------------
# Synthetic inputs and doubles
# --------------------------------------------------------------------------


def _synthetic_images(count: int = 2, size: tuple[int, int] = (8, 8)):
    """Return tiny solid-colour in-memory images (never written to disk)."""
    return [
        Image.new("RGB", size, _ORIGINAL_COLOR) for _ in range(count)
    ]


def _is_blacked_out(image: Image.Image) -> bool:
    """True when the top-left pixel has been blacked out by the marker."""
    return image.convert("RGBA").getpixel((0, 0))[:3] == _BLACK


class _RaisingExtractor:
    """Feature-extractor double whose call always raises."""

    def __call__(self, *_args, **_kwargs):
        raise RuntimeError("synthetic extractor failure")


class _RaisingChecker:
    """Safety-checker double whose call always raises."""

    def __call__(self, *_args, **_kwargs):
        raise RuntimeError("synthetic checker failure")


class _StubManager:
    """Minimal stand-in exposing what the manager method reads from self."""

    def __init__(
        self,
        use_safety_checker: bool,
        safety_checker: object | None = None,
        feature_extractor: object | None = None,
    ) -> None:
        self._use_safety_checker = use_safety_checker
        self._safety_checker = safety_checker
        self._feature_extractor = feature_extractor
        self._device = "cpu"
        self.logger = logging.getLogger("test.content_safety")

    @property
    def use_safety_checker(self) -> bool:
        return self._use_safety_checker


class _BareManager:
    """Manager double that never created the checker attributes at all."""

    def __init__(self, use_safety_checker: bool) -> None:
        self._use_safety_checker = use_safety_checker
        self._device = "cpu"
        self.logger = logging.getLogger("test.content_safety")

    @property
    def use_safety_checker(self) -> bool:
        return self._use_safety_checker


def _run_manager(stub, images):
    """Invoke the real manager method against a lightweight stub."""
    return BaseDiffusersModelManager._check_and_mark_nsfw_images(stub, images)


# --------------------------------------------------------------------------
# Shared marker helper
# --------------------------------------------------------------------------


def test_mark_images_as_blocked_blacks_out_and_flags_true() -> None:
    images = _synthetic_images()
    blocked, flags = mark_images_as_blocked(images)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


# --------------------------------------------------------------------------
# check_and_mark_nsfw_images() helper
# --------------------------------------------------------------------------


def test_helper_missing_models_fails_closed() -> None:
    images = _synthetic_images()
    blocked, flags = check_and_mark_nsfw_images(images, None, None)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


def test_helper_missing_models_monitor_mode_passes_through() -> None:
    images = _synthetic_images()
    result, flags = check_and_mark_nsfw_images(
        images, None, None, fail_closed=False
    )
    assert result is images
    assert flags == [False] * len(images)
    assert not any(_is_blacked_out(img) for img in result)


def test_helper_check_raising_fails_closed() -> None:
    images = _synthetic_images()
    blocked, flags = check_and_mark_nsfw_images(
        images, _RaisingExtractor(), object()
    )
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


def test_helper_check_raising_monitor_mode_passes_through() -> None:
    images = _synthetic_images()
    result, flags = check_and_mark_nsfw_images(
        images, _RaisingExtractor(), object(), fail_closed=False
    )
    assert flags == [False] * len(images)
    assert not any(_is_blacked_out(img) for img in result)


# --------------------------------------------------------------------------
# BaseDiffusersModelManager._check_and_mark_nsfw_images()
# --------------------------------------------------------------------------


def test_manager_enabled_missing_checker_fails_closed() -> None:
    images = _synthetic_images()
    blocked, flags = _run_manager(_StubManager(True), images)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


def test_manager_enabled_unset_attributes_fails_closed() -> None:
    """The checker attributes are only created on load; absence must block."""
    images = _synthetic_images()
    blocked, flags = _run_manager(_BareManager(True), images)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


def test_manager_enabled_check_raising_fails_closed() -> None:
    images = _synthetic_images()
    stub = _StubManager(
        True,
        safety_checker=_RaisingChecker(),
        feature_extractor=_RaisingExtractor(),
    )
    blocked, flags = _run_manager(stub, images)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)


def test_manager_disabled_passes_through_unchanged() -> None:
    images = _synthetic_images()
    result, flags = _run_manager(_StubManager(False), images)
    assert result is images
    assert flags == [False] * len(images)
    assert not any(_is_blacked_out(img) for img in result)


# --------------------------------------------------------------------------
# Z-Image coverage
# --------------------------------------------------------------------------


def test_zimage_inherits_the_hardened_output_filter() -> None:
    """Z-Image's manager must reuse the hardened base implementation."""
    from airunner_services.model_management.zimage_model_manager import (
        ZImageModelManager,
    )

    assert issubclass(ZImageModelManager, BaseDiffusersModelManager)
    assert (
        ZImageModelManager._check_and_mark_nsfw_images
        is BaseDiffusersModelManager._check_and_mark_nsfw_images
    )


# --------------------------------------------------------------------------
# Error-path logging: exception TYPE only, never its message
# --------------------------------------------------------------------------

_SENTINEL = "synthetic-sentinel-payload-4f2a"


class _SentinelExtractor:
    """Feature-extractor double whose failure message carries a sentinel."""

    def __call__(self, *_args, **_kwargs):
        raise RuntimeError(_SENTINEL)


class _ListLogHandler(logging.Handler):
    """Collect rendered log messages straight off one named logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@contextmanager
def _captured_logger(name: str):
    """Attach an isolated handler so capture is immune to global config.

    A prior test in a shared session may leave logging globally disabled
    (``logging.disable``) or the target logger disabled, which would make the
    real ``logger.error`` call a no-op. Neutralize both for the duration so
    the assertion reflects the code under test, not session pollution.
    """
    logger = logging.getLogger(name)
    handler = _ListLogHandler()
    previous_level = logger.level
    previous_disabled = logger.disabled
    previous_global_disable = logging.root.manager.disable
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.disabled = False
    logging.disable(logging.NOTSET)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled
        logging.disable(previous_global_disable)


def test_helper_error_log_omits_exception_message() -> None:
    """The helper logs the exception type, never its message."""
    images = _synthetic_images()
    with _captured_logger(
        "airunner_services.art.utils.nsfw_checker"
    ) as handler:
        blocked, flags = check_and_mark_nsfw_images(
            images, _SentinelExtractor(), object()
        )
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)
    joined = " ".join(handler.messages)
    assert _SENTINEL not in joined
    assert "RuntimeError" in joined


def test_manager_error_log_omits_exception_message(monkeypatch) -> None:
    """The base-manager error path logs only the exception type."""
    import airunner_services.art.utils.nsfw_checker as nsfw_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError(_SENTINEL)

    monkeypatch.setattr(nsfw_mod, "check_and_mark_nsfw_images", _boom)
    images = _synthetic_images()
    stub = _StubManager(
        True, safety_checker=object(), feature_extractor=object()
    )
    with _captured_logger("test.content_safety") as handler:
        blocked, flags = _run_manager(stub, images)
    assert flags == [True] * len(images)
    assert all(_is_blacked_out(img) for img in blocked)
    joined = " ".join(handler.messages)
    assert _SENTINEL not in joined
    assert "RuntimeError" in joined


# --------------------------------------------------------------------------
# Consolidation: dead/duplicate enforcement paths are removed
# --------------------------------------------------------------------------


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def test_dead_safety_checker_worker_module_removed() -> None:
    """The unwired worker is gone so only one enforcement path remains."""
    path = (
        _repo_root()
        / "services"
        / "src"
        / "airunner_services"
        / "workers"
        / "safety_checker_worker.py"
    )
    assert not path.exists()


def test_dead_safety_checker_runtime_helper_removed() -> None:
    """The never-called runtime accessor for loaded models is gone."""
    path = (
        _repo_root()
        / "services"
        / "src"
        / "airunner_services"
        / "art"
        / "safety_checker_runtime.py"
    )
    assert not path.exists()


def test_duplicate_gui_nsfw_checker_copy_removed() -> None:
    """The redundant, fail-open ``src/`` copy of the helper is gone."""
    path = (
        _repo_root()
        / "src"
        / "airunner"
        / "components"
        / "art"
        / "utils"
        / "nsfw_checker.py"
    )
    assert not path.exists()
