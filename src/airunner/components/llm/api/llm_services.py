from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType
from airunner.components.llm.managers.llm_response import LLMResponse
from typing import Optional, List


class LLMAPIService(APIServiceBase):
    def __init__(self, emit_signal=None):
        super().__init__(emit_signal)
        self._emit_signal = emit_signal

    def emit_signal(self, code, data=None):
        if self._emit_signal:
            self._emit_signal(code, data)

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
    ):
        llm_request = llm_request or LLMRequest.from_default()
        llm_request.do_tts_reply = do_tts_reply
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
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
        )

    def map_search(self, query: str) -> None:
        """Send a map search request to the LLM generate worker.

        Args:
            query (str): The search query string from the map widget.
        """
        self.emit_signal(
            SignalCode.MAP_SEARCH_REQUEST_SIGNAL, {"query": query}
        )
