"""Mistral Agent.

Simple wrapper around AgentRunner + MistralAgentWorker.
"""
import os
from typing import (
    Any,
    List,
    Optional,
    Union,
)
from pydantic import Field
import datetime
import platform
from PySide6.QtCore import QObject
from llama_index.core.tools import BaseTool, FunctionTool
from airunner.handlers.llm.huggingface_llm import HuggingFaceLLM
from llama_index.core.chat_engine.types import AgentChatResponse
from airunner.handlers.llm.agent.chat_engine.refresh_simple_chat_engine import (
    RefreshSimpleChatEngine
)
from llama_index.core.base.llms.types import ChatMessage
from airunner.enums import LLMActionType, SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.data.models.settings_models import Conversation
from airunner.handlers.llm.agent.rag_mixin import RAGMixin
from airunner.handlers.llm.agent.external_condition_stopping_criteria import (
    ExternalConditionStoppingCriteria
)
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool
from airunner.handlers.llm.agent.tools.rag_engine_tool import RAGEngineTool
from airunner.handlers.llm.agent.weather_mixin import WeatherMixin
from airunner.handlers.llm.storage.chat_store.sqlite import SQLiteChatStore
from airunner.handlers.llm.agent.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.memory import BaseMemory
from airunner.handlers.llm.agent.tools.react_agent_tool import ReActAgentTool


DEFAULT_MAX_FUNCTION_CALLS = 5


class MistralAgentQObject(
    QObject,
    MediatorMixin,
    SettingsMixin,
    RAGMixin,
    WeatherMixin
):
    """QObject wrapper for Mistral Agent"""
    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        default_tool_choice: Optional[Union[str, dict]] = None,
        max_function_calls: int = DEFAULT_MAX_FUNCTION_CALLS,
        **kwargs
    ) -> None:
        MediatorMixin.__init__(self)
        RAGMixin.__init__(self)
        self.model = model
        self.tokenizer = tokenizer
        self._do_interrupt: bool = False
        self.history: Optional[List[ChatMessage]] = []
        self._llm: Optional[HuggingFaceLLM] = None
        # self.news_scraper_worker: NewsScraperWorker = create_worker(NewsScraperWorker)
        self._conversation: Optional[Conversation] = None
        self._chat_engine: Optional[RefreshSimpleChatEngine] = None
        self._chat_engine_tool: Optional[ChatEngineTool] = None
        self._rag_engine_tool: Optional[RAGEngineTool] = None
        self._chat_store: Optional[SQLiteChatStore] = None
        self._chat_memory: Optional[ChatMemoryBuffer] = None
        self._current_action: LLMActionType = LLMActionType.NONE
        self._memory: Optional[BaseMemory] = None
        self.load_rag()
        self._react_tool_agent: Optional[ReActAgentTool] = None
        self.default_tool_choice: Optional[Union[str, dict]] = default_tool_choice
        self.max_function_calls: int = max_function_calls
        self._complete_response: str = ""
        super().__init__(**kwargs)

    @property
    def tools(self) -> List[BaseTool]:
        def get_date_and_time(*args, **kwargs) -> str:
            """Get the current date and time."""
            return self._date_time_prompt

        tools = [
            FunctionTool.from_defaults(
                get_date_and_time,
                return_direct=False
            ),
        ]
        return tools + [
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
                max_function_calls=self.max_function_calls,
                default_tool_choice=self.default_tool_choice,
                return_direct=True
            )
        return self._react_tool_agent

    @property
    def llm(self) -> HuggingFaceLLM:
        if not self._llm:
            self._llm = HuggingFaceLLM(
                model=self.model, 
                tokenizer=self.tokenizer,
                streaming_stopping_criteria=ExternalConditionStoppingCriteria(self.do_interrupt_process)
            )
        return self._llm

    @property
    def chat_engine(self) -> RefreshSimpleChatEngine:
        if not self._chat_engine:
            self._chat_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=self._system_prompt,
                memory=self.chat_memory,
                llm=self.llm
            )
        return self._chat_engine
    
    @property
    def chat_engine_tool(self) -> ChatEngineTool:
        if not self._chat_engine_tool:
            self._chat_engine_tool = ChatEngineTool.from_defaults(
                chat_engine=self.chat_engine,
                agent=self
            )
        return self._chat_engine_tool
    
    @property
    def rag_engine_tool(self) -> RAGEngineTool:
        if not self._rag_engine_tool:
            self._rag_engine_tool = RAGEngineTool.from_defaults(
                chat_engine=self.rag_engine,
                agent=self
            )
        return self._rag_engine_tool


    @property
    def do_interrupt(self):
        return self._do_interrupt

    @do_interrupt.setter
    def do_interrupt(self, value):
        self._do_interrupt = value
    
    @property
    def conversation(self) -> Optional[Conversation]:
        if self._conversation is None:
            self.conversation = self.create_conversation()
        return self._conversation
    
    @conversation.setter
    def conversation(self, value: Optional[Conversation]):
        self._conversation = value
    
    @property
    def bot_mood(self) -> str:
        mood = self.conversation.bot_mood
        return "neutral" if mood is None or mood == "" else mood

    @bot_mood.setter
    def bot_mood(self, value: str):
        conversation = self.conversation
        conversation.bot_mood = value
        self.save_object(conversation)
        self.emit_signal(SignalCode.BOT_MOOD_UPDATED, {
            "mood": value
        })
    
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
    def _date_time_prompt(self) -> str:
        return (
            "Current Date / time information:\n"
            f"- Date: {self.current_date}.\n"
            f"- Time: {self.current_time}.\n"
            f"- Timezone: {self.timezone}.\n"
        )
    
    @property
    def _operating_system_prompt(self) -> str:
        return (
            "Operating system information:\n"
            f"- System: {platform.system()}\n"
            f"- Release: {platform.release()}\n"
            f"- Version: {platform.version()}\n"
            f"- Machine: {platform.machine()}\n"
            f"- Processor: {platform.processor()}\n"
        )

    @property
    def _speakers_prompt(self) -> str:
        return (
            "User information:\n"
            f"- Username: {self.username}\n"
            f"- Location: {self.location_display_name}\n"
            "Chatbot information:\n"
            f"- Chatbot name: {self.botname}\n"
            f"- Chatbot mood: {self.bot_mood}\n"
            f"- Chatbot personality: {self.bot_personality}\n"
        )
    
    @property
    def _system_prompt(self) -> str:
        prompt = (
            f"You are a chatbot. Your name is {self.botname} and the "
            f"user's name is {self.username}.\n"
            "Here is more context that you can use to generate a response:\n"
            f"{self._date_time_prompt}"
            f"{self._operating_system_prompt}"
            f"{self._speakers_prompt}"
            f"{self._weather_prompt}"
        )
        prompt = prompt.replace("{{ username }}", self.username)
        prompt = prompt.replace("{{ botname }}", self.botname)
        return prompt
    
    @property
    def _rag_system_prompt(self) -> str:
        prompt = (
            f"You are a chatbot. Your name is {self.botname} and the "
            f"user's name is {self.username}.\n"
            "Search the full text and find all relevant information "
            "related to the query."
            "Here is more context that you can use to generate a response:\n"
            f"{self._date_time_prompt}"
        )
        prompt = prompt.replace("{{ username }}", self.username)
        prompt = prompt.replace("{{ botname }}", self.botname)
        return prompt
    
    @property
    def chat_store(self) -> SQLiteChatStore:
        if not self._chat_store:
            db_path = os.path.expanduser(
                os.path.join(
                    "~",
                    ".local",
                    "share",
                    "airunner",
                    "data",
                    "chat_store.db"
                )
            )
            self._chat_store = SQLiteChatStore.from_uri(f"sqlite:///{db_path}")
        return self._chat_store
    
    @property
    def chat_memory(self) -> ChatMemoryBuffer:
        if not self._chat_memory:
            self._chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                chat_store=self.chat_store,
                chat_store_key="user1"
            )
        return self._chat_memory

    def unload(self):
        self.unload_rag()
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        self.thread = None
        del self._chat_engine
        del self._chat_engine_tool
        del self._rag_engine_tool
        del self._react_tool_agent
        self._chat_engine = None
        self._chat_engine_tool = None
        self._rag_engine_tool = None
        self._react_tool_agent = None
    
    def reload_rag(self):
        self._reload_rag()
        self._rag_engine_tool = None

    def clear_history(self):
        pass

    def query(
        self,
        message: str
    ) -> AgentChatResponse:
        self._complete_response = ""
        response = self.tool_agent.query(message)
        self.handle_response(response.response, is_last_message=True)
    
    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT
    ) -> AgentChatResponse:
        self._complete_response = ""
        self.do_interrupt = False
        self.chat_engine_tool.update_system_prompt(self._system_prompt)
        self.rag_engine_tool.update_system_prompt(self._rag_system_prompt)
        kwargs = {
            "input": message,
            "chat_history": self._memory.get_all() if self._memory else None
        }
        if action is LLMActionType.CHAT:
            self.chat_engine_tool.call(**kwargs)
            self._memory = self.chat_engine._memory
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            self.rag_engine_tool.call(**kwargs)
            self._memory = self.rag_engine._memory
        else:
            self.react_tool_agent.call(**kwargs)
            self._memory = self.react_tool_agent.chat_engine.memory
        
    def save_chat_history(self):
        pass
    
    def interrupt_process(self):
        self.do_interrupt = True
    
    def do_interrupt_process(self):
        if self.do_interrupt:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                dict(
                    message="",
                    is_first_message=False,
                    is_end_of_message=False,
                    name=self.botname,
                    action=LLMActionType.CHAT
                )
            )
        return self.do_interrupt
    
    def handle_response(self, response, is_first_message=False, is_last_message=False):
        if response != self._complete_response:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "message": response,
                    "is_first_message": is_first_message,
                    "is_end_of_message": is_last_message,
                    "name": self.botname,
                    "action": LLMActionType.CHAT
                }
            )
        self._complete_response += response