"""Text generation functionality for LLM models."""

from typing import Any, Dict, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.managers.mixins.generation_execution_support import (
    do_generate,
)
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.llm.managers.mixins.generation_signal_support import (
    send_end_of_message,
)


class GenerationMixin:
    """Mixin for LLM text generation functionality."""

    def _do_generate(
        self,
        prompt: str,
        action: LLMActionType,
        system_prompt: Optional[str] = None,
        llm_request: Optional[Any] = None,
        do_tts_reply: bool = True,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
        skip_tool_setup: bool = False,
    ) -> Dict[str, Any]:
        """Generate a response using the loaded LLM.

        Args:
            prompt: The input prompt
            action: The LLM action type
            system_prompt: Optional system prompt override
            llm_request: Optional LLM request object
            do_tts_reply: Whether to enable TTS reply
            extra_context: Optional extra context dictionary
            skip_tool_setup: If True, skip tool setup (already filtered)

        Returns:
            Dictionary with 'response' key containing generated text
        """
        return do_generate(
            self,
            prompt,
            action,
            system_prompt,
            llm_request,
            do_tts_reply,
            extra_context,
            skip_tool_setup,
        )

    def _send_final_message(
        self, llm_request: Optional[LLMRequest] = None
    ) -> None:
        """Send a signal indicating the end of a message stream.

        Args:
            llm_request: Optional LLM request object
        """
        executed_tools = []
        if hasattr(self, "_workflow_manager") and self._workflow_manager:
            executed_tools = self._workflow_manager.get_executed_tools()
        send_end_of_message(
            self,
            llm_request,
            [0],
            list(executed_tools or []),
            None,
            None,
            None,
        )

