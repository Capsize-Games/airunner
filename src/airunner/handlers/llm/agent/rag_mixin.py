import os
from typing import List, Optional, Dict
from llama_index.core import (
    Document,
    Settings, 
    RAKEKeywordTableIndex,
    SimpleDirectoryReader,
    PromptHelper
)
from llama_index.core.indices.keyword_table import KeywordTableSimpleRetriever
from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from airunner.handlers.llm.agent.html_file_reader import HtmlFileReader
from airunner.handlers.llm.agent.refresh_context_chat_engine import RefreshContextChatEngine
from airunner.data.models.news import Article


class RAGMixin():
    def __init__(self):
        self.__rag_engine: Optional[RefreshContextChatEngine] = None
        self.__document_reader: Optional[SimpleDirectoryReader] = None
        self.__prompt_helper: Optional[PromptHelper] = None
        self.__documents: Optional[List[Document]] = None
        self.__text_splitter: Optional[SentenceSplitter] = None
        self.__index: Optional[RAKEKeywordTableIndex] = None
        self.__retriever: Optional[KeywordTableSimpleRetriever] = None
        self.__embedding: Optional[HuggingFaceEmbedding] = None
        self.__pdf_reader: PDFReader
        self.__epub_reader: EpubReader
        self.__html_reader: HtmlFileReader
        self.__markdown_reader: MarkdownReader
        self.__file_extractor: Dict[str, object]

    @property
    def rag_engine(self) -> RefreshContextChatEngine:
        return self.__rag_engine

    def load_rag(self):
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
        self.__load_context_rag_engine()
    
    def reload_rag(self):
        self.logger.debug("Reloading RAG index...")
        self.load_rag()

    def __load_embeddings(self):
        self.logger.debug("Loading embeddings...")
        path = os.path.expanduser(os.path.join(
            self.path_settings.base_path, 
            "text", 
            "models",
            "llm", 
            "embedding", 
            "intfloat/e5-large"
        ))
        self.__embedding = HuggingFaceEmbedding(path)

    def __load_readers(self):
        self.__pdf_reader = PDFReader()
        self.__epub_reader = EpubReader()
        self.__html_reader = HtmlFileReader()
        self.__markdown_reader = MarkdownReader()

    def __load_file_extractor(self):
        self.__file_extractor = {
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
                file_extractor=self.__file_extractor,
                exclude_hidden=False
            )
            self.logger.debug("Document reader loaded successfully.")
        except ValueError as e:
            self.logger.error(f"Error loading document reader: {str(e)}")

    def __load_documents(self):
        self.logger.debug("Loading documents...")
        documents = self.__document_reader.load_data() if self.__document_reader else []
        articles = self.session.query(Article).filter(Article.status == "scraped").all()
        documents += [
            Document(
                text=article.content,
                metadata={
                    "id": article.id,
                    "title": article.title,
                    #"description": article.description,
                }
            ) for article in articles[:50]
        ]
        self.__documents = documents

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

    def __load_context_rag_engine(self):
        try:
            self.__rag_engine = RefreshContextChatEngine.from_defaults(
                retriever=self.__retriever,
                chat_history=self.history,
                memory=None,
                system_prompt=self._rag_system_prompt,
                node_postprocessors=[],
                llm=self.llm,
            )
        except Exception as e:
            self.logger.error(f"Error loading chat engine: {str(e)}")

    def __load_settings(self):
        Settings.llm = self.llm
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
                llm=self.llm
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