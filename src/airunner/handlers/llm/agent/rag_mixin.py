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
from llama_index.core import StorageContext, load_index_from_storage
from airunner.handlers.llm.agent.html_file_reader import HtmlFileReader
from airunner.handlers.llm.agent.chat_engine.refresh_context_chat_engine import RefreshContextChatEngine
from airunner.data.models.news import Article
from airunner.data.models import Conversation


class RAGMixin():
    def __init__(self):
        self.__rag_engine: Optional[RefreshContextChatEngine] = None
        self.__document_reader: Optional[SimpleDirectoryReader] = None
        self.__prompt_helper: Optional[PromptHelper] = None
        self.__news_articles: Optional[List[Article]] = None
        self.__text_splitter: Optional[SentenceSplitter] = None
        self.__index: Optional[RAKEKeywordTableIndex] = None
        self.__retriever: Optional[KeywordTableSimpleRetriever] = None
        self.__embedding: Optional[HuggingFaceEmbedding] = None
        self.__pdf_reader: Optional[PDFReader] = None
        self.__epub_reader: Optional[EpubReader] = None
        self.__html_reader: Optional[HtmlFileReader] = None
        self.__markdown_reader: Optional[MarkdownReader] = None
        self.__file_extractor: Dict[str, object]
        self.__storage_context: Optional[StorageContext] = None

    @property
    def rag_engine(self) -> Optional[RefreshContextChatEngine]:
        if not self.__rag_engine:
            try:
                self.logger.debug("Loading chat engine...")
                self.rag_engine = RefreshContextChatEngine.from_defaults(
                    retriever=self.retriever,
                    #chat_history=self.history,
                    memory=self.chat_memory,
                    system_prompt=self._rag_system_prompt,
                    node_postprocessors=[],
                    llm=self.llm,
                )
                self.logger.debug("Chat engine loaded successfully.")
            except Exception as e:
                self.logger.error(f"Error loading chat engine: {str(e)}")
        return self.__rag_engine
    
    @rag_engine.setter
    def rag_engine(self, value: Optional[RefreshContextChatEngine]):
        self.__rag_engine = value

    @property
    def document_reader(self) -> SimpleDirectoryReader:
        return self.__document_reader
    
    @document_reader.setter
    def document_reader(self, value: SimpleDirectoryReader):
        self.__document_reader = value

    @property
    def prompt_helper(self) -> PromptHelper:
        return self.__prompt_helper
    
    @prompt_helper.setter
    def prompt_helper(self, value: PromptHelper):
        self.__prompt_helper = value

    @property
    def news_articles(self) -> List[Article]:
        if self.__news_articles is None:
            articles = self.session.query(Article).filter(
                Article.status == "scraped"
            ).all()[:50]
            self.__news_articles = [
                # Document(
                #     text=article.content,
                #     metadata={
                #         "id": article.id,
                #         "title": article.title,
                #         #"description": article.description,
                #     }
                # ) for article in articles[:50]
            ]
        return self.__news_articles or []
    
    @news_articles.setter
    def news_articles(self, value: List[Article]):
        self.__news_articles = value

    @property
    def text_splitter(self) -> SentenceSplitter:
        return self.__text_splitter
    
    @text_splitter.setter
    def text_splitter(self, value: SentenceSplitter):
        self.__text_splitter = value

    @property
    def index(self) -> Optional[RAKEKeywordTableIndex]:
        if not self.__index:
            self.logger.debug("Loading index...")
            index = None
            if self.storage_context:
                self.logger.debug("Loading from disc...")
                try:
                    index = (
                        load_index_from_storage(self.storage_context)
                        if self.storage_context
                        else None
                    )
                except ValueError:
                    self.logger.error("Error loading index from disc.")
            if not index:
                self.logger.debug("Loading index from documents...")
                try:
                    self.index = RAKEKeywordTableIndex.from_documents(
                        self.documents, 
                        llm=self.llm
                    )
                    self.logger.debug("Index loaded successfully.")
                except TypeError as e:
                    self.logger.error(f"Error loading index: {str(e)}")
            else:
                self.index = index
        return self.__index
    
    @index.setter
    def index(self, value: Optional[RAKEKeywordTableIndex]):
        self.__index = value

    @property
    def retriever(self) -> Optional[KeywordTableSimpleRetriever]:
        if not self.__retriever:
            try:
                self.logger.debug("Loading retriever...")
                self.retriever = KeywordTableSimpleRetriever(
                    index=self.index,
                )
                self.logger.debug("Retriever loaded successfully with index.")
            except Exception as e:
                self.logger.error(f"Error setting up the RAG retriever: {str(e)}")
        return self.__retriever
    
    @retriever.setter
    def retriever(self, value: Optional[KeywordTableSimpleRetriever]):
        self.__retriever = value

    @property
    def embedding(self) -> HuggingFaceEmbedding:
        return self.__embedding
    
    @embedding.setter
    def embedding(self, value: HuggingFaceEmbedding):
        self.__embedding = value

    @property
    def pdf_reader(self) -> Optional[PDFReader]:
        if not self.__pdf_reader:
            self.pdf_reader = PDFReader()
        return self.__pdf_reader
    
    @pdf_reader.setter
    def pdf_reader(self, value: Optional[PDFReader]):
        self.__pdf_reader = value

    @property
    def epub_reader(self) -> Optional[EpubReader]:
        if not self.__epub_reader:
            self.epub_reader = EpubReader()
        return self.__epub_reader
    
    @epub_reader.setter
    def epub_reader(self, value: Optional[EpubReader]):
        self.__epub_reader = value
    
    @property
    def html_reader(self) -> HtmlFileReader:
        if not self.__html_reader:
            self.html_reader = HtmlFileReader()
        return self.__html_reader
    
    @html_reader.setter
    def html_reader(self, value: HtmlFileReader):
        self.__html_reader = value

    @property
    def markdown_reader(self) -> MarkdownReader:
        if not self.__markdown_reader:
            self.markdown_reader = MarkdownReader()
        return self.__markdown_reader
    
    @markdown_reader.setter
    def markdown_reader(self, value: MarkdownReader):
        self.__markdown_reader = value

    @property
    def file_extractor(self) -> Dict[str, object]:
        return self.__file_extractor
    
    @file_extractor.setter
    def file_extractor(self, value: Dict[str, object]):
        self.__file_extractor = value

    @property
    def target_files(self) -> Optional[List[str]]:
        return [
            target_file.file_path for target_file in self.chatbot.target_files
        ]

    @property
    def conversation_documents(self) -> List[Document]:
        conversations = []
        _conversations = self.session.query(Conversation).all()
        for conversation in _conversations:
            messages = conversation.value or []
            conversation_text = f"Conversation {conversation.key}\n"
            for message in messages:
                conversation_text += f"{message['role']}: {message['blocks'][0]['text']}\n"
            conversation_text += "------\n"
            conversations.append(
                Document(
                    text=conversation_text,
                    metadata={
                        "id": conversation.id,
                        "key": conversation.key,
                    }
                )
            )
        return conversations

    @property
    def documents(self) -> List[Document]:
        documents = self.document_reader.load_data() if self.document_reader else []
        documents += self.conversation_documents
        documents += self.news_articles
        return documents

    @property
    def storage_persist_dir(self) -> str:
        return os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "text",
            "other",
            "cache"
        ))

    @property
    def storage_context(self) -> StorageContext:
        if self.__storage_context is None:
            if not os.path.exists(self.storage_persist_dir):
                os.makedirs(self.storage_persist_dir, exist_ok=True)
            for file in [
                "docstore.json",
                "index_store.json",
            ]:
                file_path = os.path.join(
                    self.storage_persist_dir,
                    file
                )
                if not os.path.exists(file_path):
                    with open(file_path, "w") as f:
                        f.write("{}")
            try:
                self.storage_context = StorageContext.from_defaults(
                    persist_dir=self.storage_persist_dir
                )
            except FileNotFoundError as e:
                self.logger.error(f"Error loading storage context: {str(e)}")
        return self.__storage_context
    
    @storage_context.setter
    def storage_context(self, value: StorageContext):
        self.__storage_context = value

    def load_rag(self):
        self._load_embeddings()
        self._load_document_reader()
        self._load_text_splitter()
        self._load_prompt_helper()
        self._load_settings()
    
    def unload_rag(self):
        self._unload_settings()
        self.rag_engine = None
        self.document_reader = None
        self.prompt_helper = None
        self.news_articles = None
        self.text_splitter = None
        self.index = None
        self.retriever = None
        self.embedding = None
        self.pdf_reader = None
        self.epub_reader = None
        self.html_reader = None
        self.markdown_reader = None
    
    def reload_rag(self):
        self.logger.debug("Reloading RAG...")
        self.retriever = None
        self.index = None
        self.rag_engine = None
        self.document_reader = None
        self._load_document_reader()

        # USE self.index.refresh_ref_docs to refresh the index
        

    def _load_embeddings(self):
        if not self.embedding:
            self.logger.debug("Loading embeddings...")
            path = os.path.expanduser(os.path.join(
                self.path_settings.base_path, 
                "text", 
                "models",
                "llm", 
                "embedding", 
                "intfloat/e5-large"
            ))
            self.embedding = HuggingFaceEmbedding(path)

    def _load_document_reader(self):
        if self.target_files is None or len(self.target_files) == 0:
            return
        self.logger.debug("Loading document reader...")
        try:
            self.document_reader = SimpleDirectoryReader(
                input_files=self.target_files,
                file_extractor={
                    ".pdf": self.pdf_reader,
                    ".epub": self.epub_reader,
                    ".html": self.html_reader,
                    ".htm": self.html_reader,
                    ".md": self.markdown_reader,
                },
                exclude_hidden=False
            )
            self.logger.debug("Document reader loaded successfully.")
        except ValueError as e:
            self.logger.error(f"Error loading document reader: {str(e)}")

    def _load_text_splitter(self):
        self.text_splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=20
        )

    def _load_prompt_helper(self):
        self.prompt_helper = PromptHelper(
            context_window=4096,
            num_output=1024,
            chunk_overlap_ratio=0.1,
            chunk_size_limit=None,
        )

    def _load_settings(self):
        Settings.llm = self.llm
        Settings._embed_model = self.embedding
        Settings.node_parser = self.text_splitter
        Settings.num_output = 512
        Settings.context_window = 3900
    
    def _unload_settings(self):
        Settings.llm = None
        Settings._embed_model = None
        Settings.node_parser = None
    
    def _save_index(self):
        pass
