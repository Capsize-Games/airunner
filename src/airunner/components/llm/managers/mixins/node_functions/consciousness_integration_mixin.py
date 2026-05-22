"""Shared consciousness hook helpers for workflow mixins."""

from dataclasses import dataclass
from typing import Any, List, Optional


class ConsciousnessIntegrationMixin:
    """Provide best-effort access to the optional consciousness extension."""

    @dataclass
    class _ConsciousnessCtx:
        conversation_id: Optional[int]
        thread_id: Any
        messages: Optional[List[Any]]

    def _get_consciousness_engine(self):
        """Best-effort loader for the optional consciousness extension."""
        try:
            from airunner_extensions.consciousness import get_engine

            return get_engine()
        except Exception:
            return None

    @staticmethod
    def _is_consciousness_enabled(value: Any) -> bool:
        """Normalize the per-request consciousness flag."""
        if value is None:
            return True
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }
        return bool(value)

    def _consciousness_enabled_for_request(self) -> bool:
        """Return whether consciousness hooks should run for this request."""
        try:
            data = getattr(self, "data", None) or {}
            return self._is_consciousness_enabled(
                data.get("enable_consciousness", None)
            )
        except Exception:
            return True

    def _build_consciousness_context(
        self,
        messages: Optional[List[Any]],
    ) -> _ConsciousnessCtx:
        """Build one shared context object for consciousness hooks."""
        return self._ConsciousnessCtx(
            conversation_id=getattr(self, "_conversation_id", None),
            thread_id=getattr(self, "_thread_id", "default"),
            messages=messages,
        )

    def _run_consciousness_hook(
        self,
        hook_name: str,
        *hook_args: Any,
        messages: Optional[List[Any]] = None,
    ) -> None:
        """Call one optional consciousness hook without affecting execution."""
        if not self._consciousness_enabled_for_request():
            return

        engine = self._get_consciousness_engine()
        if not engine:
            return

        hook = getattr(engine, hook_name, None)
        if not callable(hook):
            return

        try:
            hook(*hook_args, self._build_consciousness_context(messages))
        except Exception:
            return