from typing import Any, Optional

from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.tools.types import ToolOutput
from transformers import AutoModelForCausalLM, AutoTokenizer

from airunner.enums import LLMActionType
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


class LocalAgent(BaseAgent):
    action_map = {
        1: LLMActionType.CHAT,
        2: LLMActionType.SEARCH,
        3: LLMActionType.GENERATE_IMAGE,
        4: LLMActionType.PERFORM_RAG_SEARCH,
        5: LLMActionType.APPLICATION_COMMAND,
    }

    def __init__(
        self,
        model: Optional[AutoModelForCausalLM] = None,
        tokenizer: Optional[AutoTokenizer] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.model = model
        self.tokenizer = tokenizer
        self.decision_mode: bool = True

    @property
    def system_prompt(self) -> str:
        """
        Return the system prompt for the agent. If decision_mode is enabled, return a prompt instructing the LLM to select the best tool by number for the user's request. Otherwise, use the base class system_prompt.

        Returns:
            str: The system prompt.
        """
        menu_choices = {
            1: "Respond to the user conversationally: Choose thise when uou have all the context you need to respond to the user's request in a conversational manner.",
            2: "Browse the internet: Choose this when you want to get more information from the web to better respond to the user's request.",
            3: "Generate image: Use this if the user is asking for an image or visual content.",
            4: "Use documents: Choose this when you want to search through documents or files to find relevant information to respond to the user's request.",
            5: "Not sure what to do: Reason about the user's request and choose from a list of available tools in order to fulfill the request.",
        }
        if self.decision_mode:
            menu_text = "\n".join(
                f"{i}. {desc}" for i, desc in menu_choices.items()
            )
            return (
                "You are an expert AI assistant. Your task is to analyze the user's request and, using only logic and context from the chat history, select the single best tool from a numbered menu to fulfill the request. "
                "Ignore mood and personality. Respond ONLY with the number of the tool that is the best choice.\n"
                "Here is the list of tools available:\n" + menu_text
            )
        return super().system_prompt

    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        decision_mode: Optional[bool] = None,
        extra_context: Optional[dict[str, dict]] = None,
    ) -> AgentChatResponse:
        if extra_context:
            for k, v in extra_context.items():
                self.context_manager.set_context(k, v)
        decision_mode = (
            decision_mode if decision_mode is not None else self.decision_mode
        )
        if not decision_mode:
            self.interrupt = False
            return super().chat(
                message=message,
                action=action,
                system_prompt=system_prompt,
                rag_system_prompt=rag_system_prompt,
                llm_request=llm_request,
                extra_context=extra_context,
            )
        # In decision mode, call super().chat() with action=LLMActionType.DECISION
        return super().chat(
            message=message,
            action=LLMActionType.DECISION,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request,
            extra_context=extra_context,
        )

    def handle_response(
        self,
        response: str,
        is_first_message: bool = False,
        is_last_message: bool = False,
        do_not_display: bool = False,
        do_tts_reply: bool = True,
        decision_mode: Optional[bool] = None,
    ) -> None:
        decision_mode = (
            decision_mode if decision_mode is not None else self.decision_mode
        )
        if not decision_mode:
            super().handle_response(
                response=response,
                is_first_message=is_first_message,
                is_last_message=is_last_message,
                do_not_display=do_not_display,
                do_tts_reply=do_tts_reply,
            )
            return
        self._complete_response += response
        selection = self._parse_menu_selection(self._complete_response)
        if selection is not None or is_last_message:
            if selection is None:
                selection = list(self.action_map.keys())[
                    0
                ]  # Default to first action
            action = self.action_map.get(selection)
            if not is_last_message:
                self.interrupt = True
            self._complete_response = ""
            # --- Fix infinite loop: temporarily disable decision_mode ---
            prev_decision_mode = self.decision_mode
            self.decision_mode = False
            # Call super().chat() with the selected action
            super().chat(
                message=self._chat_prompt,
                action=action,
                system_prompt=None,
                rag_system_prompt=None,
                llm_request=self.llm_request,
                extra_context=None,
            )
            self.decision_mode = prev_decision_mode
            return

    def _parse_menu_selection(self, text: str) -> Optional[int]:
        import re

        match = re.match(r"\s*(\d+)[\.|\s]", text)
        if match:
            return int(match.group(1))
        match = re.match(r"\s*(\d+)", text)
        if match:
            return int(match.group(1))
        return None
