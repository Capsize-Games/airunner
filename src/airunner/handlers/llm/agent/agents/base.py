import re
from typing import (
    Any,
    Optional,
    Union,
    Dict,
    Type,
)
import datetime
import platform
import json
from unittest.mock import MagicMock

from llama_index.core.tools import BaseTool
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.llms.llm import LLM
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.base.llms.types import TextBlock

from airunner.enums import (
    LANGUAGE_DISPLAY_MAP,
    AvailableLanguage,
    LLMActionType,
    SignalCode,
)
from airunner.data.models import Conversation, User, Tab
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent import (
    RAGMixin,
    ExternalConditionStoppingCriteria,
)
from airunner.handlers.llm.agent.tools import ChatEngineTool, ReActAgentTool
from airunner.handlers.llm.agent.chat_engine import RefreshSimpleChatEngine
from airunner.handlers.llm.agent import WeatherMixin
from airunner.handlers.llm.storage.chat_store import DatabaseChatStore
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.llm.llm_settings import LLMSettings
from airunner.data.models import Conversation
from airunner.settings import (
    AIRUNNER_ART_ENABLED,
    AIRUNNER_MOOD_PROMPT_OVERRIDE,
)
from airunner.utils.llm.language import detect_language
from airunner.handlers.llm.agent.agents.registry import (
    ToolRegistry,
    EngineRegistry,
)
from .tool_mixins import (
    ImageToolsMixin,
    ConversationToolsMixin,
    SystemToolsMixin,
    UserToolsMixin,
    MemoryManagerMixin,
    ConversationManagerMixin,
    UserManagerMixin,
    LLMManagerMixin,
    MoodToolsMixin,
    AnalysisToolsMixin,
)
from .prompt_config import PromptConfig
from airunner.utils.application.logging_utils import log_method_entry_exit


class BaseAgent(
    MediatorMixin,
    SettingsMixin,
    RAGMixin,
    WeatherMixin,
    ImageToolsMixin,
    ConversationToolsMixin,
    SystemToolsMixin,
    UserToolsMixin,
    LLMManagerMixin,
    MemoryManagerMixin,
    ConversationManagerMixin,
    UserManagerMixin,
    MoodToolsMixin,
    AnalysisToolsMixin,
):
    """
    Base class for all agents.

    Args:
        default_tool_choice (Optional[Union[str, dict]]): The default tool choice.
        llm_settings (LLMSettings): The LLM settings.
        use_memory (bool): Whether to use memory.
    """

    def __init__(
        self,
        default_tool_choice: Optional[Union[str, dict]] = None,
        llm_settings: LLMSettings = LLMSettings(),
        use_memory: bool = True,
        chat_engine: Optional[Any] = None,
        mood_engine: Optional[Any] = None,
        summary_engine: Optional[Any] = None,
        chat_engine_tool: Optional[Any] = None,
        mood_engine_tool: Optional[Any] = None,
        update_user_data_engine: Optional[Any] = None,
        update_user_data_tool: Optional[Any] = None,
        summary_engine_tool: Optional[Any] = None,
        information_scraper_tool: Optional[Any] = None,
        information_scraper_engine: Optional[Any] = None,
        react_tool_agent: Optional[Any] = None,
        store_user_tool: Optional[Any] = None,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        conversation_strategy: Optional[Any] = None,
        memory_strategy: Optional[Any] = None,
        llm_strategy: Optional[Any] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the BaseAgent.
        """
        self.default_tool_choice: Optional[Union[str, dict]] = (
            default_tool_choice
        )
        self._prompt = None
        self._language = None
        self._llm_request: Optional[LLMRequest] = None
        self.llm_settings: LLMSettings = llm_settings
        self._use_memory: bool = use_memory
        self._action: LLMActionType = LLMActionType.NONE
        self._chat_prompt: str = ""
        self._current_tab: Optional[Tab] = None
        self._streaming_stopping_criteria: Optional[
            ExternalConditionStoppingCriteria
        ] = None
        self._do_interrupt: bool = False
        self._llm: Optional[LLM] = None
        self._conversation: Optional[Conversation] = None
        self._conversation_id: Optional[int] = None
        self._user: Optional[User] = None
        self._chat_engine: Optional[Any] = chat_engine
        self._mood_engine: Optional[Any] = mood_engine
        self._summary_engine: Optional[Any] = summary_engine
        self._chat_engine_tool: Optional[Any] = chat_engine_tool
        self._mood_engine_tool: Optional[Any] = mood_engine_tool
        self._update_user_data_engine = update_user_data_engine
        self._update_user_data_tool = update_user_data_tool
        self._summary_engine_tool: Optional[Any] = summary_engine_tool
        self._information_scraper_tool: Optional[Any] = (
            information_scraper_tool
        )
        self._information_scraper_engine: Optional[Any] = (
            information_scraper_engine
        )
        self._memory: Optional[BaseMemory] = None
        self._react_tool_agent: Optional[Any] = react_tool_agent
        self._complete_response: str = ""
        self._store_user_tool: Optional[Any] = store_user_tool
        self._webpage_html: str = ""
        self.model: Optional[Any] = model
        self.tokenizer: Optional[Any] = tokenizer
        self._conversation_strategy = conversation_strategy
        self._memory_strategy = memory_strategy
        self._llm_strategy = llm_strategy

        self.signal_handlers.update(
            {
                SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id
            }
        )
        super().__init__(*args, **kwargs)

    @property
    def prompt(self) -> Optional[str]:
        """
        Get the current prompt string.
        Returns:
            Optional[str]: The current prompt.
        """
        return self._prompt

    @prompt.setter
    def prompt(self, value: str) -> None:
        """
        Set the current prompt string.
        Args:
            value (str): The prompt to set.
        """
        self._prompt = value

    @property
    def language(self) -> str:
        """
        Get the language for the agent.
        Returns:
            str: The language display name.
        """
        try:
            bot_lang = AvailableLanguage(self.language_settings.bot_language)
        except ValueError:
            bot_lang = AvailableLanguage.EN
        if bot_lang is AvailableLanguage.AUTO:
            bot_lang = detect_language(self.prompt)
        return LANGUAGE_DISPLAY_MAP.get(bot_lang)

    @language.setter
    def language(self, value: str) -> None:
        """
        Set the language for the agent.
        Args:
            value (str): The language to set.
        """
        self._language = value

    @property
    def use_memory(self) -> bool:
        """
        Whether the agent should use memory.
        Returns:
            bool: True if memory is used, False otherwise.
        """
        use_memory = self._use_memory
        if (
            self.llm
            and self.llm_request
            and self.llm_request.use_memory is False
        ):  # override with llm_request
            use_memory = False
        return use_memory

    @property
    def action(self) -> LLMActionType:
        """
        Get the current LLM action type.
        Returns:
            LLMActionType: The current action.
        """
        return self._action

    @action.setter
    def action(self, value: LLMActionType) -> None:
        """
        Set the current LLM action type.
        Args:
            value (LLMActionType): The action to set.
        """
        self._action = value

    @property
    def chat_mode_enabled(self) -> bool:
        """
        Whether chat mode is enabled.
        Returns:
            bool: True if chat mode is enabled.
        """
        return self.action is LLMActionType.CHAT

    @property
    def rag_enabled(self) -> bool:
        """
        Whether RAG is enabled.
        Returns:
            bool: True if RAG is enabled.
        """
        return self.rag_settings.enabled

    @property
    def rag_mode_enabled(self) -> bool:
        """
        Whether RAG mode is enabled for the current action.
        Returns:
            bool: True if RAG mode is enabled.
        """
        return (
            self.rag_enabled
            and self.action is LLMActionType.PERFORM_RAG_SEARCH
        )

    @property
    def date_time_prompt(self) -> str:
        """
        Get the date/time prompt string.
        Returns:
            str: The date/time prompt.
        """
        return (
            (
                "Current Date / time information:\n"
                f"- The current date: {self.current_date} (Keep in mind any "
                "holidays or special events that might be taking place on this day).\n"
                f"- The current time: {self.current_time}.\n"
                f"- The user's timezone: {self.timezone}.\n"
            )
            if self.chatbot.use_datetime
            else ""
        )

    @property
    def personality_prompt(self) -> str:
        """
        Get the personality prompt string.
        Returns:
            str: The personality prompt.
        """
        return (
            f"{self.botname}'s personality: {self.chatbot.bot_personality}\n"
            if self.chatbot.use_personality
            else ""
        )

    @property
    def mood_prompt(self) -> str:
        """
        Get the mood prompt string.
        Returns:
            str: The mood prompt.
        """
        return (
            AIRUNNER_MOOD_PROMPT_OVERRIDE
            or (
                "You are a living being, one that has feelings, emotions, a personality with needs and desires.\n"
                f"{self.botname}'s current mood: {self.bot_mood}\n"
            )
            if self.chatbot.use_mood
            else ""
        )

    @property
    def operating_system_prompt(self) -> str:
        """
        Get the operating system prompt string.
        Returns:
            str: The OS prompt.
        """
        return (
            "Operating system information:\n"
            f"- System: {platform.system()}\n"
            f"- Release: {platform.release()}\n"
            f"- Version: {platform.version()}\n"
            f"- Machine: {platform.machine()}\n"
            f"- Processor: {platform.processor()}\n"
        )

    @property
    def speakers_prompt(self) -> str:
        """
        Get the speakers prompt string.
        Returns:
            str: The speakers prompt.
        """
        metadata_prompt = None
        if self.conversation:
            data = self.conversation.user_data or []
            if data is not None:
                metadata_prompt = ""
                for item in data:
                    metadata_prompt += f"-- {item}\n"
            if metadata_prompt:
                metadata_prompt = f"- Metadata:\n{metadata_prompt}"
        metadata_prompt = metadata_prompt or ""
        return (
            "User information:\n"
            f"- Username: {self.username}\n"
            f"- Location: {self.location_display_name}\n"
            f"{metadata_prompt}"
            "Chatbot information:\n"
            f"- Chatbot name: {self.botname}\n"
            f"- Chatbot mood: {self.bot_mood}\n"
            f"- Chatbot personality: {self.bot_personality}\n"
        )

    @log_method_entry_exit
    def unload(self) -> None:
        """
        Unload the chat agent and its resources.
        """
        self.logger.debug("Unloading chat agent")
        if self._llm:
            self._llm.unload()
        self.unload_rag()

        del self._chat_engine
        del self._chat_engine_tool
        del self._react_tool_agent

        del self.model
        del self.tokenizer
        del self._llm

        self.model = None
        self.tokenizer = None
        self._llm = None

        self._chat_engine = None
        self._chat_engine_tool = None
        self._react_tool_agent = None

    @property
    def webpage_html(self) -> str:
        """
        Get the webpage HTML content.
        Returns:
            str: The webpage HTML content.
        """
        return self._webpage_html

    @webpage_html.setter
    def webpage_html(self, value: str) -> None:
        """
        Set the webpage HTML content.
        Args:
            value (str): The HTML content to set.
        """
        self._webpage_html = value

    @property
    def current_tab(self) -> Optional[Tab]:
        """
        Get the current active tab.
        Returns:
            Optional[Tab]: The current active tab.
        """
        if not self._current_tab:
            self._current_tab = Tab.objects.filter_by_first(
                section="center", active=True
            )
        return self._current_tab

    @current_tab.setter
    def current_tab(self, value: Optional[Tab]) -> None:
        """
        Set the current active tab.
        Args:
            value (Optional[Tab]): The tab to set as current.
        """
        self._current_tab = value

    def _get_or_create_singleton(
        self, attr_name: str, factory: Type, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Get or create a singleton instance for the given attribute.
        If the attribute was injected (not None), use it as-is.
        Otherwise, create it using the factory.
        """
        if hasattr(self, attr_name) and getattr(self, attr_name) is not None:
            return getattr(self, attr_name)
        setattr(self, attr_name, factory(*args, **kwargs))
        return getattr(self, attr_name)

    @property
    def tools(self) -> list:
        """
        Returns a list of tools for the agent. Tools can be registered dynamically via ToolRegistry.register('name').
        To add a new tool, decorate it with @ToolRegistry.register('tool_name') and ensure it is imported.
        Returns:
            list: The list of tools.
        """
        tools = [
            self.chat_engine_react_tool,
            self.quit_application_tool,
            self.clear_conversation_tool,
            self.toggle_text_to_speech_tool,
            self.list_files_in_directory_tool,
            self.open_image_from_path_tool,
        ]
        if AIRUNNER_ART_ENABLED:
            tools.extend(
                [
                    self.generate_image_tool,
                    self.clear_canvas_tool,
                    self.set_working_width_and_height,
                ]
            )
        if self.chat_mode_enabled:
            tools.extend(
                [
                    self.information_scraper_tool,
                    self.store_user_tool,
                ]
            )
        if self.rag_mode_enabled:
            tools.extend(
                [
                    self.rag_engine_tool,
                ]
            )
        for name, tool in ToolRegistry.all().items():
            if tool not in tools:
                tools.append(tool)
        return tools

    @property
    def react_tool_agent(self) -> ReActAgentTool:
        """
        Get the ReActAgentTool instance.
        Returns:
            ReActAgentTool: The ReActAgentTool instance.
        """
        if not self._react_tool_agent:
            self._react_tool_agent = ReActAgentTool.from_tools(
                self.tools,
                agent=self,
                memory=self.chat_memory,
                llm=self.llm,
                verbose=True,
                max_function_calls=self.llm_settings.max_function_calls,
                default_tool_choice=self.default_tool_choice,
                return_direct=True,
                context=self.react_agent_prompt,
            )
        return self._react_tool_agent

    @property
    def streaming_stopping_criteria(self) -> ExternalConditionStoppingCriteria:
        """
        Get the streaming stopping criteria.
        Returns:
            ExternalConditionStoppingCriteria: The stopping criteria.
        """
        if not self._streaming_stopping_criteria:
            self._streaming_stopping_criteria = (
                ExternalConditionStoppingCriteria(self.do_interrupt_process)
            )
        return self._streaming_stopping_criteria

    @property
    def chat_engine(self) -> RefreshSimpleChatEngine:
        """
        Get the chat engine instance.
        Returns:
            RefreshSimpleChatEngine: The chat engine instance.
        """

        def factory():
            self.logger.info("Loading RefreshSimpleChatEngine")
            try:
                return RefreshSimpleChatEngine.from_defaults(
                    system_prompt=self.system_prompt,
                    memory=self.chat_memory,
                    llm=self.llm,
                )
            except Exception as e:
                self.logger.error(f"Error loading chat engine: {str(e)}")
                return None

        return self._get_or_create_singleton("_chat_engine", factory)

    @property
    def update_user_data_engine(self) -> RefreshSimpleChatEngine:
        """
        Get the update user data engine instance.
        Returns:
            RefreshSimpleChatEngine: The update user data engine instance.
        """

        def factory():
            self.logger.info("Loading UpdateUserDataEngine")
            return RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._update_user_data_prompt,
                memory=None,
                llm=self.llm,
            )

        return self._get_or_create_singleton(
            "_update_user_data_engine", factory
        )

    @property
    def mood_engine(self) -> RefreshSimpleChatEngine:
        """
        Get the mood engine instance.
        Returns:
            RefreshSimpleChatEngine: The mood engine instance.
        """

        def factory():
            self.logger.info("Loading MoodEngine")
            return RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._mood_update_prompt,
                memory=None,
                llm=self.llm,
            )

        return self._get_or_create_singleton("_mood_engine", factory)

    @property
    def summary_engine(self) -> RefreshSimpleChatEngine:
        """
        Get the summary engine instance.
        Returns:
            RefreshSimpleChatEngine: The summary engine instance.
        """

        def factory():
            self.logger.info("Loading Summary Engine")
            return RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._summarize_conversation_prompt,
                memory=None,
                llm=self.llm,
            )

        return self._get_or_create_singleton("_summary_engine", factory)

    @property
    def information_scraper_engine(self) -> RefreshSimpleChatEngine:
        """
        Get the information scraper engine instance.
        Returns:
            RefreshSimpleChatEngine: The information scraper engine instance.
        """

        def factory():
            self.logger.info("Loading information scraper engine")
            return RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._information_scraper_prompt,
                memory=None,
                llm=self.llm,
            )

        return self._get_or_create_singleton(
            "_information_scraper_engine", factory
        )

    @property
    def mood_engine_tool(self) -> ChatEngineTool:
        """
        Get the mood engine tool instance.
        Returns:
            ChatEngineTool: The mood engine tool instance.
        """

        def factory():
            self.logger.info("Loading MoodEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load MoodEngineTool: Chat engine must be provided."
                )
            return ChatEngineTool.from_defaults(
                chat_engine=self.mood_engine, agent=self, return_direct=True
            )

        return self._get_or_create_singleton("_mood_engine_tool", factory)

    @property
    def update_user_data_tool(self) -> ChatEngineTool:
        """
        Get the update user data tool instance.
        Returns:
            ChatEngineTool: The update user data tool instance.
        """

        def factory():
            self.logger.info("Loading UpdateUserDataTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load UpdateUserDataTool: Chat engine must be provided."
                )
            return ChatEngineTool.from_defaults(
                chat_engine=self.update_user_data_engine,
                agent=self,
                return_direct=True,
            )

        return self._get_or_create_singleton("_update_user_data_tool", factory)

    @property
    def summary_engine_tool(self) -> ChatEngineTool:
        """
        Get the summary engine tool instance.
        Returns:
            ChatEngineTool: The summary engine tool instance.
        """

        def factory():
            self.logger.info("Loading summary engine tool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load summary engine tool: Chat engine must be provided."
                )
            return ChatEngineTool.from_defaults(
                chat_engine=self.summary_engine, agent=self, return_direct=True
            )

        return self._get_or_create_singleton("_summary_engine_tool", factory)

    @property
    def chat_engine_tool(self) -> ChatEngineTool:
        """
        Get the chat engine tool instance.
        Returns:
            ChatEngineTool: The chat engine tool instance.
        """

        def factory():
            self.logger.info("Loading ChatEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load ChatEngineTool: Chat engine must be provided."
                )
            return ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine, agent=self, return_direct=True
            )

        return self._get_or_create_singleton("_chat_engine_tool", factory)

    @property
    def chat_engine_react_tool(self) -> ChatEngineTool:
        """
        Get the chat engine react tool instance.
        Returns:
            ChatEngineTool: The chat engine react tool instance.
        """

        def factory():
            self.logger.info("Loading ChatEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load ChatEngineTool: Chat engine must be provided."
                )
            return ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine,
                agent=self,
                return_direct=True,
                do_handle_response=False,
            )

        return self._get_or_create_singleton("_chat_engine_tool", factory)

    @property
    def do_interrupt(self) -> bool:
        """
        Whether the agent should interrupt the process.
        Returns:
            bool: True if the process should be interrupted.
        """
        return self._do_interrupt

    @do_interrupt.setter
    def do_interrupt(self, value: bool) -> None:
        """
        Set whether the agent should interrupt the process.
        Args:
            value (bool): True to interrupt the process.
        """
        self._do_interrupt = value

    @property
    def bot_mood(self) -> str:
        """
        Get the bot's current mood from the most recent assistant message in the conversation.
        Returns:
            str: The bot's current mood, or "neutral" if not available.
        """
        conversation = self.conversation
        if conversation and conversation.value:
            for msg in reversed(conversation.value):
                if msg.get("role") == "assistant" and "bot_mood" in msg:
                    return msg["bot_mood"]
        return "neutral"

    @bot_mood.setter
    def bot_mood(self, value: str) -> None:
        """
        Set the bot's mood on the most recent assistant message in the conversation.
        Args:
            value (str): The mood to set.
        """
        conversation = self.conversation
        if conversation and conversation.value:
            for msg in reversed(conversation.value):
                if msg.get("role") == "assistant":
                    msg["bot_mood"] = value
                    break

    @property
    def bot_personality(self) -> str:
        """
        Get the bot's personality.
        Returns:
            str: The bot's personality.
        """
        return self.chatbot.bot_personality

    @property
    def botname(self) -> str:
        """
        Get the bot's name.
        Returns:
            str: The bot's name.
        """
        return self.chatbot.botname

    @property
    def username(self) -> str:
        """
        Get the user's name.
        Returns:
            str: The user's name.
        """
        return self.user.username

    @property
    def zipcode(self) -> str:
        """
        Get the user's zipcode.
        Returns:
            str: The user's zipcode.
        """
        return self.user.zipcode

    @property
    def location_display_name(self) -> str:
        """
        Get the user's location display name.
        Returns:
            str: The user's location display name.
        """
        return self.user.location_display_name

    @location_display_name.setter
    def location_display_name(self, value: str) -> None:
        """
        Set the user's location display name.
        Args:
            value (str): The location display name to set.
        """
        self.user.location_display_name = value

    @property
    def day_of_week(self) -> str:
        """
        Get the current day of the week.
        Returns:
            str: The current day of the week.
        """
        return datetime.datetime.now().strftime("%A")

    @property
    def current_date(self) -> str:
        """
        Get the current date.
        Returns:
            str: The current date.
        """
        return datetime.datetime.now().strftime("%A %B %d %Y")

    @property
    def current_time(self) -> str:
        """
        Get the current time.
        Returns:
            str: The current time.
        """
        return datetime.datetime.now().strftime("%H:%M:%S")

    @property
    def timezone(self) -> str:
        """
        Get the current timezone.
        Returns:
            str: The current timezone.
        """
        return datetime.datetime.now().astimezone().tzname()

    @property
    def _information_scraper_prompt(self) -> str:
        """
        Get the information scraper prompt.
        Returns:
            str: The information scraper prompt.
        """
        return PromptConfig.INFORMATION_SCRAPER.format(username=self.username)

    @property
    def _summarize_conversation_prompt(self) -> str:
        """
        Get the summarize conversation prompt.
        Returns:
            str: The summarize conversation prompt.
        """
        return PromptConfig.SUMMARIZE_CONVERSATION

    @property
    def _mood_update_prompt(self) -> str:
        """
        Get the mood update prompt.
        Returns:
            str: The mood update prompt.
        """
        # Defensive check: ensure template is as expected
        template = PromptConfig.MOOD_UPDATE
        expected_keys = {"username", "botname"}

        # Only match single curly braces, not double (escaped) ones
        found_keys = set(
            re.findall(r"(?<!\{)\{([a-zA-Z0-9_]+)\}(?!\})", template)
        )
        if found_keys != expected_keys:
            raise RuntimeError(
                f"PromptConfig.MOOD_UPDATE template keys mismatch: found {found_keys}, expected {expected_keys}. Template: {template}"
            )
        return template.format(username=self.username, botname=self.botname)

    @property
    def system_prompt(self) -> str:
        """
        Construct the system prompt using the PromptBuilder helper class.
        Returns:
            str: The system prompt.
        """
        return PromptBuilder(self).build()

    @property
    def _update_user_data_prompt(self) -> str:
        """
        Get the update user data prompt.
        Returns:
            str: The update user data prompt.
        """
        return PromptConfig.UPDATE_USER_DATA.format(
            username=self.username, botname=self.botname
        )

    @property
    def react_agent_prompt(self) -> str:
        """
        Get the react agent prompt.
        Returns:
            str: The react agent prompt.
        """
        return f"{self.system_prompt}\n"

    def _llm_updated(self) -> None:
        """
        Handle LLM updates.
        """
        pass

    def on_web_browser_page_html(self, content: str) -> None:
        """
        Handle web browser page HTML content.
        Args:
            content (str): The HTML content.
        """
        self.webpage_html = content

    def on_delete_messages_after_id(self) -> None:
        """
        Handle deletion of messages after a specific ID.
        """
        conversation = self.conversation
        if conversation:
            messages = conversation.value
            self.chat_memory.set(messages)
            if self._chat_engine:
                self._chat_engine.memory = self.chat_memory

    def _update_system_prompt(
        self,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
    ) -> None:
        """
        Update the system prompt for the chat engine tool.
        Args:
            system_prompt (Optional[str]): The system prompt to set.
            rag_system_prompt (Optional[str]): The RAG system prompt to set.
        """
        self.chat_engine_tool.update_system_prompt(
            system_prompt or self.system_prompt
        )

        if self.rag_mode_enabled:
            self.update_rag_system_prompt(rag_system_prompt)

    @log_method_entry_exit
    def _perform_analysis(self, action: LLMActionType) -> None:
        """
        Perform analysis on the conversation using ReAct tools (function tools only).
        Args:
            action (LLMActionType): The action type to perform analysis for.
        """
        if action not in (LLMActionType.CHAT,):
            return

        if not self.llm_settings.llm_perform_analysis:
            self.logger.debug("Skipping analysis: LLM analysis is disabled")
            return

        conversation = self.conversation
        if (
            not conversation
            or not conversation.value
            or len(conversation.value) == 0
        ):
            self.logger.debug(
                "Skipping analysis: no conversation or no messages"
            )
            return

        total_messages = len(conversation.value)
        if total_messages < 3:
            self.logger.info("Skipping analysis: not enough messages")
            return

        current_time = datetime.datetime.now()

        last_analyzed_message_id = conversation.last_analyzed_message_id or 0
        if (total_messages - last_analyzed_message_id) < 2:
            self.logger.info("Skipping analysis: not enough new messages")
            return

        self.logger.info("Performing analysis (ReAct tools only)")
        self._update_system_prompt()
        self._update_conversation("last_analysis_time", current_time)
        self._update_conversation(
            "last_analyzed_message_id", total_messages - 1
        )

        # --- Use ReAct tools for mood and analysis ---
        if self.llm_settings.use_chatbot_mood and self.chatbot.use_mood:
            self._update_mood()

        if self.llm_settings.update_user_data_enabled:
            self._update_user_data()

    def _update_llm_request(self, llm_request: Optional[LLMRequest]) -> None:
        """
        Update the LLM request.
        Args:
            llm_request (Optional[LLMRequest]): The LLM request to set.
        """
        self.llm_request = llm_request
        if hasattr(self.llm, "llm_request"):
            self.llm_request = llm_request

    def _update_memory_settings(self) -> None:
        """
        Update the memory settings for the chat engine.
        """
        if (
            type(self.chat_store) is DatabaseChatStore and not self.use_memory
        ) or (type(self.chat_store) is SimpleChatStore and self.use_memory):
            self.chat_memory = None
            self.chat_store = None
        self.chat_engine._memory = self.chat_memory
        self.chat_engine_tool.chat_engine = self.chat_engine

    def _update_memory(self, action: LLMActionType) -> None:
        """
        Update the memory for the given action and ensure all chat engines share the same memory instance.
        Args:
            action (LLMActionType): The action type to update memory for.
        """
        # Use a custom memory strategy if provided
        if self._memory_strategy:
            self._memory = self._memory_strategy(action, self)
        elif action in (LLMActionType.CHAT, LLMActionType.APPLICATION_COMMAND):
            self.chat_memory.chat_store_key = str(self.conversation_id)
            self._memory = self.chat_memory
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            if hasattr(self, "rag_engine") and self.rag_engine is not None:
                self._memory = self.rag_engine.memory
            else:
                self._memory = None
        else:
            self._memory = None

        # Ensure all chat engines share the same memory instance for consistency
        for engine_attr in [
            "_chat_engine",
            "_mood_engine",
            "_summary_engine",
            "_information_scraper_engine",
        ]:
            engine = getattr(self, engine_attr, None)
            if engine is not None:
                engine.memory = self._memory

    @log_method_entry_exit
    def _perform_tool_call(
        self, action: LLMActionType, **kwargs: Any
    ) -> Optional[Any]:
        """
        Perform a tool call based on the LLMActionType using a strategy pattern.
        Args:
            action (LLMActionType): The action type to perform.
            **kwargs (Any): Additional arguments for the tool call.
        Returns:
            Optional[Any]: The result of the tool call, if any.
        """

        def chat_tool_handler(**kwargs: Any) -> Any:
            return self.chat_engine_tool.call(**kwargs)

        def rag_tool_handler(**kwargs: Any) -> Any:
            return self.rag_engine_tool.call(**kwargs)

        def store_data_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "store_user_tool"
            return self.react_tool_agent.call(**kwargs)

        def application_command_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "application_command_tool"
            return self.react_tool_agent.call(**kwargs)

        def generate_image_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "generate_image_tool"
            return self.react_tool_agent.call(**kwargs)

        tool_handlers = {
            LLMActionType.CHAT: chat_tool_handler,
            LLMActionType.PERFORM_RAG_SEARCH: rag_tool_handler,
            LLMActionType.STORE_DATA: store_data_handler,
            LLMActionType.APPLICATION_COMMAND: application_command_handler,
            LLMActionType.GENERATE_IMAGE: generate_image_handler,
        }

        handler = tool_handlers.get(action)
        if handler is None:
            self.logger.warning(f"No handler found for action: {action}")
            return None

        self.logger.info(f"Performing tool call for action: {action}")
        response = handler(**kwargs)
        self.logger.info(f"Tool call for action {action} completed.")
        return response

    def _strip_previous_messages_from_conversation(self) -> None:
        """
        Strips the previous messages from the conversation.
        """
        conversation = self.conversation
        if conversation:
            Conversation.objects.update(
                self.conversation_id, value=conversation.value[:-2]
            )

    def _append_conversation_messages(self, conversation, message):
        """
        Append user and assistant messages to the conversation value.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conversation.value.append(
            {
                "role": "user",
                "name": self.username,
                "content": message,
                "timestamp": now,
            }
        )
        conversation.value.append(
            {
                "role": "assistant",
                "name": self.botname,
                "content": self._complete_response,
                "timestamp": now,
            }
        )

    def _update_conversation_state(self, conversation):
        """
        Update conversation state and chat memory after a turn.
        """
        Conversation.objects.update(
            self.conversation_id,
            value=conversation.value,
            last_analyzed_message_id=len(conversation.value) - 1,
            last_analysis_time=datetime.datetime.now(),
        )
        if self.chat_memory is not None:
            chat_messages = [
                (
                    msg
                    if hasattr(msg, "blocks")
                    else ChatMessage(
                        role=msg.get("role", "user"),
                        blocks=[TextBlock(text=msg.get("content", ""))],
                    )
                )
                for msg in conversation.value
            ]
            self.chat_memory.set(chat_messages)
        if self.chat_engine is not None:
            self.chat_engine.memory = self.chat_memory
        if (
            hasattr(self, "react_tool_agent")
            and self.react_tool_agent is not None
        ):
            self.react_tool_agent.memory = self.chat_memory

    @log_method_entry_exit
    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        **kwargs: Any,
    ) -> AgentChatResponse:
        """
        Handle a chat message and generate a response.
        """
        if getattr(self, "_in_chat", False):
            self.logger.warning(
                "Re-entrant call to chat() detected, aborting to prevent loop."
            )
            return AgentChatResponse(response="")
        self._in_chat = True
        try:
            self.prompt = message
            self.action = action
            system_prompt = self.system_prompt
            self._chat_prompt = message
            self._complete_response = ""
            self.do_interrupt = False
            self._update_memory(action)
            kwargs = kwargs or {}
            kwargs["input"] = f"{self.username}: {message}"
            self._update_system_prompt(system_prompt, rag_system_prompt)
            self._update_llm_request(llm_request)
            self._update_memory_settings()
            self._perform_tool_call(action, **kwargs)
            conversation = self.conversation
            if conversation is not None:
                self._append_conversation_messages(conversation, message)
                self._update_conversation_state(conversation)
                # --- Restore: update mood after assistant message is appended ---
                if (
                    self.llm_settings.use_chatbot_mood
                    and getattr(self, "chatbot", None)
                    and getattr(self.chatbot, "use_mood", False)
                ):
                    self._update_mood()
            self._perform_analysis(action)
            return AgentChatResponse(response=self._complete_response)
        finally:
            self._in_chat = False

    def on_load_conversation(self, data: Optional[Dict] = None) -> None:
        """
        Handle loading a conversation and ensure chat store/memory are restored.
        Args:
            data (Optional[Dict]): The conversation data.
        """
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        self.conversation = Conversation.objects.get(conversation_id)
        if conversation_id is not None and self.use_memory:
            # Always re-initialize chat memory for the loaded conversation
            self._chat_memory = None  # Force re-creation
            messages = self.chat_store.get_messages(str(conversation_id))
            # This will create a new ChatMemoryBuffer with the correct key
            _ = (
                self.chat_memory
            )  # property will re-initialize with correct key
            self.chat_memory.set(messages)
            if self.chat_engine is not None:
                self.chat_engine.memory = self.chat_memory
            if (
                hasattr(self, "react_tool_agent")
                and self.react_tool_agent is not None
            ):
                self.react_tool_agent.memory = self.chat_memory

    def on_conversation_deleted(self, data: Optional[Dict] = None) -> None:
        """
        Handle conversation deletion.
        Args:
            data (Optional[Dict]): The conversation data.
        """
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        if (
            conversation_id == self.conversation_id
            or self.conversation_id is None
        ):
            self.conversation = None
            self.conversation_id = None

    def clear_history(self, data: Optional[Dict] = None) -> None:
        """
        Clear the conversation history.
        Args:
            data (Optional[Dict]): The conversation data.
        """
        data = data or {}
        conversation_id = data.get("conversation_id", None)

        self.conversation_id = conversation_id

        try:
            _ = self.chat_engine
        except Exception as e:
            self.logger.warning(
                f"clear_history: chat_engine not available, skipping reset_memory and continuing UI: {e}"
            )
            return
        if self.chat_engine is None:
            self.logger.warning(
                "clear_history: chat_engine is None after property, skipping reset_memory and continuing UI."
            )
            return

    def save_chat_history(self) -> None:
        """
        Save the chat history.
        """
        pass

    def interrupt_process(self) -> None:
        """
        Interrupt the current process.
        """
        self.do_interrupt = True

    def do_interrupt_process(self) -> bool:
        """
        Check if the process should be interrupted.
        Returns:
            bool: True if the process should be interrupted.
        """
        if self.do_interrupt:
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    name=self.botname,
                )
            )
        return self.do_interrupt

    @log_method_entry_exit
    def handle_response(
        self,
        response: str,
        is_first_message: bool = False,
        is_last_message: bool = False,
        do_not_display: bool = False,
        do_tts_reply: bool = True,
    ) -> None:
        """
        Handle a streamed or final response from the LLM.
        Args:
            response (str): The response text to handle.
            is_first_message (bool): Whether this is the first message in a stream.
            is_last_message (bool): Whether this is the last message in a stream.
            do_not_display (bool): If True, do not emit the signal to display the message.
            do_tts_reply (bool): If True, perform TTS reply.
        """
        # Log the actual response for debugging
        self.logger.debug(
            f"handle_response called with response: '{response}' (do_not_display={do_not_display})"
        )

        # Defensive: Only process non-empty responses
        if not response and not do_not_display:
            self.logger.debug("handle_response: Skipping empty response.")
            return

        # The 'full_message' variable as defined in the diff caused duplication when sent.
        # We should send the individual 'response' (token/chunk) and then accumulate.

        if not do_not_display:
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    message=response,
                    is_first_message=is_first_message,
                    is_end_of_message=is_last_message,
                    name=self.botname,
                    node_id=self.llm_request.node_id,
                )
            )
            self._complete_response += response

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name from the registry.
        Args:
            name (str): The name of the tool.
        Returns:
            Optional[BaseTool]: The tool instance.
        """
        return ToolRegistry.get(name)

    def get_engine(self, name: str) -> Optional[RefreshSimpleChatEngine]:
        """
        Get an engine by name from the registry.
        Args:
            name (str): The name of the engine.
        Returns:
            Optional[RefreshSimpleChatEngine]: The engine instance.
        """
        return EngineRegistry.get(name)

    @property
    def chatbot(self) -> Any:
        """
        Get the chatbot instance.
        Returns:
            Any: The chatbot instance.
        """
        if hasattr(self, "_chatbot") and self._chatbot is not None:
            return self._chatbot
        return super().chatbot

    @chatbot.setter
    def chatbot(self, value: Any) -> None:
        """
        Set the chatbot instance.
        Args:
            value (Any): The chatbot instance to set.
        """
        self._chatbot = value

    @property
    def api(self):
        """Return the API manager instance (must provide externally if not set)."""
        if hasattr(self, "_api") and self._api is not None:
            return self._api
        raise AttributeError(
            "API manager not set on agent. Set agent._api = api_manager instance."
        )

    @api.setter
    def api(self, value):
        self._api = value

    def update_mood(self, mood_description: str, emoji: str) -> str:
        """
        Update the bot's mood using the mood_tool (ReAct tool).
        Args:
            mood_description (str): The mood description.
            emoji (str): The emoji representing the mood.
        Returns:
            str: Result message.
        """
        return self.mood_tool(mood_description, emoji)

    def update_analysis(self, analysis: str) -> str:
        """
        Update the conversation analysis/summary using the analysis_tool (ReAct tool).
        Args:
            analysis (str): The analysis or summary string.
        Returns:
            str: Result message.
        """
        return self.analysis_tool(analysis)


class PromptBuilder:
    """
    Helper class to modularize and construct the system prompt for BaseAgent.
    """

    def __init__(self, agent: "BaseAgent") -> None:
        """
        Initialize the PromptBuilder.
        Args:
            agent (BaseAgent): The agent instance for which to build the prompt.
        """
        self.agent = agent

    def build(self) -> str:
        """
        Build and return the system prompt string for the agent.
        Returns:
            str: The constructed system prompt.
        """
        chatbot = self.agent.chatbot
        botname = self.agent.botname
        username = self.agent.username
        system_instructions = ""
        if (
            chatbot.use_system_instructions
            and chatbot.system_instructions
            and chatbot.system_instructions != ""
        ):
            system_instructions = f"Always follow these instructions:\n{chatbot.system_instructions}\n"
        guardrails = ""
        if (
            chatbot.use_guardrails
            and chatbot.guardrails_prompt
            and chatbot.guardrails_prompt != ""
        ):
            guardrails = f"Always follow these guardrails:\n{chatbot.guardrails_prompt}\n"
        backstory_prompt = ""
        if (
            chatbot.use_backstory
            and chatbot.backstory
            and chatbot.backstory != ""
        ):
            backstory_prompt = (
                "------\n"
                f"**Here is {botname}'s backstory:**\n"
                f"{chatbot.backstory}\n"
                "------\n"
            )
        conversation_timestamp_prompt = ""
        if self.agent.conversation is not None:
            conversation_timestamp_prompt = f"The conversation started on {self.agent.conversation.timestamp}.\n"
        prompt = (
            f"Your name is {botname}.\n"
            f"- The user ({username}) is having a conversation with the assistant ({botname}).\n"
            "**Here are the rules that you must always remember:**\n"
            "- You will ONLY generate dialogue, nothing more.\n"
            "- Only generate responses in pure dialogue form without including any actions, descriptions or stage "
            "directions in parentheses. Only return spoken words.\n"
            "- Do not generate redundant dialogue. Examine the conversation and context close and keep responses "
            "interesting and creative.\n"
            "- Do not format the response with the character's name or any other text. Only return the dialogue.\n"
            f"- Never generate dialogue for {username}, only for {botname}\n"
            f"- Never generate dialogue that has already been said in the conversation.\n"
            f"- {botname} and {username} are both humans. They are not AI or bots.\n"
            f"- As {botname}, you will always respond in a way that is consistent with {botname}'s emotions, "
            f"personality, and the context of the conversation.\n"
            "- Generate emotional, persuasive, and realistic responses.\n"
            "- Do not generate text asking how to provide assistance, or how to can help.\n"
            "- Generate dialogue that is realistic for the {botname} character.\n"
            "- The generate dialogue can contain questions, make statements, and provide information.\n"
            "- Generated dialogue should be consistent with {botname}'s personality and mood.\n"
            f"{backstory_prompt}"
            f"{system_instructions}"
            f"{guardrails}"
            "------\n"
            "**Here is more context that you can use to generate a response:**\n"
            f"{self.agent.date_time_prompt}"
            f"{self.agent.personality_prompt}"
            f"{self.agent.mood_prompt}"
            f"{self.agent.operating_system_prompt}"
            f"{self.agent.speakers_prompt}"
            f"{self.agent.weather_prompt}"
            f"{self.agent.conversation_summary_prompt}"
            "------\n"
            "**More information about the current conversation:**\n"
            f"The conversation is between user ({username}) and assistant ({botname}).\n"
            f"{conversation_timestamp_prompt}"
            "------\n"
        )
        if self.agent.language:
            prompt += f"Respond to {{ username }} in {self.agent.language}. Only deviate from this if the user asks you to.\n"
        prompt = prompt.replace("{{ username }}", username)
        prompt = prompt.replace("{{ botname }}", botname)
        prompt = prompt.replace("{{ speaker_name }}", username)
        prompt = prompt.replace("{{ listener_name }}", botname)
        return prompt
