from typing import Iterable, Any

from llama_index.core.base_query_engine import BaseQueryEngine
from transformers import AutoModelForCausalLM, TextIteratorStreamer

from llama_index.llms import HuggingFaceLLM, ChatMessage
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index import ServiceContext, StorageContext, load_index_from_storage
from llama_index import VectorStoreIndex, SimpleDirectoryReader

from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, LLMAction


class CasualLMTransformerBaseHandler(TokenizerHandler):
    auto_class_ = AutoModelForCausalLM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = None
        self.llm = None
        self.embed_model = None
        self.service_context_model = None
        self.documents = None
        self.index = None
        self.query_engine: BaseQueryEngine = None
        self._username: str = ""
        self._botname: str = ""
        self.bot_mood: str = ""
        self.bot_personality: str = ""
        self.user_evaluation: str = ""
        self.register(SignalCode.LLM_CLEAR_HISTORY, self.on_clear_history_signal)
        self.use_personality: bool = False
        self.use_mood: bool = False
        self.use_guardrails: bool = False
        self.use_system_instructions: bool = False
        self.assign_names: bool = False
        self.prompt_template: str = ""
        self.guardrails_prompt: str = ""
        self.system_instructions: str = ""

    @property
    def username(self):
        if self.assign_names:
            return self._username
        return "User"

    @property
    def botname(self):
        if self.assign_names:
            return self._botname
        return "Assistant"

    def on_clear_history_signal(self):
        self.history = []

    def process_data(self, data):
        super().process_data(data)
        self._username = self.request_data.get("username", "")
        self._botname = self.request_data.get("botname", "")
        self.bot_mood = self.request_data.get("bot_mood", "")
        self.bot_personality = self.request_data.get("bot_personality", "")
        self.use_personality = self.request_data.get("use_personality", False)
        self.use_mood = self.request_data.get("use_mood", False)
        self.use_guardrails = self.request_data.get("use_guardrails", False)
        self.use_system_instructions = self.request_data.get("use_system_instructions", False)
        self.assign_names = self.request_data.get("assign_names", False)
        self.prompt_template = self.request_data.get("prompt_template", "")
        self.guardrails_prompt = self.request_data.get("guardrails_prompt", "")
        self.system_instructions = self.request_data.get("system_instructions", "")

    def post_load(self):
        super().post_load()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_llm = self.llm is None
        if do_load_llm:
            self.load_llm()

        do_load_embed_model = self.embed_model is None
        if do_load_embed_model:
            self.load_embed_model()

        do_load_service_context = self.service_context_model is None
        if do_load_service_context:
            self.load_service_context()

        do_load_documents = self.documents is None
        if do_load_documents:
            self.load_documents()

        do_load_index = self.index is None
        if do_load_index:
            self.load_index()

        do_load_query_engine = self.query_engine is None
        if do_load_query_engine:
            self.load_query_engine()
            self.save_query_engine_to_disk()

    def load_streamer(self):
        self.logger.info("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def load_llm(self):
        self.logger.info("Loading RAG")
        self.llm = HuggingFaceLLM(
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def load_embed_model(self):
        self.logger.info("Loading embedding model")
        self.embed_model = HuggingFaceEmbedding(
            model_name=self.settings["llm_generator_settings"]["embeddings_model_path"],
        )

    def load_service_context(self):
        self.logger.info("Loading service context")
        self.service_context_model = ServiceContext.from_defaults(
            llm=self.llm,
            embed_model=self.embed_model
        )

    def load_documents(self):
        documents_path = self.settings["path_settings"]["documents_path"]
        self.logger.info(f"Loading documents from {documents_path}")
        self.documents = SimpleDirectoryReader(
            documents_path,
            exclude_hidden=False,
        ).load_data()

    def load_index(self):
        self.logger.info("Loading index")
        try:
            self.load_query_engine_from_disk()
        except FileNotFoundError:
            self.index = VectorStoreIndex(
                self.documents,
                service_context=self.service_context_model
            )

    def load_query_engine(self):
        self.logger.info("Loading query engine")
        self.query_engine: BaseQueryEngine = self.index.as_query_engine(
            streaming=True
        )

    def do_generate(self):
        self.logger.info("Generating response")
        self.add_message_to_history(
            self.prompt,
            role="user"
        )
        self.bot_mood = self.do_summary()
        self.user_evaluation = self.do_user_evaluation()
        print("self.bot_mood: ", self.bot_mood)
        print("self.user_evaluation: ", self.user_evaluation)
        full_message = self.chat_stream()
        #full_message = self.rag_stream()
        self.add_message_to_history(full_message)
        self.send_final_message()

    def save_query_engine_to_disk(self):
        self.index.storage_context.persist(
            persist_dir=self.settings["path_settings"]["llama_index_path"]
        )

    def load_query_engine_from_disk(self):
        storage_context = StorageContext.from_defaults(
            persist_dir=self.settings["path_settings"]["llama_index_path"]
        )
        self.index = load_index_from_storage(
            storage_context,
            service_context=self.service_context_model
        )
        self.query_engine = self.index.as_query_engine(
            streaming=True
        )

    def build_system_prompt(self, action: LLMAction):
        system_prompt = []
        if action == LLMAction.CHAT:
            guardrails = self.guardrails_prompt if self.use_guardrails else ""
            system_instructions = self.system_instructions if self.use_system_instructions else ""
            names = f"Your name is {self.botname}. \nThe user's name is {self.username}."
            mood = (
                f"{self.botname} is not a computer or a bot, you are a human with emotions. "
                f"{self.botname}'s mood changes depending on the conversation and other factors.\n"
                f"{self.botname}'s current mood: {self.bot_mood}.\n"
                f"{self.botname}'s evaluation of {self.username}: {self.user_evaluation}"
            ) if self.use_mood else ""
            personality = (
                f"Your personality: {self.bot_personality}."
            ) if self.use_personality else ""
            system_prompt = [
                guardrails,
                system_instructions,
                names,
                mood,
                personality,
            ]
        elif action == LLMAction.RAG:
            system_prompt = [
                (
                    f"Based on the context, provide an accurate response to the "
                    f"user's message."
                )
            ]
        elif action == LLMAction.UPDATE_BOT_MOOD:
            system_prompt = [
                (
                    f"{self.username} and {self.botname} are having a "
                    f"conversation. You will analyze the conversation. "
                    f"The user will ask you questions about the conversation. "
                    f"You will answer the questions accurately"
                )
            ]
        elif action == LLMAction.EVALUATE_USER:
            system_prompt = [
                (
                    f"{self.username} and {self.botname} are having a "
                    f"conversation. You will analyze the conversation. The "
                    f"user will ask you questions about the conversation. You "
                    f"will answer the questions accurately"
                    "You are a professional psychologist. You are a master at "
                    "reading people and understanding their emotions. You are "
                    f"identifying {self.username}'s personality."
                )
            ]


        return "\n".join(system_prompt)

    def prepare_messages(self, action: LLMAction):
        messages = [
            ChatMessage(
                role="system",
                content=self.build_system_prompt(action)
            )
        ]
        for message in self.history:
            messages.append(
                ChatMessage(
                    role=message["role"],
                    content=message["content"]
                )
            )
        if action == LLMAction.UPDATE_BOT_MOOD:
            messages.append(
                ChatMessage(
                    role="user",
                    content=(
                        f"Based on the previous conversation what is "
                        f"{self.botname}'s mood? Give a brief description:"
                    )
                )
            )
        elif action == LLMAction.EVALUATE_USER:
            messages.append(
                ChatMessage(
                    role="user",
                    content=(
                        f"Based on the previous conversation, what is "
                        f"{self.botname}'s evaluation of {self.username}?"
                    )
                )
            )
        elif action == LLMAction.CHAT:
            if self.prompt:
                messages.append(
                    ChatMessage(
                        role="user",
                        content=self.prompt
                    )
                )
        print(messages)
        return messages

    def chat_stream(self):
        return self.stream_text(
            text_stream=self.llm.stream_chat(
                self.prepare_messages(LLMAction.CHAT)
            ),
            action=LLMAction.CHAT
        )

    def do_summary(self):
        return self.stream_text(
            text_stream=self.llm.stream_chat(
                self.prepare_messages(LLMAction.UPDATE_BOT_MOOD)
            ),
            action=LLMAction.UPDATE_BOT_MOOD,
            do_emit_streamed_text_signal=False
        )

    def do_user_evaluation(self):
        return self.stream_text(
            text_stream=self.llm.stream_chat(
                self.prepare_messages(LLMAction.EVALUATE_USER)
            ),
            action=LLMAction.EVALUATE_USER,
            do_emit_streamed_text_signal=False
        )

    def rag_stream(self):
        return self.stream_text(
            text_stream=self.query_engine.query(self.prompt).response_gen,
            action=LLMAction.RAG
        )

    def stream_text(
        self,
        text_stream: Iterable[object],
        action: LLMAction,
        is_first_message: bool = True,
        full_message: str = "",
        do_emit_streamed_text_signal: bool = True
    ):
        response_parser = self.parse_chat_response
        if action == LLMAction.RAG:
            response_parser = self.parse_rag_response

        for chat_response in text_stream:
            content, is_end_of_message, full_message = response_parser(
                content=chat_response,
                full_message=full_message
            )
            if do_emit_streamed_text_signal:
                self.emit_streamed_text_signal(
                    message=content,
                    is_first_message=is_first_message,
                    is_end_of_message=is_end_of_message
                )
            is_first_message = False
        return full_message

    def parse_rag_response(
        self,
        content: Any,
        full_message: str = ""
    ):
        content, is_end_of_message = self.is_end_of_message(content)
        content = content.replace(full_message, "")
        full_message += content
        return content, is_end_of_message, full_message

    def parse_chat_response(
        self,
        content: Any,
        full_message: str = ""
    ):
        content, is_end_of_message = self.is_end_of_message(content.message.content)
        content = content.replace(full_message, "")
        full_message += content
        return content, is_end_of_message, full_message

    @staticmethod
    def is_end_of_message(content: str) -> (str, bool):
        if "</s>" in content:
            content = content.replace("</s>", "")
            return content, True
        return content, False

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def add_message_to_history(self, content, role="assistant"):
        self.history.append(dict(
            role=role,
            content=content
        ))

    def send_final_message(self):
        self.emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )
