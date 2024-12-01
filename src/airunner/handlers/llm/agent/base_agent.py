import datetime
import json
import os
import sqlite3
import time
import traceback
from typing import AnyStr
import torch
from PySide6.QtCore import QObject

from llama_index.core import Settings, RAKEKeywordTableIndex
from llama_index.core.base.llms.types import ChatMessage
from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import PromptHelper
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.indices.keyword_table import KeywordTableSimpleRetriever
from transformers import TextIteratorStreamer

from airunner.data.models.settings_models import Conversation
from airunner.handlers.llm.huggingface_llm import HuggingFaceLLM
from airunner.handlers.llm.custom_embedding import CustomEmbedding
from airunner.handlers.llm.agent.html_file_reader import HtmlFileReader
from airunner.handlers.llm.agent.external_condition_stopping_criteria import ExternalConditionStoppingCriteria
from airunner.mediator_mixin import MediatorMixin
from airunner.enums import (
    SignalCode,
    LLMChatRole,
    LLMActionType,
    AgentState
)
from airunner.utils.get_torch_device import get_torch_device
from airunner.utils.create_worker import create_worker
from airunner.utils.prepare_llm_generate_kwargs import prepare_llm_generate_kwargs
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.agent_worker import AgentWorker


class RefreshContextChatEngine(ContextChatEngine):
    def stream_chat(self, *args, system_prompt:str=None, **kwargs):
        if system_prompt:
            self._prefix_messages[0] = ChatMessage(content=system_prompt, role=self._llm.metadata.system_role)
        return super().stream_chat(*args, **kwargs)


class BaseAgent(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)

        self._requested_action = None
        self.model = kwargs.pop("model", None)
        self.__documents = None
        self.__document_reader: SimpleDirectoryReader = None
        self.__index = None
        self.__chat_engine = None
        self.__retriever = None
        self.__storage_context = None
        self.__transformations = None
        self.__index_struct = None
        self.__callback_manager = None
        self.__pdf_reader = None
        self.__epub_reader = None
        self.__html_reader = None
        self.__markdown_reader = None
        self.__embedding = None
        self.__model_name = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text/models",
                "sentence_transformers/sentence-t5-large"
            )
        )
        self.__query_instruction = "Search through all available texts and provide a brief summary of the key points which are relevant to the query."
        self.__text_instruction = "Summarize and provide a brief explanation of the text. Stay concise and to the point."
        self.__state = AgentState.SEARCH
        self.__chunk_size = 1000
        self.__chunk_overlap = 512
        self.__target_files = []
        self.__rag_model = None
        self.__rag_tokenizer = None
        self.__model = None
        self.__tokenizer = None
        self.__llm = None
        self._chatbot = None
        self.action = LLMActionType.CHAT
        self.rendered_template = None
        self.tokenizer = kwargs.pop("tokenizer", None)
        self._streamer = None
        self.chat_template = kwargs.pop("chat_template", "")
        self.is_mistral = kwargs.pop("is_mistral", True)
        self.conversation_id = None
        self.conversation_title = None
        self.conversation = None
        self.history = self.load_history_from_db(self.conversation_id)  # Load history by conversation ID
        super().__init__(*args, **kwargs)
        self.prompt = ""
        self.thread = None
        self._do_interrupt = False
        self.response_worker = create_worker(AgentWorker)
        self.load_rag(model=self.model, tokenizer=self.tokenizer)

    @property
    def do_interrupt(self):
        return self._do_interrupt

    @do_interrupt.setter
    def do_interrupt(self, value):
        self._do_interrupt = value

    @property
    def streamer(self):
        if self._streamer is None:
            self._streamer = TextIteratorStreamer(self.tokenizer)
        return self._streamer

    @property
    def available_actions(self):
        return {
            0: LLMActionType.TOGGLE_FULLSCREEN,
            1: LLMActionType.TOGGLE_TTS,
            2: LLMActionType.GENERATE_IMAGE,
            3: LLMActionType.PERFORM_RAG_SEARCH,
            4: LLMActionType.CHAT,
        }

    @property
    def username(self) -> str:
        return self.user.username

    @property
    def botname(self) -> str:
        return self.chatbot.botname

    @property
    def bot_mood(self) -> str:
        return self.conversation.bot_mood if self.conversation else ""

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
    def override_parameters(self):
        generate_kwargs = prepare_llm_generate_kwargs(self.llm_generator_settings)
        return generate_kwargs if self.llm_generator_settings.override_parameters else {}

    @property
    def system_instructions(self):
        return self.chatbot.system_instructions

    @property
    def generator_settings(self) -> dict:
        return prepare_llm_generate_kwargs(self.chatbot)

    @property
    def device(self):
        return get_torch_device(self.memory_settings.default_gpu_llm)

    @property
    def target_files(self):
        return [
            target_file.file_path for target_file in self.chatbot.target_files
        ]

    @property
    def query_instruction(self):
        if self.__state == AgentState.SEARCH:
            return self.__query_instruction
        elif self.__state == AgentState.CHAT:
            return "Search through the chat history for anything relevant to the query."

    @property
    def text_instruction(self):
        if self.__state == AgentState.SEARCH:
            return self.__text_instruction
        elif self.__state == AgentState.CHAT:
            return "Use the text to respond to the user"

    @property
    def index(self):
        if self.__state == AgentState.SEARCH:
            return self.__index
        elif self.__state == AgentState.CHAT:
            return self.__chat_history_index

    @property
    def llm(self):
        if self.__llm is None:
            try:
                if self.llm_generator_settings.use_api:
                    self.__llm = self.__model
                else:
                    self.__llm = HuggingFaceLLM(model=self.__model, tokenizer=self.__tokenizer)
            except Exception as e:
                self.logger.error(f"Error loading LLM: {str(e)}")
        return self.__llm

    @property
    def chat_engine(self):
        return self.__chat_engine

    @property
    def is_llama_instruct(self):
        return True

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    @property
    def cuda_index(self):
        return 0

    def unload(self):
        self.unload_rag()
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        self.thread = None

    def clear_history(self):
        self.history = []
        self.reload_rag()
        self.conversation_id = None
        self.conversation_title = None

    def _update_conversation_title(self, title):
        self.conversation_title = title
        self.update_conversation_title(self.conversation_id, title)

    def _create_conversation(self):
        # Get the most recent conversation ID
        self.conversation = self.get_most_recent_conversation()
        if not self.conversation:
            self.conversation = self.create_conversation()
        self.conversation_id = self.conversation.id
        self.history = self.load_history_from_db(self.conversation_id)

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

    def mood(self, botname: str, bot_mood: str, use_mood: bool) -> str:
        return (
            f"{botname} is not a computer or a bot, you are a human with emotions. "
            f"{botname}'s mood changes depending on the conversation and other factors.\n"
            f"{botname}'s current mood: {bot_mood}."
            #f"{botname}'s evaluation of {username}: {self.user_evaluation}"
        ) if (use_mood and bot_mood != "") else ""

    def history_prompt(self) -> str:
        history = ""
        previous_date = None
        for message in self.history:
            # Check if the timestamp is a string and convert it to a datetime object if necessary
            if isinstance(message["timestamp"], str):
                current_date = datetime.datetime.strptime(message["timestamp"], "%Y-%m-%d %H:%M:%S").date()
            else:
                current_date = message["timestamp"].date()

            if previous_date is None or current_date != previous_date:
                history += f"\n--- {current_date.strftime('%B %d, %Y')} ---\n"
                previous_date = current_date
            name = ""
            if message["role"] == LLMChatRole.HUMAN.value:
                name = self.username
            elif message["role"] == LLMChatRole.ASSISTANT.value:
                name = self.botname
            history += f"{name}: {message['content']}\n"
        return (
            "------\n"
            "Chat History:\n"
            f"{history}"
        )

    def date_time_prompt(self) -> str:
        if not self.chatbot.use_datetime:
            return ""
        current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        current_timezone = time.tzname
        prompt = [
            "\n======\n",
            f"Use the following information to help you with your response, but do not include it in your response or reference it directly unless asked.",
            f"Date: {current_date}, Time: {current_time}, Timezone: {current_timezone}",
        ]
        return "\n".join(prompt)

    def build_system_prompt(
        self,
        action
    ):
        system_instructions = ""
        guardrails_prompt = ""
        use_mood = self.chatbot.use_mood
        use_personality = self.chatbot.use_personality
        use_names = self.chatbot.assign_names
        use_system_instructions = self.chatbot.use_system_instructions
        use_guardrails = self.chatbot.use_guardrails
        bot_mood = self.bot_mood
        bot_personality = self.chatbot.bot_personality
        username = self.user.username
        botname = self.chatbot.botname
        if use_system_instructions:
            system_instructions = self.chatbot.system_instructions
        if use_guardrails:
            guardrails_prompt = self.chatbot.guardrails_prompt

        system_prompt = []

        if action is LLMActionType.CHAT:
            """
            Build the system prompt for chat template
            """
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
                self.date_time_prompt()
            ]

        elif action is LLMActionType.GENERATE_IMAGE:
            system_prompt = [
                system_instructions,
                self.history_prompt()
            ]

        elif action is LLMActionType.APPLICATION_COMMAND:
            prompt_template = self.get_prompt_template_by_name("application_command")
            system_instructions = prompt_template.system

            # Create a list of commands that the bot can choose from
            for index, action in self.available_actions.items():
                system_instructions += f"{index}: {action.value}\n"

            system_prompt = [
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                system_instructions,
                self.history_prompt(),
            ]

        elif action is LLMActionType.SUMMARIZE:
            prompt_template = self.get_prompt_template_by_name("summarize")
            system_instructions = prompt_template.system
            system_prompt = [
                system_instructions,
                self.history_prompt()
            ]

        elif action is LLMActionType.UPDATE_MOOD:
            prompt_template = self.get_prompt_template_by_name("update_mood")
            system_instructions = prompt_template.system
            system_prompt = [
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            prompt_template = self.get_prompt_template_by_name("rag_search")
            system_instructions = prompt_template.system
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                # self.history_prompt(),
            ]

        elif action is LLMActionType.QUIT_APPLICATION:
            self.emit_signal(SignalCode.QUIT_APPLICATION)

        elif action is LLMActionType.TOGGLE_FULLSCREEN:
            self.emit_signal(SignalCode.TOGGLE_FULLSCREEN_SIGNAL)

        return "\n".join(system_prompt)

    def names_prompt(self, use_names: bool, botname: str, username: str) -> str:
        return f"Your name is {botname}. \nThe user's name is {username}." if use_names else ""

    def personality_prompt(self, bot_personality: str, use_personality: bool) -> str:
        return (
            f"Your personality: {bot_personality}."
        ) if use_personality else ""

    def prepare_messages(
        self,
        action
    ) -> list:
        system_prompt = self.build_system_prompt(action)
        if action is LLMActionType.APPLICATION_COMMAND:
            prompt = (
                "Choose an action from THE LIST of commands for the text above. "
                "Only return the number of the command."
            )
        elif action is LLMActionType.GENERATE_IMAGE:
            prompt = (
                f"Replace the placeholder values in the following JSON:\n"
                "```json\n"+ json.dumps(dict(
                    description="PLACEHOLDER",
                    composition="PLACEHOLDER"
                )) +"\n```\n"
            )
        elif action is LLMActionType.SUMMARIZE:
            prompt = (
                f"Summarize the conversation history"
            )
        else:
            prompt = f"Respond to {self.username}"
        messages = [
            {
                "content": system_prompt,
                "role": LLMChatRole.SYSTEM.value
            },
            {
                "content": prompt,
                "role": LLMChatRole.HUMAN.value
            }
        ]
        return messages

    def get_rendered_template(
        self,
        action: LLMActionType
    ) -> str:
        conversation = self.prepare_messages(action)
        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=self.chat_template,
            conversation=conversation,
            tokenize=False
        )

        # replace variables in chat template
        variables = {
            "speaker_name": self.botname,
            "listener_name": self.username,
            "username": self.username,
            "botname": self.botname,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }
        for key, value in variables.items():
            value = value or ""
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    def run(
        self,
        prompt: str,
        action: LLMActionType,
        **kwargs
    ):
        self._requested_action = None
        self.action = action

        if action is LLMActionType.TOGGLE_TTS:
            self.emit_signal(SignalCode.TOGGLE_TTS_SIGNAL)
            return

        if action in (
            LLMActionType.CHAT,
            LLMActionType.PERFORM_RAG_SEARCH
        ) and (self.conversation_title is None or self.conversation_title == ""):
            self._requested_action = action
            action = LLMActionType.SUMMARIZE

        self.logger.debug("Running...")
        self.prompt = prompt

        if self.conversation_id is None:
            self._create_conversation()
            self.set_conversation_title()

        # Add the user's message to history
        if action not in (
            LLMActionType.APPLICATION_COMMAND,
            LLMActionType.UPDATE_MOOD
        ):
            self.add_message_to_history(
                self.prompt,
                LLMChatRole.HUMAN
            )

        self.rendered_template = self.get_rendered_template(action)

        model_inputs = self.tokenizer(
            self.rendered_template,
            return_tensors="pt"
        ).to(self.device)

        kwargs.update(
            action=action,
            do_emit_response=True
        )

        self.run_with_thread(
            model_inputs,
            **kwargs
        )

    def prepare_generate_data(self, model_inputs, stopping_criteria):
        data = dict(
            **model_inputs,
            **self.generator_settings,
            stopping_criteria=[stopping_criteria]
        )
        data.update(self.override_parameters)
        return data

    def run_with_thread(
        self,
        model_inputs,
        action: LLMActionType,
        **kwargs,
    ):
        with torch.no_grad():
            # Generate the response
            self.logger.debug("Generating...")

            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)

            if self.do_interrupt:
                self.do_interrupt = False

            stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
            data = self.prepare_generate_data(model_inputs, stopping_criteria)

            data["streamer"] = kwargs.get("streamer", self.streamer)

            if action is not LLMActionType.PERFORM_RAG_SEARCH:
                try:
                    self.response_worker.add_to_queue({
                        "model": self.model,
                        "kwargs": data,
                        "prompt": self.prompt,
                        "botname": self.botname,
                    })
                except Exception as e:
                    self.logger.error("545: An error occurred in model.generate:")
                    self.logger.error(str(e))
                    self.logger.error(traceback.format_exc())

            # strip all new lines from rendered_template:
            #self.rendered_template = self.rendered_template.replace("\n", " ")
            eos_token = self.tokenizer.eos_token
            bos_token = self.tokenizer.bos_token
            if self.is_mistral:
                self.rendered_template = bos_token + self.rendered_template
            skip = True
            streamed_template = ""
            replaced = False
            is_end_of_message = False
            is_first_message = True

            if action == LLMActionType.GENERATE_IMAGE:
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message="Generating image prompt.\n",
                        is_first_message=is_first_message,
                        is_end_of_message=False,
                        name=self.botname,
                        action=LLMActionType.CHAT
                    )
                )
                is_first_message = False

            if action in (
                LLMActionType.CHAT,
                LLMActionType.GENERATE_IMAGE,
                LLMActionType.UPDATE_MOOD,
                LLMActionType.SUMMARIZE,
                LLMActionType.APPLICATION_COMMAND
            ):
                for new_text in self.streamer:
                    # strip all newlines from new_text
                    streamed_template += new_text
                    if self.is_mistral:
                        streamed_template = streamed_template.replace(f"{bos_token} [INST]", f"{bos_token}[INST]")
                        streamed_template = streamed_template.replace("  [INST]", " [INST]")
                    # iterate over every character in rendered_template and
                    # check if we have the same character in streamed_template
                    if not replaced:
                        for i, char in enumerate(self.rendered_template):
                            try:
                                if char == streamed_template[i]:
                                    skip = False
                                else:
                                    skip = True
                                    break
                            except IndexError:
                                skip = True
                                break
                    if skip:
                        continue
                    elif not replaced:
                        replaced = True
                        streamed_template = streamed_template.replace(self.rendered_template, "")
                    else:
                        if eos_token in new_text:
                            streamed_template = streamed_template.replace(eos_token, "")
                            new_text = new_text.replace(eos_token, "")
                            is_end_of_message = True
                        # strip botname from new_text
                        new_text = new_text.replace(f"{self.botname}:", "")
                        if action in (
                            LLMActionType.CHAT,
                            LLMActionType.PERFORM_RAG_SEARCH,
                            LLMActionType.GENERATE_IMAGE
                        ):
                            self.emit_signal(
                                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                                dict(
                                    message=new_text,
                                    is_first_message=is_first_message,
                                    is_end_of_message=is_end_of_message,
                                    name=self.botname,
                                    action=action
                                )
                            )
                        else:
                            self.emit_signal(
                                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                                dict(
                                    message="",
                                    is_first_message=is_first_message,
                                    is_end_of_message=is_end_of_message,
                                    name=self.botname,
                                    action=action
                                )
                            )
                        is_first_message = False
            elif action is LLMActionType.PERFORM_RAG_SEARCH:
                streamed_template = ""
                data = dict(
                    **self.generator_settings,
                    stopping_criteria=[stopping_criteria]
                )
                data.update(self.override_parameters)
                self.llm.generate_kwargs = data
                response = self.chat_engine.stream_chat(
                    message=self.prompt,
                    system_prompt=self.rendered_template
                )
                is_first_message = True
                is_end_of_message = False
                for new_text in response.response_gen:
                    streamed_template += new_text

                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        dict(
                            message=" " +new_text,
                            is_first_message=is_first_message,
                            is_end_of_message=is_end_of_message,
                            name=self.botname,
                            action=action
                        )
                    )
                    is_first_message = False
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message="",
                        is_first_message=False,
                        is_end_of_message=True,
                        name=self.botname,
                        action=action
                    )
                )

            if streamed_template is not None:
                if action in (
                    LLMActionType.CHAT,
                    LLMActionType.PERFORM_RAG_SEARCH,
                ):
                    self.add_message_to_history(
                        streamed_template,
                        LLMChatRole.ASSISTANT
                    )

                elif action is LLMActionType.UPDATE_MOOD:
                    self.bot_mood = streamed_template
                    return self.run(
                        prompt=self.prompt,
                        action=LLMActionType.CHAT,
                        **kwargs,
                    )

                elif action is LLMActionType.SUMMARIZE:
                    self._update_conversation_title(streamed_template)
                    return self.run(
                        prompt=self.prompt,
                        action=self._requested_action,
                        **kwargs,
                    )

                elif action is LLMActionType.GENERATE_IMAGE:
                    self.emit_signal(
                        SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
                        {
                            "message": streamed_template,
                            "type": "photo"
                        }
                    )
                elif action is LLMActionType.APPLICATION_COMMAND:
                    index = ''.join(c for c in streamed_template if c.isdigit())
                    try:
                        index = int(index)
                    except ValueError:
                        index = 0

                    try:
                        action = self.available_actions[index]
                    except KeyError:
                        action = LLMActionType.CHAT

                    if action is not None:
                        return self.run(
                            prompt=self.prompt,
                            action=action,
                        )
            return streamed_template

    def get_db_connection(self):
        return sqlite3.connect('airunner.db')

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        if content is None:
            return

        name = self.username
        is_bot = False

        if role is LLMChatRole.ASSISTANT and content:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")
            is_bot = True
            name = self.botname

        message = self.save_message(
            content,
            role.value,
            name,
            is_bot,
            self.conversation_id
        )

        self.history.append({
            "role": message.role,
            "content": message.content,
            "name": name,
            "is_bot": message.is_bot,
            "timestamp": message.timestamp,
            "conversation_id": message.conversation_id
        })

    def on_load_conversation(self, message):
        self.history = []
        self.conversation = message["conversation"]
        self.conversation_id = message["conversation_id"]

        # Merge the conversation object into the current session
        self.conversation = self.session.merge(self.conversation)

        self.history = self.load_history_from_db(self.conversation_id)
        self.set_conversation_title()
        self.emit_signal(SignalCode.SET_CONVERSATION, {
            "messages": self.history
        })

    def set_conversation_title(self):
        
        self.conversation_title = self.session.query(Conversation).filter_by(id=self.conversation_id).first().title
        

    def load_rag(self, model, tokenizer):
        self.__model = model
        self.__tokenizer = tokenizer
        self.__load_rag()

    def unload_rag(self):
        if self.__llm is not None:
            self.__llm.unload()
            del self.__llm
            self.__llm = None

    def reload_rag(self, data: dict = None):
        self.logger.debug("Reloading RAG index...")
        self.__target_files = data["target_files"] if data is not None else self.__target_files
        self.__load_rag()

    def __load_rag(self):
        self.__load_rag_tokenizer()
        self.__load_rag_model()
        self.__load_embeddings()
        self.__load_readers()
        self.__load_file_extractor()
        self.__load_document_reader()
        self.__load_documents()
        self.__load_text_splitter()
        self.__load_prompt_helper()
        self.__load_settings()
        self.__load_document_index()
        self.__load_retriever()
        self.__load_context_chat_engine()

    def __load_rag_tokenizer(self):
        self.logger.debug("Loading RAG tokenizer...")
        # TODO
        pass

    def __load_rag_model(self):
        self.logger.debug("Loading RAG model...")
        # TODO
        pass

    def __load_embeddings(self):
        self.logger.debug("Loading embeddings...")
        self.__embedding = CustomEmbedding(self.llm)

    def __load_readers(self):
        self.__pdf_reader = PDFReader()
        self.__epub_reader = EpubReader()
        self.__html_reader = HtmlFileReader()
        self.__markdown_reader = MarkdownReader()

    def __load_file_extractor(self):
        self.file_extractor = {
            ".pdf": self.__pdf_reader,
            ".epub": self.__epub_reader,
            ".html": self.__html_reader,
            ".htm": self.__html_reader,
            ".md": self.__markdown_reader,
        }

    def __load_document_reader(self):
        if self.target_files is None or len(self.target_files) == 0:
            return
        self.logger.debug("Loading document reader...")
        try:
            self.__document_reader = SimpleDirectoryReader(
                input_files=self.target_files,
                file_extractor=self.file_extractor,
                exclude_hidden=False
            )
            self.logger.debug("Document reader loaded successfully.")
        except ValueError as e:
            self.logger.error(f"Error loading document reader: {str(e)}")

    def __load_documents(self):
        if not self.__document_reader:
            return
        self.logger.debug("Loading documents...")
        self.__documents = self.__document_reader.load_data()

    def __load_text_splitter(self):
        self.__text_splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=20
        )

    def __load_prompt_helper(self):
        self.__prompt_helper = PromptHelper(
            context_window=4096,
            num_output=1024,
            chunk_overlap_ratio=0.1,
            chunk_size_limit=None,
        )

    def __load_context_chat_engine(self):
        try:
            self.__chat_engine = RefreshContextChatEngine.from_defaults(
                retriever=self.__retriever,
                chat_history=self.history,
                memory=None,
                system_prompt="Search the full text and find all relevant information related to the query.",
                node_postprocessors=[],
                llm=self.__llm,
            )
        except Exception as e:
            self.logger.error(f"Error loading chat engine: {str(e)}")

    def __load_settings(self):
        Settings.llm = self.__llm
        Settings._embed_model = self.__embedding
        Settings.node_parser = self.__text_splitter
        Settings.num_output = 512
        Settings.context_window = 3900

    def __load_document_index(self):
        self.logger.debug("Loading index...")
        documents = self.__documents or []
        try:
            self.__index = RAKEKeywordTableIndex.from_documents(
                documents,
                llm=self.__llm
            )
            self.logger.debug("Index loaded successfully.")
        except TypeError as e:
            self.logger.error(f"Error loading index: {str(e)}")

    def __load_retriever(self):
        try:
            self.__retriever = KeywordTableSimpleRetriever(
                index=self.__index,
            )
            self.logger.debug("Retriever loaded successfully with index.")
        except Exception as e:
            self.logger.error(f"Error setting up the retriever: {str(e)}")
