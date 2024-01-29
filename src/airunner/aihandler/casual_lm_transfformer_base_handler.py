from typing import Iterable, Any

import torch
from llama_index.core.base_query_engine import BaseQueryEngine
from llama_index.core.llms.types import ChatResponse
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
        #full_message = self.chat_stream()
        full_message = self.rag_stream()
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

    def build_system_prompt(self):
        # The guardrails prompt is optional and can be overriden.
        guardrails_prompt = ""
        if self.settings["llm_generator_settings"]["use_guardrails"]:
            guardrails_prompt = self.settings["llm_generator_settings"]["guardrails_prompt"]

        system_prompt = []

        if self.settings["llm_generator_settings"]["use_guardrails"]:
            system_prompt.append(guardrails_prompt)

        if self.settings["llm_generator_settings"]["use_system_instructions"]:
            system_prompt.append(
                self.settings["llm_generator_settings"]["system_instructions"]
            )

        if self.settings["llm_generator_settings"]["assign_names"]:
            system_prompt.append(
                "Your name is " + self.botname + ". "
            )
            system_prompt.append(
                "The user's name is " + self.username + "."
            )

        if self.settings["llm_generator_settings"]["use_mood"]:
            system_prompt.append(f"Your mood: {self.bot_mood}.")

        if self.settings["llm_generator_settings"]["use_personality"]:
            system_prompt.append(f"Your personality: {self.bot_personality}.")

        system_prompt = "\n".join(system_prompt)
        return system_prompt

    def prepare_messages(self, system_prompt=None):
        if system_prompt is None:
            system_prompt = ChatMessage(
                role="system",
                content=self.build_system_prompt()
            )
        messages = [
            system_prompt
        ]
        for message in self.history:
            messages.append(
                ChatMessage(
                    role=message["role"],
                    content=message["content"]
                )
            )
        if self.prompt:
            messages.append(
                ChatMessage(
                    role="user",
                    content=self.prompt
                )
            )
        return messages

    def chat_stream(self):
        return self.stream_text(
            text_stream=self.llm.stream_chat(self.prepare_messages()),
            action=LLMAction.CHAT
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
    ):
        response_parser = self.parse_chat_response
        if action == LLMAction.RAG:
            response_parser = self.parse_rag_response

        for chat_response in text_stream:
            content, is_end_of_message, full_message = response_parser(
                content=chat_response,
                full_message=full_message
            )
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