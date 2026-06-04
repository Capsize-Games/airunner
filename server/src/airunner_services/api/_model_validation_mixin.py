"""Model validation and loading mixin for legacy API handlers."""

import os
from typing import Any, Optional, Tuple

from airunner_services.api.legacy_server import get_api


class ModelValidationMixin:
    """Mixin providing model validation/loading for BaseHTTPRequestHandler."""

    def _validate_model_available(self) -> Tuple[bool, str, str]:
        """Check if the configured LLM model is available and downloaded.

        Returns:
            Tuple of (is_valid, model_path, error_message)
        """
        api = get_api()
        if not api:
            return False, "", "API not initialized"
        llm_settings = getattr(api, "llm_generator_settings", None)
        if not llm_settings:
            return False, "", "LLM settings not configured"
        model_path = getattr(llm_settings, "model_path", "") or ""
        model_name = getattr(llm_settings, "model_name", "") or ""
        if not model_path:
            return False, "", (
                "No model path configured. Please run 'airunner' (GUI) "
                "first to download and select a model."
            )
        if not os.path.exists(model_path):
            return False, model_path, (
                f"Model not found at '{model_path}'. "
                f"The model '{model_name}' needs to be downloaded. "
                "Please run 'airunner' (GUI) and download the model, "
                "or run 'airunner-setup' to download default models."
            )
        has_config = os.path.exists(
            os.path.join(model_path, "config.json"),
        )
        has_gguf = any(
            f.endswith(".gguf")
            for f in os.listdir(model_path)
            if os.path.isfile(os.path.join(model_path, f))
        )
        if not has_config and not has_gguf:
            return False, model_path, (
                f"Model at '{model_path}' appears incomplete "
                "(missing config.json or .gguf file). "
                "Please re-download the model using the AIRunner GUI "
                "or 'airunner-setup'."
            )
        return True, model_path, ""

    def _is_llm_model_loaded(self) -> bool:
        """Check if an LLM model is currently loaded."""
        api = get_api()
        if not api:
            return False
        return self._llm_loaded_from_balancer(
            api,
        ) or self._llm_loaded_from_worker(api)

    @staticmethod
    def _llm_loaded_from_balancer(api) -> bool:
        """Check if LLM is loaded via the model load balancer."""
        balancer = getattr(api, "model_load_balancer", None)
        if balancer is None:
            return False
        return bool(getattr(balancer, "llm_model", None))

    @staticmethod
    def _llm_loaded_from_worker(api) -> bool:
        """Check if LLM is loaded via the worker manager."""
        worker_manager = getattr(api, "worker_manager", None)
        if worker_manager is None:
            return False
        llm_worker = getattr(worker_manager, "llm_generate_worker", None)
        if llm_worker is None:
            return False
        llm = getattr(llm_worker, "llm", None)
        return llm is not None

    def _ensure_llm_model_loaded(self) -> Tuple[bool, str]:
        """Ensure the LLM model is loaded before processing a request."""
        from airunner_services.contract_enums import SignalCode

        if self._is_llm_model_loaded():
            return True, ""
        api = get_api()
        if not api:
            return False, "API not initialized"
        mediator = getattr(api, "signal_mediator", None)
        if mediator is not None:
            mediator.emit_signal(SignalCode.LLM_LOAD_SIGNAL, {})
        return True, ""

    def _is_art_model_loaded(self) -> bool:
        """Check if an art/SD model is currently loaded."""
        api = get_api()
        if not api:
            return False
        worker_manager = getattr(api, "worker_manager", None)
        if worker_manager is None:
            return False
        sd_worker = getattr(worker_manager, "sd_worker", None)
        if sd_worker is None:
            return False
        model_manager = getattr(sd_worker, "model_manager", None)
        if model_manager is None:
            return False
        return bool(getattr(model_manager, "active_model", None))

    def _art_model_status(self) -> str:
        """Return the current SD model status as a string."""
        try:
            from airunner_services.contract_enums import ModelStatus
        except ImportError:
            return "unknown"
        api = get_api()
        if not api:
            return "no_api"
        worker_manager = getattr(api, "worker_manager", None)
        if worker_manager is None:
            return "no_worker_manager"
        sd_worker = getattr(worker_manager, "sd_worker", None)
        if sd_worker is None:
            return "no_sd_worker"
        model_manager = getattr(sd_worker, "model_manager", None)
        if model_manager is None:
            return "no_model_manager"
        status = getattr(model_manager, "model_status", None)
        if status is None:
            return "no_status"
        if isinstance(status, ModelStatus):
            return status.value
        return str(status)

    def _ensure_art_model_loaded(
        self,
        model_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Ensure the art model is loaded before processing a request."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

        if self._is_art_model_loaded():
            return True, ""
        mediator = getattr(get_api(), "signal_mediator", None)
        if mediator is not None:
            payload: dict[str, Any] = {}
            if model_path:
                payload["model_path"] = model_path
            mediator.emit_signal(
                SignalCode.SD_LOAD_SIGNAL,
                payload,
            )
        return True, ""
