import os.path

from llama_index.core import Settings

from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import PromptHelper
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core import SimpleKeywordTableIndex
from llama_index.core.indices.keyword_table import KeywordTableSimpleRetriever

from airunner.aihandler.llm.huggingface_llm import HuggingFaceLLM
from airunner.enums import AgentState
from airunner.aihandler.llm.custom_embedding import CustomEmbedding
from airunner.aihandler.llm.agent.html_file_reader import HtmlFileReader


class AgentLlamaIndexMixin:
    def __init__(self):
        self.__documents = None
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

    @property
    def target_files(self):
        target_files = self.__target_files or []
        if len(target_files) == 0:
            target_files = []#self.chatbot.target_files or []
            print("TODO: load target files")
        return target_files

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

    def load_rag(self, model, tokenizer):
        self.__model = model
        self.__tokenizer = tokenizer
        self.__load_rag()

    def unload_rag(self):
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
        self.__load_documents()
        self.__load_text_splitter()
        self.__load_prompt_helper()
        self.__load_settings()
        self.__load_document_index()
        self.__load_retriever()
        self.__load_context_chat_engine()

    def __load_rag_tokenizer(self):
        self.logger.debug("Loading RAG tokenizer...")
        pass

    def __load_rag_model(self):
        self.logger.debug("Loading RAG model...")
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

    def __load_documents(self):
        self.logger.debug("Loading documents...")
        try:
            self.__documents = SimpleDirectoryReader(
                input_files=self.target_files,
                file_extractor=self.file_extractor,
                exclude_hidden=False
            ).load_data()
            self.logger.debug(f"Loaded {len(self.__documents)} documents.")
        except ValueError as e:
            self.logger.error(f"Error loading documents: {str(e)}")
            self.__documents = None

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
            self.__chat_engine = ContextChatEngine.from_defaults(
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
            self.__index = SimpleKeywordTableIndex.from_documents(
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
