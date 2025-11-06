from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType
from airunner.components.llm.managers.llm_response import LLMResponse
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class LLMAPIService(APIServiceBase):
    """LLM API service providing signal-based LLM operations."""

    def __init__(self):
        super().__init__()

    def chatbot_changed(self):
        self.emit_signal(SignalCode.CHATBOT_CHANGED)

    def send_request(
        self,
        prompt,
        command: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        action: LLMActionType = LLMActionType.CHAT,
        do_tts_reply: bool = True,
        node_id: Optional[str] = None,
        request_id: Optional[str] = None,
        callback: Optional[callable] = None,
    ):
        """Send an LLM generation request.

        Args:
            prompt: The user's input text
            command: Optional command string
            llm_request: Optional LLM parameters
            action: The action type (CHAT, CODE, etc.)
            do_tts_reply: Whether to convert reply to speech
            node_id: Optional node identifier
            request_id: Optional unique request identifier for correlation
            callback: Optional callback function for responses
        """
        # Use action-optimized defaults if no explicit request provided
        llm_request = llm_request or LLMRequest.for_action(action)
        llm_request.do_tts_reply = do_tts_reply

        # DEBUG: Log max_new_tokens value
        logger.debug(
            f"llm_request.max_new_tokens={llm_request.max_new_tokens}, action={action}"
        )

        data = {
            "llm_request": True,
            "request_data": {
                "action": action,
                "prompt": prompt,
                "command": command,
                "llm_request": llm_request,
                "do_tts_reply": do_tts_reply,
            },
        }
        if node_id is not None:
            data["node_id"] = node_id

        if request_id is not None:
            data["request_id"] = request_id

            # Register pending request if callback provided
            if callback:
                from airunner.utils.application.signal_mediator import (
                    SignalMediator,
                )

                mediator = SignalMediator()
                mediator.register_pending_request(request_id, callback)

        self.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, data)

    def clear_history(self, **kwargs):
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, kwargs)

    def converation_deleted(self, conversation_id: int):
        self.emit_signal(
            SignalCode.CONVERSATION_DELETED,
            {"conversation_id": conversation_id},
        )

    def model_changed(self, model_service: str):
        self.update_llm_generator_settings(model_service=model_service)
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED, {"model_service": model_service}
        )

    def reload_rag(self, target_files: Optional[List[str]] = None):
        self.emit_signal(
            SignalCode.RAG_RELOAD_INDEX_SIGNAL,
            {"target_files": target_files} if target_files else None,
        )

    def load_conversation(self, conversation_id: int):
        self.emit_signal(
            SignalCode.QUEUE_LOAD_CONVERSATION,
            {"action": "load_conversation", "index": conversation_id},
        )

    def interrupt(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def delete_messages_after_id(self, message_id: int):
        self.emit_signal(
            SignalCode.DELETE_MESSAGES_AFTER_ID, {"message_id": message_id}
        )

    def finalize_image_generated_by_llm(self, _data):
        """
        Callback function to be called after the image has been generated.
        """
        # Ask the LLM to provide a brief confirmation in the current conversation style
        self.send_request(
            "The image request has completed. Write a single concise reply (1 short sentence) acknowledging the generated image.",
            action=LLMActionType.CHAT,
            do_tts_reply=True,
        )
        # self.send_llm_text_streamed_signal(
        #     LLMResponse(
        #         message="Your image has been generated successfully.",
        #         is_first_message=True,
        #         is_end_of_message=True,
        #     )
        # )

    def send_llm_text_streamed_signal(self, response: LLMResponse):
        # Include request_id at top level for SignalMediator correlation
        data = {"response": response}
        if response.request_id:
            data["request_id"] = response.request_id
        self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, data)
