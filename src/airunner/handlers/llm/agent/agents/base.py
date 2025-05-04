import os
from typing import (
    Any,
    List,
    Optional,
    Union,
    Dict,
    Type,
    Annotated,
)
import datetime
import platform

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.llms.llm import LLM
from llama_index.core.storage.chat_store.base import BaseChatStore
from llama_index.core.storage.chat_store import SimpleChatStore

from transformers import AutoModelForCausalLM, AutoTokenizer

from airunner.enums import GeneratorSection, LLMActionType, SignalCode, ImagePreset
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
from airunner.handlers.llm.agent.memory import ChatMemoryBuffer
from airunner.handlers.llm.storage.chat_store import DatabaseChatStore
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.llm.llm_settings import LLMSettings
from airunner.handlers.llm import HuggingFaceLLM
from airunner.data.models import Conversation
from airunner.settings import (
    AIRUNNER_LLM_CHAT_STORE,
    AIRUNNER_ART_ENABLED,
    AIRUNNER_MOOD_PROMPT_OVERRIDE,
)


class BaseAgent(
    MediatorMixin,
    SettingsMixin,
    RAGMixin,
    WeatherMixin,
):
    """
    Base class for all agents.

    Args:
        default_tool_choice (Optional[Union[str, dict], optional): The default tool choice. Defaults to None.
        llm_settings (LLMSettings, optional): The LLM settings. Defaults to LLMSettings().
    """

    def __init__(
        self,
        default_tool_choice: Optional[Union[str, dict]] = None,
        llm_settings: LLMSettings = LLMSettings(),
        use_memory: bool = True,
        *args,
        **kwargs,
    ) -> None:
        self.default_tool_choice: Optional[Union[str, dict]] = (
            default_tool_choice
        )
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
        self._chat_engine: Optional[RefreshSimpleChatEngine] = None
        self._mood_engine: Optional[RefreshSimpleChatEngine] = None
        self._summary_engine: Optional[RefreshSimpleChatEngine] = None
        self._chat_engine_tool: Optional[ChatEngineTool] = None
        self._mood_engine_tool: Optional[ChatEngineTool] = None
        self._update_user_data_engine = None
        self._update_user_data_tool = None
        self._summary_engine_tool: Optional[ChatEngineTool] = None
        self._information_scraper_tool: Optional[ChatEngineTool] = None
        self._information_scraper_engine: Optional[RefreshSimpleChatEngine] = (
            None
        )
        self._chat_store: Optional[Type[BaseChatStore]] = None
        self._chat_memory: Optional[ChatMemoryBuffer] = None
        self._memory: Optional[BaseMemory] = None
        self._react_tool_agent: Optional[ReActAgentTool] = None
        self._complete_response: str = ""
        self._store_user_tool: Optional[FunctionTool] = None
        self._webpage_html: str = ""
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None

        self.signal_handlers.update(
            {
                SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id
            }
        )
        super().__init__(*args, **kwargs)

    @property
    def use_memory(self) -> bool:
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
        return self._action

    @action.setter
    def action(self, value: LLMActionType):
        self._action = value

    @property
    def chat_mode_enabled(self) -> bool:
        return self.action is LLMActionType.CHAT

    @property
    def rag_enabled(self) -> bool:
        return self.rag_settings.enabled

    @property
    def rag_mode_enabled(self) -> bool:
        return (
            self.rag_enabled
            and self.action is LLMActionType.PERFORM_RAG_SEARCH
        )

    @property
    def conversation_summaries(self) -> str:
        summaries = ""
        conversations = Conversation.objects.order_by(Conversation.id.desc())[
            :5
        ]
        conversations = list(conversations)
        conversations = sorted(conversations, key=lambda x: x.id, reverse=True)
        for conversation in conversations:
            if conversation.summary:
                summaries += f"- {conversation.summary}\n"
        if summaries != "":
            summaries = f"Recent conversation summaries:\n{summaries}"
        return summaries

    @property
    def date_time_prompt(self) -> str:
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
        return (
            f"{self.botname}'s personality: {self.chatbot.bot_personality}\n"
            if self.chatbot.use_personality
            else ""
        )

    @property
    def mood_prompt(self) -> str:
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

    @property
    def conversation_summary_prompt(self) -> str:
        return (
            f"- Conversation summary:\n{self.conversation.summary}\n"
            if self.conversation and self.conversation.summary
            else ""
        )

    def unload(self):
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
    def llm_request(self) -> LLMRequest:
        if not self._llm_request:
            self._llm_request = LLMRequest.from_default()
        return self._llm_request

    @llm_request.setter
    def llm_request(self, value: LLMRequest):
        self._llm_request = value

    @property
    def llm(self) -> Type[LLM]:
        if not self._llm and self.model and self.tokenizer:
            self.logger.info("Loading HuggingFaceLLM")
            if self.model and self.tokenizer:
                self._llm = HuggingFaceLLM(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    streaming_stopping_criteria=self.streaming_stopping_criteria,
                )
                self._llm_updated()
            else:
                self.logger.error(
                    "Unable to load HuggingFaceLLM: "
                    "Model and tokenizer must be provided."
                )
        return self._llm

    @property
    def webpage_html(self) -> str:
        return self._webpage_html

    @webpage_html.setter
    def webpage_html(self, value: str):
        self._webpage_html = value

    @property
    def current_tab(self) -> Optional[Tab]:
        if not self._current_tab:
            self._current_tab = Tab.objects.filter_by_first(
                section="center", active=True
            )
        return self._current_tab

    @current_tab.setter
    def current_tab(self, value: Optional[Tab]):
        self._current_tab = value

    @property
    def do_summarize_conversation(self) -> bool:
        if not self.conversation:
            return False

        messages = self.conversation.value or []
        total_messages = len(messages)
        if (
            (
                total_messages > self.llm_settings.summarize_after_n_turns
                and self.conversation.summary is None
            )
            or total_messages % self.llm_settings.summarize_after_n_turns == 0
        ):
            return True
        return False

    @property
    def user(self) -> User:
        if not self._user:
            user = None
            if self.conversation:
                user = User.objects.get(self.conversation.user_id)
            if not user:
                user = User.objects.filter_first(
                    User.username == self.username
                )
            if not user:
                user = User()
                user.save()
            self.user = user
        return self._user

    @user.setter
    def user(self, value: Optional[User]):
        self._user = value
        self._update_conversation("user_id", value.id)

    @property
    def information_scraper_tool(self) -> FunctionTool:
        self.logger.info("information_scraper_tool called")
        if not self._information_scraper_tool:

            def scrape_information(tag: str, information: str) -> str:
                """Scrape information from the text."""
                self.logger.info(f"Scraping information for tag: {tag}")
                self.logger.info(f"Information: {information}")
                self._update_user(tag, information)
                data = self.user.data or {}
                data[tag] = (
                    [information]
                    if tag not in data
                    else data[tag] + [information]
                )
                self._update_user("data", data)
                return "Information scraped."

            self._information_scraper_tool = FunctionTool.from_defaults(
                scrape_information, return_direct=True
            )

        return self._information_scraper_tool

    @property
    def store_user_tool(self) -> FunctionTool:
        if not self._store_user_tool:

            def store_user_information(
                category: Annotated[
                    str,
                    (
                        "The category of the information to store. "
                        "Can be 'likes', 'dislikes', 'hobbies', 'interests', etc."
                    ),
                ],
                information: Annotated[
                    str,
                    (
                        "The information to store. "
                        "This can be a string or a list of strings."
                    ),
                ],
            ) -> str:
                """Store information about the user with this tool.

                Choose this when you need to save information about the user.
                """
                data = self.user.data or {}
                data[category] = (
                    [information]
                    if category not in data
                    else data[category] + [information]
                )
                self._update_user(category, information)
                return "User information updated."

            self._store_user_tool = FunctionTool.from_defaults(
                store_user_information, return_direct=True
            )

        return self._store_user_tool

    @property
    def quit_application_tool(self) -> FunctionTool:
        if not hasattr(self, "_quit_application_tool"):

            def quit_application() -> str:
                """Quit the application.

                Call this tool if the user wants to quit the application,
                asks you to quit, shutdown or exit. Do not panic and
                close the application on your own."""
                self.api.quit_application()
                return "Quitting application..."

            self._quit_application_tool = FunctionTool.from_defaults(
                quit_application, return_direct=True
            )
        return self._quit_application_tool

    @property
    def toggle_text_to_speech_tool(self) -> FunctionTool:
        if not hasattr(self, "_toggle_text_to_speech"):

            def toggle_text_to_speech(
                enabled: Annotated[
                    bool,
                    (
                        "Enable or disable text to speech. "
                        "Must be 'True' or 'False'."
                    ),
                ],
            ) -> str:
                """Enable or disable the text-to-speech.

                Call this tool if the user wants to enable or disable
                text to speech."""
                self.api.tts.toggle(enabled)
                return "Text to speech toggled."

            self._toggle_text_to_speech = FunctionTool.from_defaults(
                toggle_text_to_speech, return_direct=True
            )
        return self._toggle_text_to_speech

    @property
    def list_files_in_directory_tool(self) -> FunctionTool:
        if not hasattr(self, "_list_files_in_directory_tool"):

            def list_files_in_directory(
                directory: Annotated[
                    str,
                    (
                        "The directory to search in. "
                        "Must be a valid directory path."
                    ),
                ],
            ) -> str:
                """List files in a directory.

                Call this tool if the user wants to list files in a directory.
                """
                os_path = os.path.abspath(directory)
                if not os.path.isdir(os_path):
                    return "Invalid directory path."
                if not os.path.exists(os_path):
                    return "Directory does not exist."
                return os.listdir(os_path)

            self._list_files_in_directory_tool = FunctionTool.from_defaults(
                list_files_in_directory, return_direct=False
            )
        return self._list_files_in_directory_tool

    @property
    def open_image_from_path_tool(self) -> FunctionTool:
        if not hasattr(self, "_open_image_from_path_tool"):

            def open_image_from_path(
                image_path: Annotated[
                    str,
                    (
                        "The path to the image file. "
                        "Must be a valid file path."
                    ),
                ],
            ) -> str:
                """Open an image from a specific path.

                Call this tool if the user wants to open an image. First Find
                the image file from a directory and then use this tool to open in.
                """
                if not os.path.isfile(image_path):
                    return (
                        f"Unable to open image: {image_path} does not exist."
                    )
                self.api.art.canvas.image_from_path(image_path)
                return "Opening image..."

            self._open_image_from_path_tool = FunctionTool.from_defaults(
                open_image_from_path, return_direct=True
            )
        return self._open_image_from_path_tool

    @property
    def clear_canvas_tool(self) -> FunctionTool:
        if not hasattr(self, "_clear_canvas_tool"):

            def clear_canvas() -> str:
                """Clear the canvas.

                Call this tool if the user wants to clear the canvas, delete
                images, etc."""
                self.api.art.canvas.clear()
                return "Canvas cleared."

            self._clear_canvas_tool = FunctionTool.from_defaults(
                clear_canvas, return_direct=True
            )
        return self._clear_canvas_tool

    @property
    def clear_conversation_tool(self) -> FunctionTool:
        if not hasattr(self, "_clear_conversation_tool"):

            def clear_conversation() -> str:
                """Clear the conversation.

                Call this tool if the user wants to clear the conversation,
                delete messages, etc."""
                self.api.llm.clear_history()
                return "Conversation cleared."

            self._clear_conversation_tool = FunctionTool.from_defaults(
                clear_conversation, return_direct=True
            )
        return self._clear_conversation_tool

    @property
    def set_working_width_and_height(self) -> FunctionTool:
        if not hasattr(self, "_set_working_width_and_height"):

            def set_working_width_and_height(
                width: Annotated[
                    Optional[int],
                    (
                        f"The width of the image. Currently: {self.application_settings.working_width}. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
                height: Annotated[
                    Optional[int],
                    (
                        f"The height of the image. Currently: {self.application_settings.working_height}. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
            ) -> str:
                """Set the working width and height of the image canvas.

                Only call this if the one current sizes is different from
                one of the requested sizes.
                Images will be generated at this size. Call this tool if the
                user requests that you change the size of the working width / height,
                or active canvas area, or working image size etc."""
                if width is not None:
                    self.update_application_settings("working_width", width)

                if height is not None:
                    self.update_application_settings("working_height", height)

                return f"Working width and height set to {width}x{height}."

            self._set_working_width_and_height = FunctionTool.from_defaults(
                set_working_width_and_height, return_direct=True
            )
        return self._set_working_width_and_height

    @property
    def generate_image_tool(self) -> FunctionTool:
        if not hasattr(self, "_generate_image_tool"):
            image_preset_options = [item.value for item in ImagePreset]

            def generate_image(
                prompt: Annotated[
                    str,
                    (
                        "Describe the subject of the image along with the "
                        "composition, lighting, lens type and other "
                        "descriptors that will bring the image to life."
                    ),
                ],
                second_prompt: Annotated[
                    str,
                    (
                        "Describe the scene, the background, the colors, "
                        "the mood and other descriptors that will enhance "
                        "the image."
                    ),
                ],
                image_type: Annotated[
                    GeneratorSection,
                    (
                        "The type of image to generate. "
                        f"Can be {image_preset_options}."
                    ),
                ],
                width: Annotated[
                    int,
                    (
                        "The width of the image. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
                height: Annotated[
                    int,
                    (
                        "The height of the image. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
            ) -> str:
                """Generate an image using the given request."""
                # Enforce width and height constraints
                if width % 64 != 0:
                    # get as close to multiple of 64 as possible
                    width = (width // 64) * 64
                if height % 64 != 0:
                    # get as close to multiple of 64 as possible
                    height = (height // 64) * 64

                self.api.art.llm_image_generated(
                    prompt, second_prompt, image_type, width, height
                )
                return "Generating image..."

            self._generate_image_tool = FunctionTool.from_defaults(
                generate_image, return_direct=True
            )
        return self._generate_image_tool

    @property
    def tools(self) -> List[BaseTool]:
        tools = [
            self.chat_engine_react_tool,
            self.quit_application_tool,
            self.clear_conversation_tool,
            self.toggle_text_to_speech_tool,
            self.list_files_in_directory_tool,
            self.open_image_from_path_tool,
        ]

        # Add art tools if enabled
        if AIRUNNER_ART_ENABLED:
            tools.extend(
                [
                    self.generate_image_tool,
                    self.clear_canvas_tool,
                    self.set_working_width_and_height,
                ]
            )

        # Add data scraping tools if chat mode is enabled
        if self.chat_mode_enabled:
            tools.extend(
                [
                    self.information_scraper_tool,
                    self.store_user_tool,
                ]
            )

        # Add RAG tools if enabled
        if self.rag_mode_enabled:
            tools.extend(
                [
                    self.rag_engine_tool,
                ]
            )

        return tools

    @property
    def react_tool_agent(self) -> ReActAgentTool:
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
        if not self._streaming_stopping_criteria:
            self._streaming_stopping_criteria = (
                ExternalConditionStoppingCriteria(self.do_interrupt_process)
            )
        return self._streaming_stopping_criteria

    @property
    def chat_engine(self) -> RefreshSimpleChatEngine:
        if not self._chat_engine:
            self.logger.info("Loading RefreshSimpleChatEngine")
            try:
                self._chat_engine = RefreshSimpleChatEngine.from_defaults(
                    system_prompt=self.system_prompt,
                    memory=self.chat_memory,
                    llm=self.llm,
                )
            except Exception as e:
                self.logger.error(f"Error loading chat engine: {str(e)}")
        return self._chat_engine

    @property
    def update_user_data_engine(self) -> RefreshSimpleChatEngine:
        if not self._update_user_data_engine:
            self.logger.info("Loading UpdateUserDataEngine")
            self._update_user_data_engine = (
                RefreshSimpleChatEngine.from_defaults(
                    system_prompt=self._update_user_data_prompt,
                    memory=None,
                    llm=self.llm,
                )
            )
        return self._update_user_data_engine

    @property
    def mood_engine(self) -> RefreshSimpleChatEngine:
        if not self._mood_engine:
            self.logger.info("Loading MoodEngine")
            self._mood_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._mood_update_prompt,
                memory=None,
                llm=self.llm,
            )
        return self._mood_engine

    @property
    def summary_engine(self) -> RefreshSimpleChatEngine:
        if not self._summary_engine:
            self.logger.info("Loading Summary Engine")
            self._summary_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._summarize_conversation_prompt,
                memory=None,
                llm=self.llm,
            )
        return self._summary_engine

    @property
    def information_scraper_engine(self) -> RefreshSimpleChatEngine:
        if not self._information_scraper_engine:
            self.logger.info("Loading information scraper engine")
            self._information_scraper_engine = (
                RefreshSimpleChatEngine.from_defaults(
                    system_prompt=self._information_scraper_prompt,
                    memory=None,
                    llm=self.llm,
                )
            )
        return self._information_scraper_engine

    @property
    def mood_engine_tool(self) -> ChatEngineTool:
        if not self._mood_engine_tool:
            self.logger.info("Loading MoodEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load MoodEngineTool: Chat engine must be provided."
                )
            self._mood_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.mood_engine, agent=self, return_direct=True
            )
        return self._mood_engine_tool

    @property
    def update_user_data_tool(self) -> ChatEngineTool:
        if not self._update_user_data_tool:
            self.logger.info("Loading UpdateUserDataTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load UpdateUserDataTool: Chat engine must be provided."
                )
            self._update_user_data_tool = ChatEngineTool.from_defaults(
                chat_engine=self.update_user_data_engine,
                agent=self,
                return_direct=True,
            )
        return self._update_user_data_tool

    @property
    def summary_engine_tool(self) -> ChatEngineTool:
        if not self._summary_engine_tool:
            self.logger.info("Loading summary engine tool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load summary engine tool: Chat engine must be provided."
                )
            self._summary_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.summary_engine, agent=self, return_direct=True
            )
        return self._summary_engine_tool

    @property
    def chat_engine_tool(self) -> ChatEngineTool:
        if not self._chat_engine_tool:
            self.logger.info("Loading ChatEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load ChatEngineTool: Chat engine must be provided."
                )
            self._chat_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine, agent=self, return_direct=True
            )
        return self._chat_engine_tool

    @property
    def chat_engine_react_tool(self) -> ChatEngineTool:
        if not self._chat_engine_tool:
            self.logger.info("Loading ChatEngineTool")
            if not self.chat_engine:
                raise ValueError(
                    "Unable to load ChatEngineTool: Chat engine must be provided."
                )
            self._chat_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine,
                agent=self,
                return_direct=True,
                do_handle_response=False,
            )
        return self._chat_engine_tool

    @property
    def do_interrupt(self) -> bool:
        return self._do_interrupt

    @do_interrupt.setter
    def do_interrupt(self, value: bool):
        self._do_interrupt = value

    @property
    def bot_mood(self) -> str:
        mood = None
        conversation = self.conversation
        if conversation:
            mood = conversation.bot_mood
        return "neutral" if mood is None or mood == "" else mood

    @bot_mood.setter
    def bot_mood(self, value: str):
        if self.conversation:
            self._update_conversation("bot_mood", value)
            self.api.llm.chatbot.update_mood(value)

    @property
    def conversation(self) -> Optional[Conversation]:
        if not self.use_memory:
            return None
        if not self._conversation:
            self.conversation = self._create_conversation()
        return self._conversation

    @conversation.setter
    def conversation(self, value: Optional[Conversation]):
        self._conversation = value
        if value and self.conversation_id != value.id:
            self.chat_memory.chat_store_key = str(value.id)
            self._conversation_id = value.id
        self._user = None
        self._chatbot = None

    @property
    def conversation_id(self) -> int:
        if not self.use_memory:
            return ""
        conversation_id = self._conversation_id
        if not conversation_id and self._conversation:
            self._conversation_id = self._conversation.id
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, value: int):
        if value != self._conversation_id:
            self._conversation_id = value
            if (
                self.conversation
                and self.conversation.id != self._conversation_id
            ):
                self.conversation = None

    @property
    def bot_personality(self) -> str:
        return self.chatbot.bot_personality

    @property
    def botname(self) -> str:
        return self.chatbot.botname

    @property
    def username(self) -> str:
        return self.user.username

    @property
    def zipcode(self) -> str:
        return self.user.zipcode

    @property
    def location_display_name(self) -> str:
        return self.user.location_display_name

    @location_display_name.setter
    def location_display_name(self, value: str):
        self.user.location_display_name = value

    @property
    def day_of_week(self) -> str:
        return datetime.datetime.now().strftime("%A")

    @property
    def current_date(self) -> str:
        return datetime.datetime.now().strftime("%A %B %d %Y")

    @property
    def current_time(self) -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    @property
    def timezone(self) -> str:
        return datetime.datetime.now().astimezone().tzname()

    @property
    def _information_scraper_prompt(self) -> str:
        prompt = (
            "You are an information scraper. You will examine a given text and extract relevant information from it.\n"
            "You must take into account the context of the text, the subject matter, and the tone of the text.\n"
            f"Find any information about {self.username} which seems relevant, interesting, important, informative, "
            f"or useful.\n"
            f"Find anything that can be used to understand {self.username} better. {self.username} is the user in "
            f"the conversation.\n"
            "Find any likes, dislikes, interests, hobbies, relatives, information about spouses, pets, friends, family "
            "members, or any other information that seems relevant.\n"
            "You will extract this information and provide a brief summary of it.\n"
        )
        return prompt

    @property
    def _summarize_conversation_prompt(self) -> str:
        prompt = (
            "You are a conversation summary writer. You will examine a given conversation and write an appropriate "
            "summary for it.\n"
            "You must take into account the context of the conversation, the subject matter, and the tone of "
            "the conversation.\n"
            "You must also consider the mood of the chatbot and the user.\n"
            "Your summaries will be no more than a few sentences long.\n"
        )
        return prompt

    @property
    def _mood_update_prompt(self) -> str:
        prompt = (
            f"You are a mood analyzier. You are examining a conversation between {self.username} and {self.botname}.\n"
            f"{self.username} is a human and {self.botname} is a chatbot.\n"
            f"Based on the given conversation, you must determine what {self.botname}'s mood is.\n"
            f"You must describe {self.botname}'s mood in one or two sentences.\n"
            f"You must take into account {self.botname}'s personality and the context of the conversation.\n"
            f"You must try to determine the sentiment behind {self.username}'s words. You should also take into "
            f"account {self.botname}'s current mood before "
            f"determining what {self.botname}'s new mood is.\n"
            "You must also consider the subject matter of the conversation and the tone of the conversation.\n"
            "Determine what {self.botname}'s mood is and why then provide a brief explanation.\n"
        )
        return prompt

    @property
    def system_prompt(self) -> str:
        system_instructions = ""
        guardrails = ""
        if (
            self.chatbot.use_system_instructions
            and self.chatbot.system_instructions
            and self.chatbot.system_instructions != ""
        ):
            system_instructions = f"Always follow these instructions:\n{self.chatbot.system_instructions}\n"
        if (
            self.chatbot.use_guardrails
            and self.chatbot.guardrails_prompt
            and self.chatbot.guardrails_prompt != ""
        ):
            guardrails = f"Always follow these guardrails:\n{self.chatbot.guardrails_prompt}\n"
        backstory_prompt = ""
        if (
            self.chatbot.use_backstory
            and self.chatbot.backstory
            and self.chatbot.backstory != ""
        ):
            backstory_prompt = (
                "------\n"
                f"**Here is {self.botname}'s backstory:**\n"
                f"{self.chatbot.backstory}\n"
                "------\n"
            )
        section_prompt = ""
        if self.conversation is not None:
            conversation_timestamp_prompt = (
                f"The conversation started on {self.conversation.timestamp}.\n"
            )
        else:
            conversation_timestamp_prompt = ""
        prompt = (
            f"Your name is {self.botname}.\n"
            f"- The user ({self.username}) is having a conversation with the assistant ({self.botname}).\n"
            "**Here are the rules that you must always remember:**\n"
            "- You will ONLY generate dialogue, nothing more.\n"
            "- Only generate responses in pure dialogue form without including any actions, descriptions or stage "
            "directions in parentheses. Only return spoken words.\n"
            "- Do not generate redundant dialogue. Examine the conversation and context close and keep responses "
            "interesting and creative.\n"
            "- Do not format the response with the character's name or any other text. Only return the dialogue.\n"
            f"- Never generate dialogue for {self.username}, only for {self.botname}\n"
            f"- Never generate dialogue that has already been said in the conversation.\n"
            f"- {self.botname} and {self.username} are both humans. They are not AI or bots.\n"
            f"- As {self.botname}, you will always respond in a way that is consistent with {self.botname}'s emotions, "
            f"personality, and the context of the conversation.\n"
            f"- Generate emotional, persuasive, and realistic responses.\n"
            f"- Do not generate text asking how to provide assistance, or how to can help.\n"
            f"- Generate dialogue that is realistic for the {self.botname} character.\n"
            f"- The generate dialogue can contain questions, make statements, and provide information.\n"
            f"- Generated dialogue should be consistent with {self.botname}'s personality and mood.\n"
            f"- Don't try to change the subject. Stick to the current conversation.\n"
            f"{backstory_prompt}"
            f"{system_instructions}"
            f"{guardrails}"
            # f"{self.conversation_summaries}"
            "------\n"
            "**Here is more context that you can use to generate a response:**\n"
            f"{self.date_time_prompt}"
            f"{self.personality_prompt}"
            f"{self.mood_prompt}"
            f"{self.operating_system_prompt}"
            f"{self.speakers_prompt}"
            f"{self.weather_prompt}"
            f"{self.conversation_summary_prompt}"
            f"------\n"
            "**More information about the current conversation:**\n"
            f"The conversation is between user ({self.username}) and assistant ({self.botname}).\n"
            f"{conversation_timestamp_prompt}"
            f"{section_prompt}"
        )
        prompt = prompt.replace("{{ username }}", self.username)
        prompt = prompt.replace("{{ botname }}", self.botname)
        prompt = prompt.replace("{{ speaker_name }}", self.username)
        prompt = prompt.replace("{{ listener_name }}", self.botname)
        return prompt

    @property
    def _update_user_data_prompt(self) -> str:
        prompt = (
            f"You are to examine the conversation between the user ({self.username} and the chatbot assistant "
            f"({self.botname}).\n"
            f"You are to determine what information about the user ({self.username}) is relevant, interesting, "
            f"important, informative, or useful.\n"
            f"You are to find anything that can be used to understand the user ({self.username}) better.\n"
            f"You are to find any likes, dislikes, interests, hobbies, relatives, information about spouses, pets, "
            f"friends, family members, or any other information that seems relevant.\n"
            f"You are to extract this information and provide a brief summary of it.\n"
        )
        return prompt

    @property
    def react_agent_prompt(self) -> str:
        return f"{self.system_prompt}\n"

    @property
    def chat_store(self) -> Type[BaseChatStore]:
        if not self._chat_store:
            if AIRUNNER_LLM_CHAT_STORE == "db" and self.use_memory:
                self._chat_store = DatabaseChatStore()
            else:
                self._chat_store = SimpleChatStore()
        return self._chat_store

    @chat_store.setter
    def chat_store(self, value: Optional[Type[BaseChatStore]]):
        self._chat_store = value

    @property
    def chat_memory(self) -> Optional[ChatMemoryBuffer]:
        if not self._chat_memory:
            self.logger.info("Loading ChatMemoryBuffer")
            self._chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                chat_store=self.chat_store,
                chat_store_key=str(self.conversation_id),
            )
        return self._chat_memory

    @chat_memory.setter
    def chat_memory(self, value: Optional[ChatMemoryBuffer]):
        self._chat_memory = value

    def _llm_updated(self):
        pass

    def on_web_browser_page_html(self, content: str):
        self.webpage_html = content

    def on_delete_messages_after_id(self):
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
    ):
        self.chat_engine_tool.update_system_prompt(
            system_prompt or self.system_prompt
        )

        if self.rag_mode_enabled:
            self.update_rag_system_prompt(rag_system_prompt)

    def _perform_analysis(self, action: LLMActionType):
        """
        Perform analysis on the conversation.

        Analysis is now performed more sparingly based on message count thresholds
        and time elapsed since last analysis to reduce performance impact.
        """
        if action not in (LLMActionType.CHAT,):
            return

        if not self.llm_settings.llm_perform_analysis:
            return

        # Check if we have a conversation to analyze
        conversation = self.conversation
        if (
            not conversation
            or not conversation.value
            or len(conversation.value) == 0
        ):
            return

        total_messages = len(conversation.value)
        # Don't analyze if there are too few messages
        if total_messages < 3:
            return

        # Track last analysis timestamp in conversation
        last_analysis_time = conversation.last_analysis_time
        current_time = datetime.datetime.now()

        # Set a minimum time between analyses (e.g., 5 minutes)
        min_time_between_analysis = datetime.timedelta(minutes=5)
        if (
            last_analysis_time
            and (current_time - last_analysis_time) < min_time_between_analysis
        ):
            self.logger.info("Skipping analysis: too soon since last analysis")
            return

        # Check message threshold since last analysis
        last_analyzed_message_id = conversation.last_analyzed_message_id or 0
        if (
            total_messages - last_analyzed_message_id
        ) < 10:  # Minimum 10 new messages
            self.logger.info("Skipping analysis: not enough new messages")
            return

        self.logger.info("Performing analysis")

        self._update_system_prompt()

        # Update conversation tracking fields
        self._update_conversation("last_analysis_time", current_time)
        self._update_conversation(
            "last_analyzed_message_id", total_messages - 1
        )

        if self.llm_settings.use_chatbot_mood and self.chatbot.use_mood:
            self._update_mood()

        if self.llm_settings.update_user_data_enabled:
            self._update_user_data()

    def _update_llm_request(self, llm_request: Optional[LLMRequest]):
        self.llm_request = llm_request
        if hasattr(self.llm, "llm_request"):
            self.llm_request = llm_request

    def _update_memory_settings(self):
        if (
            type(self.chat_store) is DatabaseChatStore and not self.use_memory
        ) or (type(self.chat_store) is SimpleChatStore and self.use_memory):
            self.chat_memory = None
            self.chat_store = None
        self.chat_engine._memory = self.chat_memory
        self.chat_engine_tool.chat_engine = self.chat_engine

    def _perform_tool_call(self, action: LLMActionType, **kwargs):
        if action is LLMActionType.CHAT:
            tool_name = "chat_engine_tool"
            tool_agent = self.chat_engine_tool
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            tool_name = "rag_engine_tool"
            tool_agent = self.rag_engine_tool
        elif action is LLMActionType.STORE_DATA:
            tool_name = "store_user_tool"
            tool_agent = self.react_tool_agent
            kwargs["tool_choice"] = tool_name
        elif action is LLMActionType.APPLICATION_COMMAND:
            tool_name = "react_tool_agent"
            tool_agent = self.react_tool_agent
            kwargs["tool_choice"] = tool_name
        elif action is LLMActionType.GENERATE_IMAGE:
            tool_name = "generate_image_tool"
            tool_agent = self.react_tool_agent
            kwargs["tool_choice"] = tool_name
        else:
            return

        self.logger.info(f"Performing call with tool {tool_name}")

        response = tool_agent.call(**kwargs)

        self.logger.info(f"Handling response from {tool_name}")

        if tool_name == "rag_engine_tool":
            self._handle_rag_engine_tool_response(response, **kwargs)
        else:
            self.logger.debug(f"Todo: handle {tool_name} response")

    def _strip_previous_messages_from_conversation(self):
        """
        Strips the previous messages from the conversation.
        """
        conversation = self.conversation
        if conversation:
            Conversation.objects.update(
                self.conversation_id, value=conversation.value[:-2]
            )

    def _update_memory(self, action: LLMActionType):
        memory = None
        if action is LLMActionType.CHAT:
            memory = self.chat_engine.memory if self.chat_engine else None
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            memory = self.rag_engine.memory if self.rag_engine else None
        elif action is LLMActionType.APPLICATION_COMMAND:
            memory = (
                self.react_tool_agent.chat_engine.memory
                if self.react_tool_agent
                else None
            )
        self._memory = memory

    def _update_mood(self):
        self.logger.info("Attempting to update mood")
        conversation = self.conversation
        if (
            not conversation
            or not conversation.value
            or len(conversation.value) == 0
        ):
            self.logger.info("No conversation found")
            return
        total_messages = len(conversation.value)
        last_updated_message_id = conversation.last_updated_message_id
        if last_updated_message_id is None:
            last_updated_message_id = 0
        latest_message_id = total_messages - 1
        if last_updated_message_id == latest_message_id:
            self.logger.info("No new messages")
            return
        if (
            latest_message_id - last_updated_message_id
            < self.llm_settings.update_mood_after_n_turns
        ):
            self.logger.info("Not enough messages")
            return
        self.logger.info("Updating mood")
        start_index = last_updated_message_id
        chat_history = self._memory.get_all() if self._memory else None
        if not chat_history:
            messages = conversation.value
            chat_history = [
                ChatMessage(
                    role=message["role"],
                    blocks=message["blocks"],
                )
                for message in messages
            ]
        chat_history = chat_history[start_index:]
        kwargs = {
            "input": f"What is {self.botname}'s mood based on this conversation?",
            # "chat_history": chat_history,
        }
        response = self.mood_engine_tool.call(do_not_display=True, **kwargs)
        self.logger.info(f"Saving conversation with mood: {response.content}")
        Conversation.objects.update(
            self.conversation_id,
            bot_mood=response.content,
            value=conversation.value[:-2],
            last_updated_message_id=latest_message_id,
        )

    def _update_user_data(self):
        self.logger.info("Attempting to update user preferences")
        conversation = self.conversation
        self.logger.info("Updating user preferences")
        chat_history = self._memory.get_all() if self._memory else None
        if not chat_history:
            messages = conversation.value
            chat_history = [
                ChatMessage(
                    role=message["role"],
                    blocks=message["blocks"],
                )
                for message in (messages or [])
            ]
        kwargs = {
            "input": f"Extract concise, one-sentence summaries of relevant information about {self.username} from this conversation.",
            # "chat_history": chat_history,
        }
        response = self.update_user_data_tool.call(
            do_not_display=True, **kwargs
        )
        if response.content.strip():
            self.logger.info("Updating user with new information")
            concise_summary = response.content.strip().split("\n")[
                :5
            ]  # Limit to 5 concise summaries
            Conversation.objects.update(
                self.conversation_id,
                user_data=concise_summary
                + (self.conversation.user_data or []),
            )
        else:
            self.logger.info("No meaningful information to update.")

    def _summarize_conversation(self):
        if (
            not self.llm_settings.perform_conversation_summary
            or not self.do_summarize_conversation
        ):
            return

        conversation = self.conversation
        if (
            not conversation
            or not conversation.value
            or len(conversation.value) == 0
        ):
            return

        self.logger.info("Summarizing conversation")
        chat_history = self._memory.get_all() if self._memory else None
        if not chat_history:
            messages = conversation.value
            chat_history = [
                ChatMessage(
                    role=message["role"],
                    blocks=message["blocks"],
                )
                for message in messages
            ]
        response = self.summary_engine_tool.call(
            do_not_display=True,
            input="Provide a brief summary of this conversation",
            # chat_history=chat_history,
        )
        self.logger.info(
            f"Saving conversation with summary: {response.content}"
        )
        Conversation.objects.update(
            self.conversation_id,
            summary=response.content,
            value=conversation.value[:-2],
        )

    def _log_system_prompt(
        self, action, system_prompt, rag_system_prompt, llm_request
    ):
        if self.llm_settings.print_llm_system_prompt:
            if action is LLMActionType.PERFORM_RAG_SEARCH:
                self.logger.info(
                    "RAG SYSTEM PROMPT:\n" + (rag_system_prompt or "")
                )
            else:
                self.logger.info("SYSTEM PROMPT:\n" + (system_prompt or ""))
            self.logger.info(llm_request.to_dict())

    def _scrape_information(self, message: str):
        self.logger.info("Attempting to scrape information")
        self.react_tool_agent.call(
            tool_choice="information_scraper_tool",
            input=message,
            # chat_history=self._memory.get_all() if self._memory else None,
        )

    def _create_conversation(self) -> Conversation:
        conversation = None
        if self.conversation_id:
            self.logger.info(
                f"Loading conversation with ID: {self.conversation_id}"
            )
            conversation = Conversation.objects.get(self.conversation_id)

        if not conversation:
            self.logger.info("No conversation found, looking for most recent")
            conversation = Conversation.most_recent()

        if not conversation:
            self.logger.info("Creating new conversation")
            conversation = Conversation.create()

        return conversation

    def _update_conversation(self, key: str, value: Any):
        if self.conversation:
            setattr(self.conversation, key, value)
            Conversation.objects.update(self.conversation_id, **{key: value})

    def _update_user(self, key: str, value: Any):
        setattr(self.user, key, value)
        self.user.save()

    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        **kwargs,
    ) -> AgentChatResponse:
        self.action = action
        # system_prompt = system_prompt or self.system_prompt
        system_prompt = self.system_prompt
        self._chat_prompt = message
        self._complete_response = ""
        self.do_interrupt = False
        self._update_memory(action)
        kwargs = kwargs or {}
        kwargs.update(
            {
                "input": f"{self.username}: {message}",
                # "chat_history": (
                #     self._memory.get_all() if self._memory else None
                # ),
                "llm_request": llm_request,
            }
        )
        self._perform_analysis(action)
        self._summarize_conversation()
        self._log_system_prompt(
            action, system_prompt, rag_system_prompt, llm_request
        )
        self._update_system_prompt(system_prompt, rag_system_prompt)
        self._update_llm_request(llm_request)
        self._update_memory_settings()
        self._perform_tool_call(action, **kwargs)
        return AgentChatResponse(response=self._complete_response)

    # def chat(
    #     self,
    #     message: str,
    #     action: LLMActionType = LLMActionType.CHAT,
    #     system_prompt: Optional[str] = None,
    #     rag_system_prompt: Optional[str] = None,
    #     llm_request: Optional[LLMRequest] = None,
    #     **kwargs,
    # ) -> AgentChatResponse:
    #     kwargs = kwargs or {}
    #     kwargs.update(
    #         {
    #             "input": message,
    #             "chat_history": [],
    #             "llm_request": llm_request,
    #         }
    #     )
    #     self._chat_prompt = message
    #     print("CALLING PERFORM TOOL CALL WITH", action, kwargs)
    #     self._update_system_prompt(system_prompt, rag_system_prompt)
    #     self._update_llm_request(llm_request)
    #     self._perform_tool_call(action, **kwargs)
    #     return AgentChatResponse(response=self._complete_response)

    def on_load_conversation(self, data: Optional[Dict] = None):
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        self.conversation = Conversation.objects.get(conversation_id)

    def on_conversation_deleted(self, data: Optional[Dict] = None):
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        if (
            conversation_id == self.conversation_id
            or self.conversation_id is None
        ):
            self.conversation = None
            self.conversation_id = None
            self.reset_memory()

    def clear_history(self, data: Optional[Dict] = None):
        data = data or {}
        conversation_id = data.get("conversation_id", None)

        self.conversation_id = conversation_id

        self.reset_memory()

    def reset_memory(self):
        self.chat_memory = None
        self.chat_store = None
        messages = self.chat_store.get_messages(key=str(self.conversation_id))
        self.chat_memory.set(messages)
        self.chat_engine.memory = self.chat_memory
        self.react_tool_agent.memory = self.chat_memory
        self.reload_rag_engine()

    def save_chat_history(self):
        pass

    def interrupt_process(self):
        self.do_interrupt = True

    def do_interrupt_process(self):
        if self.do_interrupt:
            self.api.send_llm_text_streamed_signal(
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
    ):
        if response != self._complete_response and not do_not_display:
            self.api.send_llm_text_streamed_signal(
                LLMResponse(
                    message=response,
                    is_first_message=is_first_message,
                    is_end_of_message=is_last_message,
                    name=self.botname,
                    node_id=self.llm_request.node_id,
                )
            )
        self._complete_response += response
