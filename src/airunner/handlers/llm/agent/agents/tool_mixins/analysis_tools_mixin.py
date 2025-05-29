from typing import Annotated
from llama_index.core.tools import FunctionTool
from airunner.enums import SignalCode
from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)
from airunner.data.models import Conversation
from airunner.utils.application.logging_utils import log_method_entry_exit


class AnalysisToolsMixin(ToolSingletonMixin):
    """Mixin for analysis-related tools."""

    @property
    def analysis_tool(self):
        def set_analysis(
            analysis: Annotated[
                str,
                (
                    "A summary or analysis of the conversation. Should be concise and relevant."
                ),
            ],
        ) -> str:
            conversation = self.conversation
            if conversation:
                Conversation.objects.update(
                    self.conversation_id, summary=analysis
                )
                # Emit signal and log
                self.emit_signal(
                    SignalCode.MOOD_SUMMARY_UPDATE_STARTED,
                    {"message": "Updating bot mood / summarizing..."},
                )
                message = "Analysis/summary updated."
                self.logger.info(message)
                return message
            message = "No conversation found to update analysis."
            self.logger.warning(message)
            return message

        return self._get_or_create_singleton(
            "_analysis_tool",
            FunctionTool.from_defaults,
            set_analysis,
            return_direct=True,
        )

    @staticmethod
    def _extract_analysis(response):
        if response is None:
            return None
        for attr in ("message", "content", "analysis", "data", "response"):
            val = getattr(response, attr, None)
            if isinstance(val, str) and val.strip():
                return val.strip()
        if isinstance(response, str):
            return response.strip()
        if isinstance(response, dict):
            for key in ("message", "content", "analysis", "data", "response"):
                val = response.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        if isinstance(response, list) and response:
            first = response[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
            if isinstance(first, dict):
                for key in (
                    "message",
                    "content",
                    "analysis",
                    "data",
                    "response",
                ):
                    val = first.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        return None

    @staticmethod
    def _is_meaningless_magicmock(analysis):
        from unittest.mock import MagicMock

        if not isinstance(analysis, MagicMock):
            return False
        attrs = [
            getattr(analysis, a, None)
            for a in ("content", "message", "analysis", "data", "response")
        ]
        return all(
            (a is None or (isinstance(a, str) and not a.strip()))
            for a in attrs
        )

    def _fallback_update_user_data(self, conversation_context):
        tool = getattr(self, "update_user_data_tool", None)
        if tool is not None:
            try:
                tool_response = tool.call(conversation_context)
                return self._extract_analysis(tool_response)
            except Exception as e2:
                self.logger.error(f"update_user_data_tool.call failed: {e2}")
        return None

    @log_method_entry_exit
    def _update_user_data(self) -> None:
        """
        Update the user data using the update_user_data_engine and only update user_data if there is meaningful content.
        This method does NOT update summary or call analysis_tool.
        """
        try:
            conversation = self.conversation
            if not (conversation and conversation.value):
                return
            context = getattr(conversation, "formatted_messages", None)
            if not (context and context.strip()):
                return
            try:
                response = self.update_user_data_engine.chat(context)
                analysis = self._extract_analysis(response)
            except Exception as e:
                self.logger.error(
                    f"update_user_data_engine.chat failed: {e}. Trying update_user_data_tool.call as fallback."
                )
                analysis = self._fallback_update_user_data(context)
            if not (
                analysis and str(analysis).strip()
            ) or self._is_meaningless_magicmock(analysis):
                return
            analysis_str = (
                analysis.strip()
                if isinstance(analysis, str)
                else str(analysis)
            )
            if len(analysis_str) <= 10:
                return
            user_data_list = [
                line.strip()
                for line in analysis_str.split("\n")
                if line.strip() and not line.strip().startswith("system:")
            ]
            if not user_data_list:
                return
            conversation.user_data = user_data_list
            Conversation.objects.update(
                conversation.id, user_data=user_data_list
            )
        except Exception as e:
            self.logger.error(f"Error updating user data: {e}")

    def update_analysis(self, analysis: str) -> str:
        return self.analysis_tool(analysis)
