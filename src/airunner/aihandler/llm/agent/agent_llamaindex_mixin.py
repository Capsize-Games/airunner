import os.path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface import HuggingFaceLLM
from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core import Settings
from airunner.aihandler.llm.html_file_reader import HtmlFileReader
from airunner.enums import SignalCode


class AgentLlamaIndexMixin:
    def __init__(self):
        self.__documents = None
        self.__index = None
        self.__service_context = None
        self.__callback_manager = None
        self.__pdf_reader = None
        self.__epub_reader = None
        self.__html_reader = None
        self.__markdown_reader = None
        self.__target_files = [
            ""
        ]
        self.__model_name = os.path.expanduser(f"{self.settings['path_settings']['sentence_transformers_path']}/sentence-t5-base")
        self.__query_instruction = "Search through all available texts and provide a brief summary of the key points which are relevant to the query."
        self.__text_instruction = "Summarize and provide a brief explanation of the text. Stay concise and to the point."

    def load_rag(self, model, tokenizer):
        self.__load_llm(model, tokenizer)
        self.__load_rag_model()
        self.__load_readers()
        self.__load_file_extractor()
        self.__load_documents()
        self.__load_service_context()
        self.__load_index()

    def __load_llm(self, model, tokenizer):
        self.__llm = HuggingFaceLLM(
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1000,
        )

    def perform_rag_search(self, prompt, streaming: bool = False):
        query_engine = self.__index.as_query_engine(streaming=streaming)
        response = query_engine.query(prompt)
        if streaming:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            is_first_message = True
            is_end_of_message = False
            for res in response.response_gen:
                print(res)
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=res,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False
        else:
            return response

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            dict(
                message="",
                is_first_message=is_first_message,
                is_end_of_message=True,
                name=self.botname,
            )
        )

    def __load_rag_model(self):
        self.logger.debug("Loading RAG model...")
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=self.__model_name,
            query_instruction=self.__query_instruction,
            text_instruction=self.__text_instruction,
            trust_remote_code=False,
        )

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

    def __load_documents(self):
        self.logger.debug("Loading documents...")
        self.__documents = SimpleDirectoryReader(
            input_files=self.__target_files,
            file_extractor=self.file_extractor,
            exclude_hidden=False
        ).load_data()

    def __load_service_context(self):
        self.logger.debug("Loading service context...")
        self.__service_context = ServiceContext.from_defaults(
            llm=self.__llm,
            embed_model=Settings.embed_model
        )

    def __load_index(self):
        self.logger.debug("Loading index...")
        self.__index = VectorStoreIndex.from_documents(
            self.__documents,
            service_context=self.__service_context,
        )
