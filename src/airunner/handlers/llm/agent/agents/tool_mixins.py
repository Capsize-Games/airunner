"""
Mixins for tool definitions for BaseAgent and related agents.
"""

from typing import Annotated, Optional, Any
import os
from llama_index.core.tools import FunctionTool
from airunner.enums import GeneratorSection, ImagePreset, SignalCode
from airunner.settings import AIRUNNER_LLM_CHAT_STORE
from airunner.handlers.llm.storage.chat_store import DatabaseChatStore
from llama_index.core.storage.chat_store import SimpleChatStore
from airunner.handlers.llm.agent.memory import ChatMemoryBuffer
from airunner.data.models import Conversation
from airunner.data.models import User
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm import HuggingFaceLLM
from llama_index.core.llms.llm import LLM
from typing import Type


class ToolSingletonMixin:
    """Provides a DRY singleton property helper for tool/engine mixins."""

    def _get_or_create_singleton(self, attr_name, factory, *args, **kwargs):
        if not hasattr(self, attr_name) or getattr(self, attr_name) is None:
            setattr(self, attr_name, factory(*args, **kwargs))
        return getattr(self, attr_name)


class ImageToolsMixin(ToolSingletonMixin):
    """Mixin for image-related tools."""

    @property
    def set_working_width_and_height(self):
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
    def generate_image_tool(self):
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
                if width % 64 != 0:
                    width = (width // 64) * 64
                if height % 64 != 0:
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
    def clear_canvas_tool(self):
        def clear_canvas() -> str:
            self.api.art.canvas.clear()
            return "Canvas cleared."

        return self._get_or_create_singleton(
            "_clear_canvas_tool",
            FunctionTool.from_defaults,
            clear_canvas,
            return_direct=True,
        )

    @property
    def open_image_from_path_tool(self):
        def open_image_from_path(
            image_path: Annotated[
                str,
                ("The path to the image file. Must be a valid file path."),
            ],
        ) -> str:
            if not os.path.isfile(image_path):
                return f"Unable to open image: {image_path} does not exist."
            self.api.art.canvas.image_from_path(image_path)
            return "Opening image..."

        return self._get_or_create_singleton(
            "_open_image_from_path_tool",
            FunctionTool.from_defaults,
            open_image_from_path,
            return_direct=True,
        )


class ConversationToolsMixin(ToolSingletonMixin):
    """Mixin for conversation-related tools."""

    @property
    def clear_conversation_tool(self):
        def clear_conversation() -> str:
            self.api.llm.clear_history()
            return "Conversation cleared."

        return self._get_or_create_singleton(
            "_clear_conversation_tool",
            FunctionTool.from_defaults,
            clear_conversation,
            return_direct=True,
        )


class SystemToolsMixin(ToolSingletonMixin):
    """Mixin for system and file tools."""

    @property
    def quit_application_tool(self):
        def quit_application() -> str:
            self.api.quit_application()
            return "Quitting application..."

        return self._get_or_create_singleton(
            "_quit_application_tool",
            FunctionTool.from_defaults,
            quit_application,
            return_direct=True,
        )

    @property
    def toggle_text_to_speech_tool(self):
        def toggle_text_to_speech(
            enabled: Annotated[
                bool,
                (
                    "Enable or disable text to speech. "
                    "Must be 'True' or 'False'."
                ),
            ],
        ) -> str:
            self.api.tts.toggle(enabled)
            return "Text to speech toggled."

        return self._get_or_create_singleton(
            "_toggle_text_to_speech_tool",
            FunctionTool.from_defaults,
            toggle_text_to_speech,
            return_direct=True,
        )

    @property
    def list_files_in_directory_tool(self):
        def list_files_in_directory(
            directory: Annotated[
                str,
                (
                    "The directory to search in. "
                    "Must be a valid directory path."
                ),
            ],
        ) -> str:
            os_path = os.path.abspath(directory)
            if not os.path.isdir(os_path):
                return "Invalid directory path."
            if not os.path.exists(os_path):
                return "Directory does not exist."
            return os.listdir(os_path)

        return self._get_or_create_singleton(
            "_list_files_in_directory_tool",
            FunctionTool.from_defaults,
            list_files_in_directory,
            return_direct=False,
        )


class UserToolsMixin(ToolSingletonMixin):
    """Mixin for user/information tools."""

    @property
    def information_scraper_tool(self):
        self.logger.info("information_scraper_tool called")

        def scrape_information(tag: str, information: str) -> str:
            self.logger.info(f"Scraping information for tag: {tag}")
            self.logger.info(f"Information: {information}")
            self._update_user(tag, information)
            data = self.user.data or {}
            data[tag] = (
                [information] if tag not in data else data[tag] + [information]
            )
            self._update_user("data", data)
            return "Information scraped."

        return self._get_or_create_singleton(
            "_information_scraper_tool",
            FunctionTool.from_defaults,
            scrape_information,
            return_direct=True,
        )

    @property
    def store_user_tool(self):
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
            data = self.user.data or {}
            data[category] = (
                [information]
                if category not in data
                else data[category] + [information]
            )
            self._update_user(category, information)
            return "User information updated."

        return self._get_or_create_singleton(
            "_store_user_tool",
            FunctionTool.from_defaults,
            store_user_information,
            return_direct=True,
        )


class MemoryManagerMixin:
    """
    Mixin for managing chat memory and chat store logic.
    """

    @property
    def chat_store(self):
        if not hasattr(self, "_chat_store") or self._chat_store is None:
            if AIRUNNER_LLM_CHAT_STORE == "db" and self.use_memory:
                self._chat_store = DatabaseChatStore()
            else:
                self._chat_store = SimpleChatStore()
        return self._chat_store

    @chat_store.setter
    def chat_store(self, value):
        self._chat_store = value

    @property
    def chat_memory(self):
        if not hasattr(self, "_chat_memory") or self._chat_memory is None:
            self.logger.info("Loading ChatMemoryBuffer")
            self._chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                chat_store=self.chat_store,
                chat_store_key=str(self.conversation_id),
            )
        return self._chat_memory

    @chat_memory.setter
    def chat_memory(self, value):
        self._chat_memory = value

    def reset_memory(self):
        self.chat_memory = None
        self.chat_store = None
        # Defensive: check for None before using
        if self.chat_store is not None:
            messages = self.chat_store.get_messages(
                key=str(self.conversation_id)
            )
        else:
            messages = []
        if self.chat_memory is not None:
            self.chat_memory.set(messages)
        # Only set memory if chat_engine is initialized
        if self.chat_engine is not None:
            self.chat_engine.memory = self.chat_memory
        else:
            self.logger.warning(
                "reset_memory: chat_engine is None, cannot set memory."
            )
        if (
            hasattr(self, "react_tool_agent")
            and self.react_tool_agent is not None
        ):
            self.react_tool_agent.memory = self.chat_memory
        self.reload_rag_engine()

    def _update_memory(self, action: str) -> None:
        """
        Update the memory for the given action and ensure all chat engines share the same memory instance.
        Args:
            action (str): The action type to update memory for.
        """
        # Use a custom memory strategy if provided
        if hasattr(self, "_memory_strategy") and self._memory_strategy:
            self._memory = self._memory_strategy(action, self)
        elif action in ("CHAT", "APPLICATION_COMMAND"):
            self.chat_memory.chat_store_key = str(self.conversation_id)
            self._memory = self.chat_memory
        elif action == "PERFORM_RAG_SEARCH":
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


class ConversationManagerMixin:
    """
    Mixin for managing conversation retrieval, creation, updating, and summary logic.
    """

    @property
    def conversation(self) -> Optional[Conversation]:
        if not self.use_memory:
            return None
        if not hasattr(self, "_conversation") or self._conversation is None:
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
        conversation_id = getattr(self, "_conversation_id", None)
        if (
            not conversation_id
            and hasattr(self, "_conversation")
            and self._conversation
        ):
            self._conversation_id = self._conversation.id
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, value: int):
        if value != getattr(self, "_conversation_id", None):
            self._conversation_id = value
            if (
                self.conversation
                and self.conversation.id != self._conversation_id
            ):
                self.conversation = None

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
    def conversation_summary_prompt(self) -> str:
        return (
            f"- Conversation summary:\n{self.conversation.summary}\n"
            if self.conversation and self.conversation.summary
            else ""
        )


class UserManagerMixin:
    """
    Mixin for managing user retrieval and updates.
    """

    @property
    def user(self) -> User:
        # If _user is set by test, always return it
        if hasattr(self, "_user_set_by_test") and getattr(
            self, "_user_set_by_test", False
        ):
            return self._user
        # If _user is set, always return it and never overwrite
        if hasattr(self, "_user") and self._user is not None:
            return self._user
        # Only fetch from DB if _user is not set
        user = None
        if self.conversation:
            user = User.objects.get(self.conversation.user_id)
        if not user:
            user = User.objects.filter_first(
                User.username == getattr(self, "_username", None)
                or getattr(self, "username", None)
            )
        if not user:
            user = User()
            user.save()
        # Only set _user if it was not set before
        if not hasattr(self, "_user") or self._user is None:
            self._user = user
        return self._user

    @user.setter
    def user(self, value: Optional[User]):
        self._user = value
        # Only update conversation if value is not None and has id
        if value is not None and hasattr(value, "id"):
            self._update_conversation("user_id", value.id)

    def _update_user(self, key: str, value):
        setattr(self.user, key, value)
        self.user.save()


class LLMManagerMixin:
    """
    Mixin for managing LLM instantiation, model, and tokenizer logic.
    """

    @property
    def llm_request(self) -> LLMRequest:
        if not hasattr(self, "_llm_request") or self._llm_request is None:
            self._llm_request = LLMRequest.from_default()
        return self._llm_request

    @llm_request.setter
    def llm_request(self, value: LLMRequest):
        self._llm_request = value

    @property
    def llm(self) -> Type[LLM]:
        if not hasattr(self, "_llm") or self._llm is None:
            if (
                hasattr(self, "model")
                and hasattr(self, "tokenizer")
                and self.model
                and self.tokenizer
            ):
                self.logger.info("Loading HuggingFaceLLM")
                self._llm = HuggingFaceLLM(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    streaming_stopping_criteria=getattr(
                        self, "streaming_stopping_criteria", None
                    ),
                )
                self._llm_updated()
            else:
                self.logger.error(
                    "Unable to load HuggingFaceLLM: Model and tokenizer must be provided."
                )
        return self._llm

    @property
    def model(self):
        return getattr(self, "_model", None)

    @model.setter
    def model(self, value):
        self._model = value

    @model.deleter
    def model(self):
        self._model = None

    @property
    def tokenizer(self):
        return getattr(self, "_tokenizer", None)

    @tokenizer.setter
    def tokenizer(self, value):
        self._tokenizer = value

    @tokenizer.deleter
    def tokenizer(self):
        self._tokenizer = None

    def unload_llm(self):
        if hasattr(self, "_llm") and self._llm:
            self._llm.unload()
        self._llm = None
        self._model = None
        self._tokenizer = None


class MoodToolsMixin(ToolSingletonMixin):
    """Mixin for mood-related tools."""

    @property
    def mood_tool(self):
        def set_mood(
            mood_description: Annotated[
                str,
                (
                    "A description of the bot's mood. This should be a short phrase or sentence."
                ),
            ],
            emoji: Annotated[
                str,
                (
                    "An emoji representing the bot's mood. Example: 😊, 😢, 😡, etc."
                ),
            ],
        ) -> str:
            conversation = self.conversation
            if conversation and conversation.value:
                # Update the latest assistant message with mood and emoji
                for msg in reversed(conversation.value):
                    if msg.get("role") == "assistant":
                        msg["bot_mood"] = mood_description
                        msg["bot_mood_emoji"] = emoji
                        break
                Conversation.objects.update(
                    self.conversation_id, value=conversation.value
                )
                self.emit_signal(
                    SignalCode.BOT_MOOD_UPDATED,
                    {"mood": mood_description, "emoji": emoji},
                )
                message = f"Mood set to '{mood_description}' {emoji}."
                self.logger.info(message)
                return message
            message = "No assistant message found to update mood."
            self.logger.warning(message)
            return message

        return self._get_or_create_singleton(
            "_mood_tool",
            FunctionTool.from_defaults,
            set_mood,
            return_direct=True,
        )


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
            self.logger.warning(
                message
            )
            return message

        return self._get_or_create_singleton(
            "_analysis_tool",
            FunctionTool.from_defaults,
            set_analysis,
            return_direct=True,
        )
