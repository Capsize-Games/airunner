import os
from typing import List, Optional, Dict, Set
from llama_index.core import (
    Document,
    Settings, 
    RAKEKeywordTableIndex,
    SimpleDirectoryReader,
    PromptHelper
)
from llama_index.core.indices.keyword_table.utils import simple_extract_keywords
from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.keyword_table import KeywordTableSimpleRetriever
from airunner.handlers.llm.agent.html_file_reader import HtmlFileReader
from airunner.handlers.llm.agent.chat_engine.refresh_context_chat_engine import RefreshContextChatEngine
from airunner.data.models.news import Article
from airunner.data.models import Conversation


class RAGMixin:
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
        self._conversations: List[Conversation] = []

    @property
    def rag_engine(self) -> Optional[RefreshContextChatEngine]:
        if not self.__rag_engine:
            try:
                self.logger.debug("Loading chat engine...")
                if not self.retriever:
                    raise ValueError("No retriever found.")
                self.rag_engine = RefreshContextChatEngine.from_defaults(
                    retriever=self.retriever,
                    #chat_history=self.history,
                    memory=self.chat_memory,
                    system_prompt=self._rag_system_prompt,
                    node_postprocessors=[],
                    llm=self.llm,
                )
                self.logger.debug("Chat engine loaded successfully.")
            except ValueError as e:
                self.logger.error(f"ValueError loading chat engine: {str(e)}")
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
            articles = Article.objects.filter(
                Article.status == "scraped"
            ).all()[:50]
            self.__news_articles = [
                Document(
                    text=article.description,
                    metadata={
                        "id": article.id,
                        "title": article.title,
                        #"description": article.description,
                    }
                ) for article in articles[:50]
            ]
        return self.__news_articles or []
    
    @news_articles.setter
    def news_articles(self, value: List[Article]):
        self.__news_articles = value

    @property
    def text_splitter(self) -> SentenceSplitter:
        if not self.__text_splitter:
            self.text_splitter = SentenceSplitter(
                chunk_size=256,
                chunk_overlap=20
            )
        return self.__text_splitter
    
    @text_splitter.setter
    def text_splitter(self, value: SentenceSplitter):
        self.__text_splitter = value

    @property
    def index(self) -> Optional[RAKEKeywordTableIndex]:
        loaded_from_documents = False
        do_save_to_disc = False
        if not self.__index:
            self.logger.debug("Loading index...")
            if self.storage_context:
                self.logger.debug("Loading from disc...")
                try:
                    self.__index = (
                        load_index_from_storage(self.storage_context)
                        if self.storage_context
                        else None
                    )
                    self.logger.info("Index loaded successfully.")
                except ValueError:
                    self.logger.error("Error loading index from disc.")
            
            if not self.__index:
                self._load_index_from_documents()
                loaded_from_documents = True
                do_save_to_disc = True
            
            if not loaded_from_documents:
                self.logger.info("Refreshing index...")
                try:
                    # Get existing document IDs
                    existing_doc_ids = set(self.__index.docstore.docs.keys())
                    
                    # Get new documents that aren't in the index
                    new_nodes = []
                    for doc in self.documents:
                        doc_id = doc.doc_id
                        if doc_id not in existing_doc_ids:
                            nodes = self.text_splitter.get_nodes_from_documents([doc])
                            new_nodes.extend(nodes)
                    
                    if new_nodes:
                        self.logger.info(f"Adding {len(new_nodes)} new nodes to index...")
                        # Store nodes directly in docstore
                        for node in new_nodes:
                            # Ensure node has the correct ID
                            node.id_ = node.node_id
                            # Add node to docstore
                            self.__index.docstore.add_documents([node], allow_update=True)
                        
                        # Build keyword table for new nodes
                        new_keywords = {}
                        for node in new_nodes:
                            # Use RAKE algorithm to extract keywords
                            extracted = self._extract_keywords_from_text(node.text)
                            for keyword in extracted:
                                if keyword in new_keywords:
                                    new_keywords[keyword].append(node.node_id)
                                else:
                                    new_keywords[keyword] = [node.node_id]
                        
                        # Merge keyword tables
                        self.logger.debug("Merging keyword tables...")
                        for keyword, node_ids in new_keywords.items():
                            if keyword in self.__index.index_struct.table:
                                # Convert to set to deduplicate
                                existing_ids = set(self.__index.index_struct.table[keyword])
                                new_ids = set(node_ids)
                                # Merge and convert back to list
                                self.__index.index_struct.table[keyword] = list(existing_ids | new_ids)
                            else:
                                self.__index.index_struct.table[keyword] = node_ids

                        self.logger.info(f"Added {len(new_nodes)} nodes and updated keyword tables")
                        self._save_index_to_disc()
                        
                        self._update_conversations_status("indexed")
                    else:
                        self.logger.info("No new nodes to add to index.")
                        
                except Exception as e:
                    self.logger.error(f"Error refreshing index: {str(e)}")
                    self._load_index_from_documents()
            
            if self.__index and do_save_to_disc:
                self._save_index_to_disc()
        return self.__index

    def _update_conversations_status(self, status: str):
        conversations = Conversation.objects.filter(
            (Conversation.status != status) | (Conversation.status is None)
        ).all()
        total_conversations = len(conversations)
        if total_conversations == 1:
            conversations = []
        elif total_conversations > 1:
            conversations = conversations[:-1]
        for conversation in conversations:
            conversation.status = status
        conversation.save()
    
    @index.setter
    def index(self, value: Optional[RAKEKeywordTableIndex]):
        self.__index = value

    @staticmethod
    def _extract_keywords_from_text(text: str) -> Set[str]:
        """Extract keywords from text using RAKE algorithm."""
        # Use llama_index's built-in keyword extractor
        return set(simple_extract_keywords(text))

    def _load_index_from_documents(self):
        self.logger.debug("Loading index from documents...")
        try:
            self.__index = RAKEKeywordTableIndex.from_documents(
                self.documents,
                llm=self.llm
            )
            self.logger.debug("Index loaded successfully.")
        except TypeError as e:
            self.logger.error(f"Error loading index: {str(e)}")
    
    def _save_index_to_disc(self):
        self.logger.info("Saving index to disc...")
        try:
            self.__index.storage_context.persist(persist_dir=self.storage_persist_dir)
            self.logger.info("Index saved successfully.")
            self.logger.info("Setting conversations status to indexed...")
            self._update_conversations_status("indexed")
        except ValueError:
            self.logger.error("Error saving index to disc.")

    @property
    def retriever(self) -> Optional[KeywordTableSimpleRetriever]:
        if not self.__retriever:
            try:
                self.logger.debug("Loading retriever...")
                index = self.index
                if not index:
                    raise ValueError("No index found.")
                self.retriever = KeywordTableSimpleRetriever(
                    index=index,
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
        if not self.__embedding:
            self.logger.debug("Loading embeddings...")
            path = os.path.expanduser(os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "embedding",
                "intfloat/e5-large"
            ))

            try:
                self.__embedding = HuggingFaceEmbedding(path)
            except NotImplementedError:
                self.logger.error("Error loading embeddings.")
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
    def conversations(self) -> List[Conversation]:
        conversations = Conversation.objects.filter(
            (Conversation.status != "indexed") | (Conversation.status is None)
        ).all()
        total_conversations = len(conversations)
        if total_conversations == 1:
            conversations = []
        elif total_conversations > 1:
            conversations = conversations[:-1]
        return conversations

    @property
    def conversation_documents(self) -> List[Document]:
        conversation_documents = []
        conversations = Conversation.objects.filter(
            (Conversation.status != "indexed") | (Conversation.status is None)
        ).all()
        total_conversations = len(conversations)
        if total_conversations == 1:
            conversations = []
        elif total_conversations > 1:
            conversations = conversations[:-1]
        for conversation in conversations:
            messages = conversation.value or []
            for message_id, message in enumerate(messages):
                username = (
                    conversation.user_name
                    if message["role"] == "user"
                    else conversation.chatbot_name
                )
                conversation_documents.append(
                    Document(
                        text=f'{message["role"]}: \"{message["blocks"][0]["text"]}\"',
                        metadata={
                            "id": str(conversation.id) + "_" + str(message_id),
                            "key": conversation.key + "_" + str(message_id),
                            "speaker": username,
                            "role": message["role"],
                        }
                    )
                )
        return conversation_documents

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
        self._load_document_reader()
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
        self._conversations = None
        self._load_document_reader()

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
    
    @staticmethod
    def _unload_settings():
        Settings.llm = None
        Settings._embed_model = None
        Settings.node_parser = None
    
    def _save_index(self):
        pass
