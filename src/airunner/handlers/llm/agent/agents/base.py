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
from airunner.handlers.llm.agent.agents.prompt_builder import PromptBuilder
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent import (
    RAGMixin,
    ExternalConditionStoppingCriteria,
)
from airunner.handlers.llm.agent.tools import ChatEngineTool, ReActAgentTool
from airunner.handlers.llm.agent.tools.search_engine_tool import (
    SearchEngineTool,
)
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
    VERBOSE_REACT_TOOL_AGENT,
)
from airunner.utils.llm.language import detect_language
from airunner.handlers.llm.agent.agents.registry import (
    ToolRegistry,
    EngineRegistry,
)
from airunner.handlers.llm.agent.agents.tool_mixins import (
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


class BaseAgent(
    MediatorMixin,
    SettingsMixin,
    RAGMixin,
    WeatherMixin,
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
        verbose_react_tool_agent: bool = VERBOSE_REACT_TOOL_AGENT,
        *args,
        **kwargs,
    ) -> None:
        self.default_tool_choice: Optional[Union[str, dict]] = (
            default_tool_choice
        )
        self.prompt: Optional[str] = None
        self.webpage_html: str = ""
        self.current_tab: Optional[Tab] = None
        self.do_interrupt: bool = False
        self.llm_settings: LLMSettings = llm_settings
        self._use_memory: bool = use_memory
        self._action: LLMActionType = LLMActionType.NONE
        self._chat_prompt: str = ""
        self._streaming_stopping_criteria: Optional[
            ExternalConditionStoppingCriteria
        ] = None
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
        self.model: Optional[Any] = model
        self.tokenizer: Optional[Any] = tokenizer
        self._conversation_strategy = conversation_strategy
        self._memory_strategy = memory_strategy
        self._llm_strategy = llm_strategy
        self._chatbot = None
        self._api = None
        self.verbose_react_tool_agent = verbose_react_tool_agent
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            from airunner.utils.application.get_logger import get_logger
            from airunner.settings import AIRUNNER_LOG_LEVEL

            self._logger = get_logger(
                self.__class__.__name__, AIRUNNER_LOG_LEVEL
            )
        self.signal_handlers.update(
            {
                SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id,
            }
        )
        self.extra_context: list[str] = []
        super().__init__(*args, **kwargs)

    @property
    def latest_extra_context(self) -> str:
        """
        Get the most recently added extra context string.
        Returns:
            str: The latest context string, or empty string if none.
        """
        return self.extra_context[-1] if self.extra_context else ""

    @property
    def logger(self):
        return self._logger

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
            self.search_engine_tool,  # Use new SearchEngineTool instead of search_tool
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
        # Only add tool instances, not classes
        for name, tool in ToolRegistry.all().items():
            if not isinstance(tool, type) and tool not in tools:
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
                max_function_calls=self.llm_settings.max_function_calls,
                default_tool_choice=self.default_tool_choice,
                return_direct=True,
                context=self.react_agent_prompt,
                verbose=self.verbose_react_tool_agent,
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
                return RefreshSimpleChatEngine(
                    llm=self.llm,
                    memory=self.chat_memory,
                    prefix_messages=(
                        [
                            ChatMessage(
                                content=self.system_prompt,
                                role=self.llm.metadata.system_role,
                            )
                        ]
                        if self.system_prompt
                        else None
                    ),
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
            return RefreshSimpleChatEngine(
                llm=self.llm,
                memory=None,
                prefix_messages=(
                    [
                        ChatMessage(
                            content=self._update_user_data_prompt,
                            role=self.llm.metadata.system_role,
                        )
                    ]
                    if hasattr(self, "_update_user_data_prompt")
                    and self._update_user_data_prompt
                    else None
                ),
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
            return RefreshSimpleChatEngine(
                llm=self.llm,
                memory=None,
                prefix_messages=(
                    [
                        ChatMessage(
                            content=self._mood_update_prompt,
                            role=self.llm.metadata.system_role,
                        )
                    ]
                    if hasattr(self, "_mood_update_prompt")
                    and self._mood_update_prompt
                    else None
                ),
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
            return RefreshSimpleChatEngine(
                llm=self.llm,
                memory=None,
                prefix_messages=(
                    [
                        ChatMessage(
                            content=self._summarize_conversation_prompt,
                            role=self.llm.metadata.system_role,
                        )
                    ]
                    if hasattr(self, "_summarize_conversation_prompt")
                    and self._summarize_conversation_prompt
                    else None
                ),
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
            return RefreshSimpleChatEngine(
                llm=self.llm,
                memory=None,
                prefix_messages=(
                    [
                        ChatMessage(
                            content=self._information_scraper_prompt,
                            role=self.llm.metadata.system_role,
                        )
                    ]
                    if hasattr(self, "_information_scraper_prompt")
                    and self._information_scraper_prompt
                    else None
                ),
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
    def search_engine_tool(self) -> SearchEngineTool:
        """
        Get the search engine tool instance.
        Returns:
            SearchEngineTool: The search engine tool instance.
        """

        def factory():
            self.logger.info("Loading SearchEngineTool")
            if not self.llm:
                raise ValueError(
                    "Unable to load SearchEngineTool: LLM must be provided."
                )
            return SearchEngineTool.from_defaults(
                llm=self.llm,
                agent=self,
                return_direct=True,
                do_handle_response=True,  # Enable streaming through agent.handle_response
            )

        return self._get_or_create_singleton("_search_engine_tool", factory)

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

    def _llm_updated(self) -> None:
        """
        Handle LLM updates.
        """
        pass

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

    def _sync_memory_to_all_engines(self) -> None:
        """
        Ensure all engine instances share the same memory instance for full context.
        """
        for engine_attr in [
            "_chat_engine",
            "_mood_engine",
            "_summary_engine",
            "_information_scraper_engine",
        ]:
            engine = getattr(self, engine_attr, None)
            if engine is not None:
                engine.memory = self._memory

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
        self._sync_memory_to_all_engines()

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
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            return self.chat_engine_tool.call(**kwargs)

        def rag_tool_handler(**kwargs: Any) -> Any:
            # Ensure the query is always forwarded as 'query' (and 'input' for compatibility)
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            # Defensive: ensure chat_memory and rag_engine.memory are set up with correct chat_store_key
            if hasattr(self, "chat_memory") and self.chat_memory is not None:
                self.chat_memory.chat_store_key = str(self.conversation_id)
            if hasattr(self, "rag_engine") and self.rag_engine is not None:
                self.rag_engine.memory = self.chat_memory
            # Patch: Forward 'prompt' or 'input' as 'query' if 'query' is missing
            query_arg = None
            if "query" in kwargs:
                query_arg = kwargs["query"]
            elif "input" in kwargs:
                query_arg = kwargs["input"]
            elif "prompt" in kwargs:
                query_arg = kwargs["prompt"]
            # Remove 'query', 'input', and 'prompt' from kwargs to avoid TypeError
            for k in ["query", "input", "prompt"]:
                if k in kwargs:
                    del kwargs[k]
            if query_arg is not None:
                response = self.rag_engine_tool.call(query_arg, **kwargs)
            else:
                response = self.rag_engine_tool.call(**kwargs)
            # Handle/display the response as with other tools
            if response is not None:
                # If response is a ToolOutput, AgentChatResponse, or similar, extract string content
                content = getattr(response, "content", None)
                if content is None and hasattr(response, "response"):
                    content = response.response
                if content is None:
                    content = str(response)
                self.handle_response(
                    content, is_first_message=True, is_last_message=True
                )
                self._complete_response = content
            return response

        def store_data_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "store_user_tool"
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            return self.react_tool_agent.call(**kwargs)

        def application_command_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "application_command_tool"
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            return self.react_tool_agent.call(**kwargs)

        def generate_image_handler(**kwargs: Any) -> Any:
            kwargs["tool_choice"] = "generate_image_tool"
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            return self.react_tool_agent.call(**kwargs)

        def search_tool_handler(**kwargs: Any) -> Any:
            if "chat_history" not in kwargs:
                kwargs["chat_history"] = (
                    self.chat_memory.get() if self.chat_memory else []
                )
            # Only call the search tool; it will invoke the chat engine tool as needed
            return self.search_engine_tool.call(**kwargs)

        tool_handlers = {
            LLMActionType.CHAT: chat_tool_handler,
            LLMActionType.DECISION: chat_tool_handler,
            LLMActionType.PERFORM_RAG_SEARCH: rag_tool_handler,
            LLMActionType.STORE_DATA: store_data_handler,
            LLMActionType.APPLICATION_COMMAND: application_command_handler,
            LLMActionType.GENERATE_IMAGE: generate_image_handler,
            LLMActionType.SEARCH: search_tool_handler,
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
        Append user and assistant messages to the conversation value using the unified engine logic.
        Always store with both 'content' and 'blocks' fields for compatibility.
        """
        if hasattr(self.chat_engine, "append_conversation_messages"):
            self.chat_engine.append_conversation_messages(
                conversation, message, self._complete_response
            )
        else:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conversation.value.append(
                {
                    "role": "user",
                    "name": self.username,
                    "content": message,
                    "timestamp": now,
                    "blocks": [{"block_type": "text", "text": message}],
                }
            )
            conversation.value.append(
                {
                    "role": "assistant",
                    "name": self.botname,
                    "content": self._complete_response,
                    "timestamp": now,
                    "blocks": [
                        {"block_type": "text", "text": self._complete_response}
                    ],
                }
            )

    def _update_conversation_state(self, conversation):
        """
        Update conversation state and chat memory after a turn using the unified engine logic.
        Ensures all messages are converted to ChatMessage objects with blocks for memory buffer compatibility.
        """
        if hasattr(self.chat_engine, "update_conversation_state"):
            self.chat_engine.update_conversation_state(conversation)
        else:
            Conversation.objects.update(
                self.conversation_id,
                value=conversation.value,
                last_analyzed_message_id=len(conversation.value) - 1,
                last_analysis_time=datetime.datetime.now(),
            )
            if self.chat_memory is not None:
                chat_messages = []
                for msg in conversation.value:
                    # Convert to ChatMessage with blocks if not already
                    if hasattr(msg, "blocks") and isinstance(msg.blocks, list):
                        chat_messages.append(msg)
                    elif isinstance(msg, dict):
                        content = msg.get("content", "")
                        role = msg.get("role", "user")
                        if role == "bot":
                            role = "assistant"
                        chat_messages.append(
                            ChatMessage(
                                role=role,
                                blocks=[TextBlock(text=content)],
                            )
                        )
                    else:
                        # Fallback: treat as plain text
                        chat_messages.append(
                            ChatMessage(
                                role="user", blocks=[TextBlock(text=str(msg))]
                            )
                        )
                self.chat_memory.set(chat_messages)
            self._sync_memory_to_all_engines()

    def _remove_last_message_from_conversation(self, conversation) -> None:
        """
        Remove the last message from the conversation.
        This is used to handle cases where the last message needs to be deleted or modified.
        Ensures memory buffer receives ChatMessage objects, not dicts.
        """
        if conversation and conversation.value:
            conversation.value.pop()
            # Convert dicts to ChatMessage objects for memory compatibility
            from llama_index.core.base.llms.types import ChatMessage, TextBlock

            messages = []
            for msg in conversation.value:
                if isinstance(msg, dict):
                    text = msg.get("content", "")
                    role = msg.get("role", "user")
                    blocks = [TextBlock(text=text)]
                    messages.append(ChatMessage(role=role, blocks=blocks))
                else:
                    messages.append(msg)
            self.chat_memory.set(messages)

    def _make_chat_message(self, role: str, content: str) -> ChatMessage:
        """
        Helper to create a ChatMessage for unified engine logic.
        """
        return ChatMessage(role=role, blocks=[TextBlock(text=content)])

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
            self._sync_memory_to_all_engines()

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
            if (
                self.llm_settings.use_chatbot_mood
                and getattr(self, "chatbot", None)
                and getattr(self.chatbot, "use_mood", False)
            ):
                self._update_mood()
        self._perform_analysis(action)
        return AgentChatResponse(response=self._complete_response)

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
        self._sync_memory_to_all_engines()

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
        # Defensive: Only process non-empty responses
        if not response and not do_not_display:
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