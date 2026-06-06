from airunner_services.api.services.llm_services import (
    LLMAPIService as ServiceLLMAPIService,
)
from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)


class LLMAPIService(ServiceLLMAPIService):
    """GUI bridge subclass for the canonical service-owned LLM API."""

    def _forward_tts_stream_signal(self, data: dict) -> bool:
        """Forward one streamed LLM chunk directly to the GUI TTS worker."""
        worker = self._tts_stream_worker()
        handler = getattr(worker, "on_llm_text_streamed_signal", None)
        if not callable(handler):
            return False
        handler(dict(data))
        return True

    def _forward_tts_thinking_signal(self, data: dict) -> bool:
        """Forward one thinking update directly to the GUI TTS worker."""
        worker = self._tts_stream_worker()
        handler = getattr(worker, "on_llm_thinking_signal", None)
        if not callable(handler):
            return False
        handler(dict(data))
        return True

    def _tts_stream_worker(self):
        """Return the live GUI TTS worker when one exists."""
        worker_manager = self._worker_manager()
        if worker_manager is None:
            return None
        resolver = getattr(worker_manager, "_stream_tts_worker", None)
        if callable(resolver):
            return resolver()
        return getattr(worker_manager, "tts_generator_worker", None)

    def _worker_manager(self):
        """Return the GUI worker manager when one is available."""
        resolved_api = LLMAPIService._resolve_api_instance()
        for candidate in (
            getattr(getattr(self, "api", None), "main_window", None),
            getattr(
                getattr(getattr(self, "api", None), "app", None),
                "main_window",
                None,
            ),
            getattr(resolved_api, "main_window", None),
        ):
            if candidate is None:
                continue
            worker_manager = getattr(candidate, "worker_manager", None)
            if worker_manager is not None:
                return worker_manager
        return None

    def _daemon_client(self):
        """Return the daemon client when one is available."""
        api = peek_registered_api()
        return getattr(api, "daemon_client", None) if api else None

    @staticmethod
    def _resolve_api_instance():
        """Resolve the registered App/API object when service init ran early."""
        return peek_registered_api()
