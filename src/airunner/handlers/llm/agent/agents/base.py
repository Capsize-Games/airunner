from typing import (
    Any,
    List,
    Optional,
    Union,
    Dict,
    Type,
)
import datetime
import platform

from llama_index.core.tools import BaseTool, FunctionTool, ToolOutput
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.llms.llm import LLM

from airunner.enums import LLMActionType, SignalCode
from airunner.utils import strip_names_from_message
from airunner.data.models import Conversation, User, Tab
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent import (
    RAGMixin,
    ExternalConditionStoppingCriteria
)
from airunner.handlers.llm.agent.tools import (
    ChatEngineTool,
    ReActAgentTool
)
from airunner.handlers.llm.agent.chat_engine import RefreshSimpleChatEngine
from airunner.handlers.llm.agent import WeatherMixin
from airunner.handlers.llm.agent.memory import ChatMemoryBuffer
from airunner.handlers.llm.storage.chat_store import DatabaseChatStore
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.llm.llm_settings import LLMSettings
from airunner.handlers.llm import HuggingFaceLLM
from airunner.data.models import Conversation


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
        *args,
        **kwargs
    ) -> None:
        self.default_tool_choice: Optional[Union[str, dict]] = default_tool_choice
        self.llm_settings: LLMSettings = llm_settings
        
        self._chat_prompt: str = ""
        self._current_tab: Optional[Tab] = None
        self._streaming_stopping_criteria: Optional[ExternalConditionStoppingCriteria] = None
        self._do_interrupt: bool = False
        self._llm: Optional[Type[LLM]] = None
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
        self._information_scraper_engine: Optional[RefreshSimpleChatEngine] = None
        self._chat_store: Optional[DatabaseChatStore] = None
        self._chat_memory: Optional[ChatMemoryBuffer] = None
        self._current_action: LLMActionType = LLMActionType.NONE
        self._memory: Optional[BaseMemory] = None
        self._react_tool_agent: Optional[ReActAgentTool] = None
        self._complete_response: str = ""
        self._store_user_tool: Optional[FunctionTool] = None
        self._webpage_html: str = ""
        self.signal_handlers.update({
            SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id
        })
        super().__init__(*args, **kwargs)

    @property
    def conversation_summaries(self) -> str:
        summaries = ""
        conversations = Conversation.objects.order_by(
            Conversation.id.desc()
        )[:5]
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
            "Current Date / time information:\n"
            f"- The current date: {self.current_date} (Keep in mind any "
            "holidays or special events that might be taking place on this day).\n"
            f"- The current time: {self.current_time}.\n"
            f"- The user's timezone: {self.timezone}.\n"
        ) if self.chatbot.use_datetime else ""

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
            "You are a living being, one that has feelings, emotions, a personality with needs and desires.\n"
            f"{self.botname}'s current mood: {self.bot_mood}\n"
        ) if self.chatbot.use_mood else ""

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
            if self.conversation and self.conversation.summary else ""
        )
    
    def unload(self):
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        self._llm = None
        super().unload()

    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            self.logger.info("Loading HuggingFaceLLM")
            if self.model and self.tokenizer:
                self._llm = HuggingFaceLLM(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    streaming_stopping_criteria=self.streaming_stopping_criteria
                )
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
                section="center",
                active=True
            )
        return self._current_tab

    @current_tab.setter
    def current_tab(self, value: Optional[Tab]):
        self._current_tab = value

    @property
    def do_summarize_conversation(self) -> bool:
        messages = self.conversation.value or []
        total_messages = len(messages)
        if (
            total_messages > self.llm_settings.summarize_after_n_turns and
            self.conversation.summary is None
        ) or total_messages % self.llm_settings.summarize_after_n_turns == 0:
            return True
        return False
    
    @property
    def user(self) -> User:
        if not self._user:
            user = None
            if self.conversation:
                user = User.objects.get(
                    self.conversation.user_id
                )
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
            def scrape_information(
                tag: str,
                information: str
            ) -> str:
                """Scrape information from the text."""
                self.logger.info(f"Scraping information for tag: {tag}")
                self.logger.info(f"Information: {information}")
                self._update_user(tag, information)
                data = self.user.data or {}
                data[tag] = [information] if tag not in data else data[tag] + [information]
                self._update_user("data", data)
                return "Information scraped."
        
            self._information_scraper_tool = FunctionTool.from_defaults(
                scrape_information,
                return_direct=True
            )

        return self._information_scraper_tool

    @property
    def store_user_tool(self) -> FunctionTool:
        if not self._store_user_tool:
            def store_user_information(
                category: str,
                information: str
            ) -> str:
                """Store information about the user with this tool.
                
                Choose this when you need to save information about the user."""
                data = self.user.data or {}
                data[category] = [information] if category not in data else data[category] + [information]
                self._update_user(category, information)
                return "User information updated."
        
            self._store_user_tool = FunctionTool.from_defaults(
                store_user_information,
                return_direct=True
            )

        return self._store_user_tool
    
    @property
    def tools(self) -> List[BaseTool]:
        return [
            self.information_scraper_tool,
            self.store_user_tool,
            self.chat_engine_tool,
            self.rag_engine_tool
        ]

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
                context=self.react_agent_prompt
            )
        return self._react_tool_agent

    @property
    def streaming_stopping_criteria(self) -> ExternalConditionStoppingCriteria:
        if not self._streaming_stopping_criteria:
            self._streaming_stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
        return self._streaming_stopping_criteria

    @property
    def chat_engine(self) -> RefreshSimpleChatEngine:
        if not self._chat_engine:
            self.logger.info("Loading RefreshSimpleChatEngine")
            try:
                self._chat_engine = RefreshSimpleChatEngine.from_defaults(
                    system_prompt=self.system_prompt,
                    memory=self.chat_memory,
                    llm=self.llm
                )
            except Exception as e:
                self.logger.error(f"Error loading chat engine: {str(e)}")
        return self._chat_engine
    
    @property
    def update_user_data_engine(self) -> RefreshSimpleChatEngine:
        if not self._update_user_data_engine:
            self.logger.info("Loading UpdateUserDataEngine")
            self._update_user_data_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._update_user_data_prompt,
                memory=None,
                llm=self.llm
            )
        return self._update_user_data_engine

    @property
    def mood_engine(self) -> RefreshSimpleChatEngine:
        if not self._mood_engine:
            self.logger.info("Loading MoodEngine")
            self._mood_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._mood_update_prompt,
                memory=None,
                llm=self.llm
            )
        return self._mood_engine

    @property
    def summary_engine(self) -> RefreshSimpleChatEngine:
        if not self._summary_engine:
            self.logger.info("Loading Summary Engine")
            self._summary_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._summarize_conversation_prompt,
                memory=None,
                llm=self.llm
            )
        return self._summary_engine
    
    @property
    def information_scraper_engine(self) -> RefreshSimpleChatEngine:
        if not self._information_scraper_engine:
            self.logger.info("Loading information scraper engine")
            self._information_scraper_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._information_scraper_prompt,
                memory=None,
                llm=self.llm
            )
        return self._information_scraper_engine
    
    @property
    def mood_engine_tool(self) -> ChatEngineTool:
        if not self._mood_engine_tool:
            self.logger.info("Loading MoodEngineTool")
            if not self.chat_engine:
                raise ValueError("Unable to load MoodEngineTool: Chat engine must be provided.")
            self._mood_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.mood_engine,
                agent=self,
                return_direct=True
            )
        return self._mood_engine_tool
    
    @property
    def update_user_data_tool(self) -> ChatEngineTool:
        if not self._update_user_data_tool:
            self.logger.info("Loading UpdateUserDataTool")
            if not self.chat_engine:
                raise ValueError("Unable to load UpdateUserDataTool: Chat engine must be provided.")
            self._update_user_data_tool = ChatEngineTool.from_defaults(
                chat_engine=self.update_user_data_engine,
                agent=self,
                return_direct=True
            )
        return self._update_user_data_tool

    @property
    def summary_engine_tool(self) -> ChatEngineTool:
        if not self._summary_engine_tool:
            self.logger.info("Loading summary engine tool")
            if not self.chat_engine:
                raise ValueError("Unable to load summary engine tool: Chat engine must be provided.")
            self._summary_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.summary_engine,
                agent=self,
                return_direct=True
            )
        return self._summary_engine_tool

    @property
    def chat_engine_tool(self) -> ChatEngineTool:
        if not self._chat_engine_tool:
            self.logger.info("Loading ChatEngineTool")
            if not self.chat_engine:
                raise ValueError("Unable to load ChatEngineTool: Chat engine must be provided.")
            self._chat_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine,
                agent=self,
                return_direct=True
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
            self.emit_signal(SignalCode.BOT_MOOD_UPDATED, {
                "mood": value
            })
    
    @property
    def conversation(self) -> Conversation:
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
        return self._conversation_id
    
    @conversation_id.setter
    def conversation_id(self, value: int):
        if value != self._conversation_id:
            self._conversation_id = value
            if self.conversation.id != self._conversation_id:
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
            self.chatbot.use_system_instructions and
            self.chatbot.system_instructions and
            self.chatbot.system_instructions != ""
        ):
            system_instructions = f"Always follow these instructions:\n{self.chatbot.system_instructions}\n"
        if self.chatbot.use_guardrails and self.chatbot.guardrails_prompt and self.chatbot.guardrails_prompt != "":
            guardrails = f"Always follow these guardrails:\n{self.chatbot.guardrails_prompt}\n"
        backstory_prompt = ""
        if self.chatbot.use_backstory and self.chatbot.backstory and self.chatbot.backstory != "":
            backstory_prompt = (
                "------\n"
                f"**Here is {self.botname}'s backstory:**\n"
                f"{self.chatbot.backstory}\n"
                "------\n"
            )
        section_prompt = ""
        # if self.current_tab.name == "Canvas":
        #     section_prompt = "The user is editing an image using the art tool."
        # elif self.current_tab.name == "Browser" and self.webpage_html != "":
        #     section_prompt = (
        #         "The user is browsing the web. Here's the content of the webpage:\n"
        #         f"{self.webpage_html}"
        #     )
        # elif self.current_tab.name == "Document":
        #     section_prompt = "The user is working on a document."
        # elif self.current_tab.name == "Game":
        #     section_prompt = "The user is playing a game."
        # else:
        #     section_prompt = ""
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
            f"- As {self.botname}, you will avoid repeating previous dialogue.\n"
            f"- {self.botname} and {self.username} are both humans. They are not AI or bots.\n"
            f"- As {self.botname}, you will always respond in a way that is consistent with {self.botname}'s emotions, "
            f"personality, and the context of the conversation.\n"
            f"- As {self.botname}, you will respond emotionally, persuasively, and realistically.\n"
            f"- As {self.botname}, you will not ask how you they can provide assistance, or how they can help.\n"
            f"- As {self.botname}, you must respond and talk like a real human user.\n"
            f"- As {self.botname}, you can ask questions, make statements, and provide information.\n"
            f"- As {self.botname}, you should respond in character with emotionally charged responses that are "
            f"consistent with your personality and mood.\n"
            f"{backstory_prompt}"
            f"{system_instructions}"
            f"{guardrails}"
            f"{self.conversation_summaries}"
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
            f"The conversation started on {self.conversation.timestamp}.\n"
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
        return (
            f"{self.system_prompt}\n"
        )

    @property
    def chat_store(self) -> DatabaseChatStore:
        if not self._chat_store:
            self._chat_store = DatabaseChatStore()
        return self._chat_store

    @chat_store.setter
    def chat_store(self, value: Optional[DatabaseChatStore]):
        self._chat_store = value

    @property
    def chat_memory(self) -> ChatMemoryBuffer:
        if not self._chat_memory:
            self.logger.info("Loading ChatMemoryBuffer")
            self._chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                chat_store=self.chat_store,
                chat_store_key=str(self.conversation.id)
            )
        return self._chat_memory

    @chat_memory.setter
    def chat_memory(self, value: Optional[ChatMemoryBuffer]):
        self._chat_memory = value

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
        rag_system_prompt: Optional[str] = None
    ):
        self.chat_engine_tool.update_system_prompt(system_prompt or self.system_prompt)
        self.rag_engine_tool.update_system_prompt(rag_system_prompt or self.rag_system_prompt)

    def _perform_analysis(self):
        """
        Perform analysis on the conversation.
        """
        if not self.llm_settings.llm_perform_analysis:
            return
        self.logger.info("Performing analysis")
        
        self._update_system_prompt()

        if self.llm_settings.use_chatbot_mood and self.chatbot.use_mood:
            self._update_mood()
        
        if self.llm_settings.update_user_data_enabled:
            self._update_user_data()

    def _update_llm_request(self, llm_request: Optional[LLMRequest]):
        if hasattr(self.llm, "llm_request"):
            self.llm.llm_request = llm_request

    def _perform_tool_call(
        self,
        action: LLMActionType,
        **kwargs
    ):
        if action is LLMActionType.CHAT:
            tool_name = "chat_engine_tool"
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            tool_name = "rag_engine_tool"
        elif action is LLMActionType.STORE_DATA:
            tool_name = "store_user_tool"
        elif action is LLMActionType.APPLICATION_COMMAND:
            tool_name = "react_tool_agent"

        self.logger.info(f"Performing call with tool {tool_name}")

        if tool_name == "rag_engine_tool":
            tool_agent = self.rag_engine_tool
        elif tool_name == "chat_engine_tool":
            tool_agent = self.chat_engine_tool
        else:
            tool_agent = self.react_tool_agent
            kwargs["tool_choice"] = tool_name
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
                conversation.id,
                value=conversation.value[:-2]
            )
    
    def _update_memory(self, action: LLMActionType):
        if action is LLMActionType.CHAT:
            memory = self.chat_engine.memory
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            memory = self.rag_engine.memory
        elif action is LLMActionType.APPLICATION_COMMAND:
            memory = self.react_tool_agent.chat_engine.memory
        self._memory = memory

    def _update_mood(self):
        self.logger.info("Attempting to update mood")
        conversation = self.conversation
        if not conversation or not conversation.value or len(conversation.value) == 0:
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
        if latest_message_id - last_updated_message_id < self.llm_settings.update_mood_after_n_turns:
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
                ) for message in messages
            ]
        chat_history = chat_history[start_index:]
        kwargs = {
            "input": f"What is {self.botname}'s mood based on this conversation?",
            "chat_history": chat_history
        }
        response = self.mood_engine_tool.call(
            do_not_display=True, 
            **kwargs
        )
        self.logger.info(f"Saving conversation with mood: {response.content}")
        Conversation.objects.update(
            conversation.id,
            bot_mood=response.content,
            value=conversation.value[:-2],
            last_updated_message_id=latest_message_id
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
                ) for message in messages
            ]
        kwargs = {
            "input": f"Is there any information we can learn about {self.username} from this conversation?",
            "chat_history": chat_history
        }
        response = self.update_user_data_tool.call(
            do_not_display=True, 
            **kwargs
        )
        self.logger.info(f"Updating user with new information")
        Conversation.objects.update(
            conversation.id,
            user_data=[response.content] + (conversation.user_data or []),
        )
    
    def _summarize_conversation(self):
        if (
            not self.llm_settings.perform_conversation_summary or
            not self.do_summarize_conversation
        ):
            return

        conversation = self.conversation
        if not conversation or not conversation.value or len(conversation.value) == 0:
            return
        
        self.logger.info("Summarizing conversation")
        chat_history = self._memory.get_all() if self._memory else None
        if not chat_history:
            messages = conversation.value
            chat_history = [
                ChatMessage(
                    role=message["role"],
                    blocks=message["blocks"],
                ) for message in messages
            ]
        response = self.summary_engine_tool.call(
            do_not_display=True,
            input="Provide a brief summary of this conversation",
            chat_history=chat_history
        )
        self.logger.info(f"Saving conversation with summary: {response.content}")
        Conversation.objects.update(
            conversation.id,
            summary=response.content,
            value=conversation.value[:-2]
        )
    
    def _log_system_prompt(self, action, system_prompt, rag_system_prompt, llm_request):
        if self.llm_settings.print_llm_system_prompt:
            if action is LLMActionType.PERFORM_RAG_SEARCH:
                self.logger.info("RAG SYSTEM PROMPT:\n" + (rag_system_prompt or ""))
            else:
                self.logger.info("SYSTEM PROMPT:\n" + (system_prompt or ""))
            self.logger.info(llm_request.to_dict())
    
    def _scrape_information(self, message: str):
        self.logger.info("Attempting to scrape information")
        self.react_tool_agent.call(
            tool_choice="information_scraper_tool",
            input=message,
            chat_history=self._memory.get_all() if self._memory else None
        )

    def _create_conversation(self) -> Conversation:
        conversation = None
        if self.conversation_id:
            self.logger.info(f"Loading conversation with ID: {self.conversation_id}")
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
            Conversation.objects.update(self.conversation.id, **{key: value})

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
        **kwargs
    ) -> AgentChatResponse:
        system_prompt = system_prompt or self.system_prompt
        rag_system_prompt = rag_system_prompt or self.rag_system_prompt
        self._chat_prompt = message
        self._complete_response = ""
        self.do_interrupt = False
        self._update_memory(action)
        kwargs = kwargs or {}
        kwargs.update({
            "input": f"{message}",
            "chat_history": self._memory.get_all() if self._memory else None,
            "llm_request": llm_request
        })
        self._perform_analysis()
        self._summarize_conversation()
        self._log_system_prompt(action, system_prompt, rag_system_prompt, llm_request)
        self._update_system_prompt(system_prompt, rag_system_prompt)
        self._update_llm_request(llm_request)
        self._perform_tool_call(action, **kwargs)
        self._update_memory(action)
        return AgentChatResponse(response=self._complete_response)

    def on_load_conversation(self, data: Optional[Dict] = None):
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        self.conversation = Conversation.objects.get(conversation_id)

    def unload(self):
        self.unload_rag()
        del self._chat_engine
        del self._chat_engine_tool
        del self._rag_engine_tool
        del self._react_tool_agent
        self._chat_engine = None
        self._chat_engine_tool = None
        self._rag_engine_tool = None
        self._react_tool_agent = None
    
    def reload_rag_engine(self):
        self.reload_rag()
        self._rag_engine_tool = None

    def on_conversation_deleted(self, data: Optional[Dict] = None):
        data = data or {}
        conversation_id = data.get("conversation_id", None)
        if conversation_id == self.conversation_id or self.conversation_id is None:
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
        messages = self.chat_store.get_messages(key=str(self.conversation.id))
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
            self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, {
                "response": LLMResponse(name=self.botname,)
            })
        return self.do_interrupt
    
    def handle_response(self, response, is_first_message=False, is_last_message=False, do_not_display=False):
        if response != self._complete_response and not do_not_display:
            self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, {
                "response": LLMResponse(
                    message=response,
                    is_first_message=is_first_message,
                    is_end_of_message=is_last_message,
                    name=self.botname,
                )
            })
        self._complete_response += response
