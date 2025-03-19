from typing import (
    Optional,
    Type,
)
from PySide6.QtCore import QObject
import platform

from transformers import AutoModelForCausalLM, AutoTokenizer

from llama_index.core.llms.llm import LLM

from airunner.handlers.llm.huggingface_llm import HuggingFaceLLM
from airunner.mediator_mixin import MediatorMixin
from airunner.handlers.llm.agent.weather_mixin import WeatherMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.data.models import Conversation


class MistralAgentQObject(
    MediatorMixin,
    SettingsMixin,
    WeatherMixin,
    BaseAgent,
    QObject,
):
    """QObject wrapper for Mistral Agent"""
    def __init__(
        self, 
        model: Optional[AutoModelForCausalLM] = None,
        tokenizer: Optional[AutoTokenizer] = None,
        *args, 
        **kwargs
    ):
        self.model = model
        self.tokenizer = tokenizer
        super().__init__()
    
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

    def build_system_prompt(self) -> str:
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
    
    def unload(self):
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        self._llm = None
        super().unload()