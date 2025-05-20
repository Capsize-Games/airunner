import time
from airunner.enums import (
    SignalCode,
)
from airunner.workers.worker import Worker
from airunner.data.models import Conversation


class LLMChatPromptWorker(Worker):
    def handle_message(self, message):
        """
        Expects message to be a dict with at least 'action': 'load_conversation', and optionally 'index'.
        Will emit a signal with the loaded conversation data (not widgets!)
        """
        action = message.get("action")
        if action == "load_conversation":
            t0 = time.time()
            index = message.get("index")
            conversation = None
            if index is not None:
                conversation = Conversation.objects.get(index)
            t1 = time.time()
            if conversation is None:
                conversation = Conversation.objects.order_by(
                    Conversation.id.desc()
                ).first()
            t2 = time.time()
            value = conversation.value if conversation is not None else []
            if value is None:
                value = []
            t3 = time.time()
            # Only process the most recent 50 messages for performance
            all_messages = value or []
            max_messages = 50
            if len(all_messages) > max_messages:
                all_messages = all_messages[-max_messages:]
            messages = [
                {
                    "name": (
                        message_obj.get("user_name", "User")
                        if message_obj.get("role") == "user"
                        else message_obj.get("bot_name", "Bot")
                    ),
                    "content": (
                        message_obj["blocks"][0]["text"]
                        if message_obj.get("blocks")
                        and message_obj["blocks"]
                        and "text" in message_obj["blocks"][0]
                        else ""
                    ),
                    "is_bot": message_obj.get("role") == "assistant",
                    "id": message_id,
                }
                for message_id, message_obj in enumerate(all_messages)
            ]
            t4 = time.time()
            self.logger.info(
                f"Conversation.objects.get: {t1-t0:.3f}s, order_by/first: {t2-t1:.3f}s, value access: {t3-t2:.3f}s, message build: {t4-t3:.3f}s"
            )
            # Emit a signal with the conversation and messages
            if conversation is not None:
                self.emit_signal(
                    SignalCode.LOAD_CONVERSATION,
                    {
                        "conversation_id": conversation.id,
                        "messages": messages,
                    },
                )
            else:
                self.emit_signal(
                    SignalCode.LOAD_CONVERSATION,
                    {"conversation_id": None, "messages": []},
                )
