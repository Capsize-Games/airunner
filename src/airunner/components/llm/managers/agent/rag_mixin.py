import os
from typing import List, Optional, Any

from llama_index.core import (
    Document,
    Settings,
    VectorStoreIndex,
    SimpleDirectoryReader,
)
from llama_index.readers.file import PDFReader, MarkdownReader
from airunner.components.llm.managers.agent.custom_epub_reader import (
    CustomEpubReader,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever

from airunner.enums import EngineResponseCode
from airunner.components.llm.managers.agent import HtmlFileReader
from airunner.components.llm.managers.agent.chat_engine import (
    RefreshContextChatEngine,
)
from airunner.settings import (
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
    AIRUNNER_LOCAL_FILES_ONLY,
    CUDA_ERROR,
)
from airunner.components.zimreader.llamaindex_zim_reader import (
    LlamaIndexZIMReader,
)


class RAGMixin:
    """Simple RAG implementation using VectorStoreIndex for document search."""

    def __init__(self):
        self.__document_reader: Optional[SimpleDirectoryReader] = None
        self.__index: Optional[VectorStoreIndex] = None
        self.__retriever: Optional[VectorIndexRetriever] = None
        self.__embedding: Optional[HuggingFaceEmbedding] = None
        self.__rag_engine: Optional[RefreshContextChatEngine] = None
        self._rag_engine_tool: Optional[Any] = None
        self.__text_splitter: Optional[SentenceSplitter] = None
        self._target_files: Optional[List[str]] = None

        self._setup_rag()

    def _setup_rag(self):
        """Setup RAG components."""
        try:
            # Set up LlamaIndex settings
            Settings.llm = self.llm
            Settings.embed_model = self.embedding
            Settings.node_parser = self.text_splitter
            self.logger.info("RAG system initialized successfully")
        except Exception as e:
            self.logger.error(f"Error setting up RAG: {str(e)}")

    @property
    def text_splitter(self) -> SentenceSplitter:
        if not self.__text_splitter:
            self.__text_splitter = SentenceSplitter(
                chunk_size=256, chunk_overlap=20
            )
        return self.__text_splitter

    @property
    def embedding(self) -> HuggingFaceEmbedding:
        if not self.__embedding:
            self.logger.debug("Loading embeddings...")
            path = os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text",
                    "models",
                    "llm",
                    "embedding",
                    "intfloat/e5-large",
                )
            )

            try:
                self.__embedding = HuggingFaceEmbedding(
                    model_name=path, local_files_only=AIRUNNER_LOCAL_FILES_ONLY
                )
            except Exception as e:
                code = EngineResponseCode.ERROR
                error_message = "Error loading embeddings " + str(e)
                response = error_message
                if CUDA_ERROR in str(e):
                    code = EngineResponseCode.INSUFFICIENT_GPU_MEMORY
                    response = AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE
                self.logger.error(error_message)
                self.api.worker_response(code, response)
        return self.__embedding

    @property
    def target_files(self) -> Optional[List[str]]:
        """Get target files for RAG indexing."""
        if self._target_files is not None:
            return self._target_files
        chatbot_files = [
            target_file.file_path for target_file in self.chatbot.target_files
        ]
        return chatbot_files if chatbot_files else None

    @target_files.setter
    def target_files(self, value: Optional[List[str]]):
        """Set target files for the document reader."""
        self._target_files = value
        # Reset index when target files change
        self.__index = None
        self.__retriever = None
        self.__document_reader = None

    @property
    def document_reader(self) -> Optional[SimpleDirectoryReader]:
        """Get document reader for target files."""
        if not self.target_files:
            self.logger.debug("No target files specified")
            return None

        if not self.__document_reader:
            self.logger.debug(
                f"Creating document reader for files: {self.target_files}"
            )
            try:
                self.__document_reader = SimpleDirectoryReader(
                    input_files=self.target_files,
                    file_extractor={
                        ".pdf": PDFReader(),
                        ".epub": CustomEpubReader(),
                        ".html": HtmlFileReader(),
                        ".htm": HtmlFileReader(),
                        ".md": MarkdownReader(),
                        ".zim": LlamaIndexZIMReader(),
                    },
                    exclude_hidden=False,
                )
                self.logger.debug("Document reader created successfully")
            except Exception as e:
                self.logger.error(f"Error creating document reader: {str(e)}")
                return None
        return self.__document_reader

    @property
    def documents(self) -> List[Document]:
        """Load documents from target files."""
        if not self.document_reader:
            self.logger.debug("No document reader available")
            return []

        try:
            documents = self.document_reader.load_data()
            self.logger.debug(f"Loaded {len(documents)} documents")
            return documents
        except Exception as e:
            self.logger.error(f"Error loading documents: {str(e)}")
            return []

    @property
    def index(self) -> Optional[VectorStoreIndex]:
        """Get or create the vector index."""
        if not self.__index:
            self.logger.debug("Creating vector index...")
            documents = self.documents

            if not documents:
                self.logger.warning("No documents available for indexing")
                return None

            try:
                # Create index from documents
                self.__index = VectorStoreIndex.from_documents(
                    documents, embed_model=self.embedding, show_progress=True
                )
                self.logger.info(
                    f"Created vector index with {len(documents)} documents"
                )

                # Save index to storage
                self._save_index()

            except Exception as e:
                self.logger.error(f"Error creating vector index: {str(e)}")
                return None

        return self.__index

    @property
    def retriever(self) -> Optional[VectorIndexRetriever]:
        """Get retriever for the index."""
        if not self.__retriever and self.index:
            try:
                self.__retriever = VectorIndexRetriever(
                    index=self.index,
                    similarity_top_k=3,  # Return top 3 most relevant chunks
                )
                self.logger.debug("Created vector retriever")
            except Exception as e:
                self.logger.error(f"Error creating retriever: {str(e)}")
        return self.__retriever

    @property
    def rag_system_prompt(self) -> str:
        """Get system prompt for RAG."""
        return (
            f"{self.system_prompt}\n"
            "------\n"
            "CRITICAL INSTRUCTION: You are an AI assistant with access to document search capabilities. "
            "You MUST base your answers EXCLUSIVELY on the retrieved document context provided to you. "
            "Do NOT use your general knowledge or training data to answer questions. "
            "ONLY use the specific information found in the retrieved documents. "
            "If the retrieved documents contain relevant information, use it to provide a detailed answer. "
            "If the retrieved documents do not contain relevant information, explicitly state that the information is not available in the provided documents. "
            f"Always respond as {self.botname} while strictly adhering to the document-based responses.\n"
            "------\n"
        )

    @property
    def rag_engine(self) -> Optional[RefreshContextChatEngine]:
        """Get RAG chat engine."""
        if not self.__rag_engine:
            if not self.retriever:
                self.logger.error("No retriever available for RAG engine")
                return None

            try:
                self.logger.debug("Creating RAG chat engine...")
                self.__rag_engine = RefreshContextChatEngine.from_defaults(
                    retriever=self.retriever,
                    memory=self.chat_memory,
                    system_prompt=self.rag_system_prompt,
                    llm=self.llm,
                )
                self.logger.debug("RAG chat engine created successfully")
            except Exception as e:
                self.logger.error(f"Error creating RAG chat engine: {str(e)}")
                return None
        return self.__rag_engine

    @property
    def rag_engine_tool(self) -> Optional[Any]:
        """Get RAG engine tool."""
        if not self._rag_engine_tool:
            if not self.rag_engine:
                self.logger.error("No RAG engine available for tool")
                return None

            try:
                # Import here to avoid circular dependency
                from airunner.components.llm.managers.agent.tools import (
                    RAGEngineTool,
                )

                self.logger.info("Creating RAG engine tool")
                self._rag_engine_tool = RAGEngineTool.from_defaults(
                    chat_engine=self.rag_engine, agent=self, return_direct=True
                )
                self.logger.debug("RAG engine tool created successfully")
            except Exception as e:
                self.logger.error(f"Error creating RAG engine tool: {str(e)}")
                return None
        return self._rag_engine_tool

    @property
    def storage_persist_dir(self) -> str:
        """Get storage directory for index persistence."""
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path, "text", "other", "cache"
            )
        )

    def _save_index(self):
        """Save index to disk."""
        if not self.__index:
            return

        try:
            persist_dir = str(
                self.storage_persist_dir
            )  # Ensure string conversion
            os.makedirs(persist_dir, exist_ok=True)
            self.__index.storage_context.persist(persist_dir=persist_dir)
            self.logger.info(f"Index saved to {persist_dir}")
        except Exception as e:
            self.logger.error(f"Error saving index: {str(e)}")
            # Don't fail the whole process if saving fails
            pass

    def _load_index(self) -> Optional[VectorStoreIndex]:
        """Load index from disk."""
        try:
            persist_dir = self.storage_persist_dir
            if os.path.exists(persist_dir):
                storage_context = StorageContext.from_defaults(
                    persist_dir=persist_dir
                )
                index = load_index_from_storage(storage_context)
                self.logger.info(f"Index loaded from {persist_dir}")
                return index
        except Exception as e:
            self.logger.debug(f"Could not load index from disk: {str(e)}")
        return None

    def reload_rag(self):
        """Reload RAG components."""
        self.logger.debug("Reloading RAG...")
        self.__index = None
        self.__retriever = None
        self.__rag_engine = None
        self.__document_reader = None
        self._rag_engine_tool = None

    def clear_rag_documents(self):
        """Clear all RAG documents and reset components."""
        self.logger.debug("Clearing RAG documents...")
        self.target_files = None
        self.reload_rag()

    def unload_rag(self):
        """Unload all RAG components."""
        self.logger.debug("Unloading RAG...")
        self.clear_rag_documents()
        self.__embedding = None
        self.__text_splitter = None
