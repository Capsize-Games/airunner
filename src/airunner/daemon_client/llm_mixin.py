"""LLM endpoints for the GUI daemon client."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType


class LLMClientMixin:
    """LLM-related daemon API endpoints."""

    # Provided by _DaemonClientBase — declared here for type checkers.
    base_url: str
    _request: Any
    logger: Any

    def interrupt_llm(self) -> Dict[str, Any]:
        """Interrupt the active daemon-side LLM request."""
        response = self._request(
            "POST",
            "/api/v1/daemon/runtimes/llm/cancel",
            json_payload={
                "provider": "local",
                "deployment_mode": "default",
            },
        )
        return response.json()

    def unload_local_llm(
        self, *, timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Unload the daemon's local LLM runtime."""
        response = self._request(
            "POST",
            "/api/v1/daemon/runtimes/llm/unload",
            json_payload={
                "provider": "local",
                "deployment_mode": "default",
            },
            timeout_seconds=timeout_seconds,
        )
        return response.json()

    def start_rag_document_index(
        self,
        *,
        file_paths: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Trigger daemon-backed document indexing."""
        response = self._request(
            "POST",
            "/api/v1/llm/rag/index",
            json_payload={"file_paths": file_paths},
        )
        return response.json()

    def cancel_rag_document_index(self) -> Dict[str, Any]:
        """Request cancellation for the daemon-backed indexing flow."""
        response = self._request(
            "POST",
            "/api/v1/llm/rag/index/cancel",
        )
        return response.json()

    def rag_document_index_status(self) -> Dict[str, Any]:
        """Return the current daemon-backed indexing status payload."""
        response = self._request(
            "GET",
            "/api/v1/llm/rag/index/status",
        )
        return response.json()

    def stream_llm_request(
        self,
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        request_id: str,
        *,
        search_hints: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[int] = None,
        node_id: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        """Yield NDJSON chunks from the daemon's legacy LLM endpoint."""
        headers = {"x-request-id": request_id}
        with self._request(
            "POST",
            "/llm/generate",
            json_payload=self._llm_payload(
                prompt,
                llm_request,
                action,
                search_hints=search_hints,
                conversation_id=conversation_id,
                node_id=node_id,
            ),
            headers=headers,
            stream=True,
        ) as response:
            for line in response.iter_lines(chunk_size=1):
                if not line:
                    continue
                yield json.loads(line.decode("utf-8"))

    # ------------------------------------------------------------------
    # Internal LLM helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _llm_payload(
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        *,
        search_hints: Optional[Dict[str, Any]],
        conversation_id: Optional[int],
        node_id: Optional[str],
    ) -> Dict[str, Any]:
        """Build the legacy daemon payload from an LLM request object."""
        payload = {
            "prompt": prompt,
            "action": action.name,
            "stream": True,
        }
        payload.update(
            LLMClientMixin._llm_request_fields(llm_request)
        )
        if search_hints is not None:
            payload["search_hints"] = search_hints
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id
        if node_id is not None:
            payload["node_id"] = node_id
        return payload

    @staticmethod
    def _llm_request_fields(
        llm_request: LLMRequest,
    ) -> Dict[str, Any]:
        """Return JSON-safe fields that the daemon legacy route
        understands."""
        payload = llm_request.to_dict()
        extra_fields = {
            "model_service": llm_request.model_service,
            "api_model": llm_request.api_model,
            "dtype": llm_request.dtype,
            "use_memory": llm_request.use_memory,
            "tool_categories": llm_request.tool_categories,
            "system_prompt": llm_request.system_prompt,
            "response_format": llm_request.response_format,
            "rag_files": llm_request.rag_files,
            "ephemeral_conversation": llm_request.ephemeral_conversation,
            "enable_thinking": llm_request.enable_thinking,
            "model": llm_request.model,
            "force_tool": llm_request.force_tool,
            "include_mood": llm_request.include_mood,
            "include_datetime": llm_request.include_datetime,
            "include_style": llm_request.include_style,
            "include_memory": llm_request.include_memory,
            "include_ui_context": llm_request.include_ui_context,
        }
        for key, value in extra_fields.items():
            if value is not None:
                payload[key] = value
        return payload
