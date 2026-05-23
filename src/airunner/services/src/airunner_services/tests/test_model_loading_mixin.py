"""Tests for service-owned model auto-swap unload behavior."""

from airunner_services.contract_enums import SignalCode
from airunner_services.model_management.mixins.model_loading_mixin import (
    ModelLoadingMixin,
)


class _LoggerStub:
    """Capture minimal logging calls for the model-loading test double."""

    def info(self, *_args, **_kwargs) -> None:
        """Accept info logs without side effects."""

    def error(self, *_args, **_kwargs) -> None:
        """Accept error logs without side effects."""


class _SignalMediatorStub:
    """Record emitted signals for assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[SignalCode, dict]] = []

    def emit(self, signal_code: SignalCode, data: dict) -> None:
        """Record one emitted signal payload."""
        self.calls.append((signal_code, data))


class _ModelLoaderDouble(ModelLoadingMixin):
    """Provide only the collaborators needed by request_model_swap."""

    def __init__(self, model_type: str) -> None:
        self.logger = _LoggerStub()
        self.signal_mediator = _SignalMediatorStub()
        self._model_types = {"loaded-model": model_type}

    def _determine_models_to_unload(self, *_args, **_kwargs) -> list[str]:
        """Return one loaded model so the unload path is exercised."""
        return ["loaded-model"]


def test_model_swap_unloads_text_to_image_via_service_signal() -> None:
    """Text-to-image auto-swap should not depend on the service API."""
    loader = _ModelLoaderDouble("text_to_image")

    result = loader.request_model_swap("next-model", "llm")

    assert result["success"] is True
    assert result["unloaded_models"] == ["loaded-model"]
    assert loader.signal_mediator.calls == [
        (SignalCode.SD_UNLOAD_SIGNAL, {}),
    ]