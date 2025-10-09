import os
from typing import List, Optional, Any, Dict
import hashlib
from datetime import datetime
import json

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
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    ExactMatchFilter,
)
from llama_index.core.schema import NodeWithScore, QueryBundle

from airunner.enums import EngineResponseCode, SignalCode
from airunner.components.llm.managers.agent import HtmlFileReader
from airunner.components.llm.managers.agent.chat_engine import (
    ConversationAwareContextChatEngine,
)
from airunner.settings import (
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
    AIRUNNER_LOCAL_FILES_ONLY,
    CUDA_ERROR,
)
from airunner.components.zimreader.llamaindex_zim_reader import (
    LlamaIndexZIMReader,
)
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)
from airunner.components.llm.managers.agent.tools import (
    RAGEngineTool,
)
import shutil
import gc
from bs4 import BeautifulSoup


class MultiIndexRetriever(VectorIndexRetriever):
    """Simple retriever that loads only manually-activated documents."""

    def __init__(
        self,
        rag_mixin,
        similarity_top_k: int = 5,
        **kwargs,
    ):
        """Initialize multi-index retriever.

        Args:
            rag_mixin: Reference to RAGMixin instance for loading indexes
            similarity_top_k: Number of nodes to retrieve total
        """
        self._rag_mixin = rag_mixin
        self._similarity_top_k = similarity_top_k

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Load and search only documents marked as active by user.

        This is a simple manual system - no automatic filtering or ranking.
        Only documents with active=True in the database are loaded.
        """
        all_nodes = []

        # Get active document IDs from database
        active_doc_ids = self._rag_mixin._get_active_document_ids()

        if not active_doc_ids:
            if hasattr(self._rag_mixin, "logger"):
                self._rag_mixin.logger.warning(
                    "No active documents selected. Please activate documents in the Documents panel."
                )
            return []

        if hasattr(self._rag_mixin, "logger"):
            self._rag_mixin.logger.info(
                f"Searching {len(active_doc_ids)} active document(s)"
            )

        for doc_id in active_doc_ids:
            try:
                # Lazy load the index
                doc_index = self._rag_mixin._load_doc_index(doc_id)
                if not doc_index:
                    continue

                # Create a retriever for this specific index
                retriever = VectorIndexRetriever(
                    index=doc_index,
                    similarity_top_k=self._similarity_top_k,
                )

                # Retrieve nodes from this index
                nodes = retriever.retrieve(query_bundle)
                all_nodes.extend(nodes)

            except Exception as e:
                # Log but continue with other indexes
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.error(
                        f"Error retrieving from index {doc_id}: {e}"
                    )

        # Sort all nodes by score (highest first)
        all_nodes.sort(key=lambda x: x.score or 0.0, reverse=True)

        # Return top N nodes across all filtered indexes
        return all_nodes[: self._similarity_top_k]


class RAGMixin:
    """Per-document RAG implementation with lazy loading for scalability."""

    def __init__(self):
        self.__document_reader: Optional[SimpleDirectoryReader] = None
        self.__index: Optional[VectorStoreIndex] = None
        self.__retriever: Optional[VectorIndexRetriever] = None
        self.__embedding: Optional[HuggingFaceEmbedding] = None
        self.__rag_engine: Optional[ConversationAwareContextChatEngine] = None
        self._rag_engine_tool: Optional[Any] = None
        self.__text_splitter: Optional[SentenceSplitter] = None
        self._target_files: Optional[List[str]] = None
        self.__doc_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self.__cache_validated: bool = False

        # Per-document index architecture
        self.__index_registry: Optional[Dict[str, Any]] = None
        self.__doc_indexes_cache: Dict[str, VectorStoreIndex] = {}
        self.__loaded_doc_ids: List[str] = []

        self._setup_rag()

    def _setup_rag(self):
        """Setup RAG components."""
        try:
            # Set up LlamaIndex settings
            Settings.llm = self.llm
            Settings.embed_model = self.embedding
            Settings.node_parser = self.text_splitter

            # Check for old unified index and migrate if needed
            self._detect_and_migrate_old_index()

            self.logger.info("RAG system initialized successfully")
        except Exception as e:
            self.logger.error(f"Error setting up RAG: {str(e)}")

    @property
    def text_splitter(self) -> SentenceSplitter:
        if not self.__text_splitter:
            self.__text_splitter = SentenceSplitter(
                chunk_size=512, chunk_overlap=50
            )
        return self.__text_splitter

    @property
    def doc_indexes_dir(self) -> str:
        """Directory containing per-document indexes."""
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "other",
                "cache",
                "doc_indexes",
            )
        )

    @property
    def registry_path(self) -> str:
        """Path to index registry file."""
        return os.path.join(self.doc_indexes_dir, "index_registry.json")

    @property
    def index_registry(self) -> Dict[str, Any]:
        """Get or load the index registry."""
        if self.__index_registry is None:
            self.__index_registry = self._load_registry()
        return self.__index_registry

    @property
    def embedding(self) -> HuggingFaceEmbedding:
        if not self.__embedding:
            import torch

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

            # Use GPU if available (same pattern as TTS/STT)
            device = "cuda:0" if torch.cuda.is_available() else "cpu"

            try:
                self.__embedding = HuggingFaceEmbedding(
                    model_name=path,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    device=device,
                )
                self.logger.info(f"HuggingFaceEmbedding loaded on {device}")
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
        """Get all document paths that exist on disk."""
        if self._target_files is not None:
            return self._target_files

        try:
            # Get all documents from DB
            all_docs = DBDocument.objects.all()
            # Filter to only those that exist on disk
            paths = [
                d.path
                for d in all_docs
                if getattr(d, "path", None) and os.path.exists(d.path)
            ]
            if paths:
                return paths
        except Exception as e:
            self.logger.error(f"Error fetching documents: {e}")

        return None

    @target_files.setter
    def target_files(self, value: Optional[List[str]]):
        """Set target files and reset index."""
        self._target_files = value
        self.__index = None
        self.__retriever = None
        self.__document_reader = None
        self.__doc_metadata_cache.clear()
        self.__cache_validated = False

    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA256 hash of file content for change detection."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            return None

    def _generate_doc_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path."""
        return hashlib.md5(file_path.encode()).hexdigest()[:16]

    def _validate_cache_integrity(self) -> bool:
        """Validate that disk cache matches database state.

        Returns:
            True if cache is valid and can be used, False if rebuild needed.
        """
        if self.__cache_validated:
            return True

        persist_dir = self.storage_persist_dir
        if not os.path.exists(persist_dir):
            self.logger.info("Cache directory does not exist - rebuild needed")
            return False

        try:
            # Check if we have any indexed documents in DB
            indexed_docs = DBDocument.objects.filter(
                DBDocument.indexed == True
            )
            if not indexed_docs or len(indexed_docs) == 0:
                self.logger.info("No indexed documents in DB")
                return False

            # Validate each indexed document
            needs_rebuild = False
            for doc in indexed_docs:
                if not os.path.exists(doc.path):
                    self.logger.warning(
                        f"Indexed document no longer exists: {doc.path}"
                    )
                    # Mark as not indexed
                    DBDocument.objects.update(pk=doc.id, indexed=False)
                    needs_rebuild = True
                    continue

                # Check if file has changed since indexing
                current_hash = self._calculate_file_hash(doc.path)
                if (
                    current_hash
                    and doc.file_hash
                    and current_hash != doc.file_hash
                ):
                    self.logger.info(
                        f"Document has changed since indexing: {doc.path}"
                    )
                    DBDocument.objects.update(pk=doc.id, indexed=False)
                    needs_rebuild = True

            if needs_rebuild:
                self.logger.info(
                    "Cache integrity check failed - rebuild needed"
                )
                return False

            self.logger.info("Cache integrity validated successfully")
            self.__cache_validated = True
            return True

        except Exception as e:
            self.logger.error(f"Error validating cache integrity: {e}")
            return False

    def _get_unindexed_documents(self) -> List[DBDocument]:
        """Get list of documents that need to be indexed."""
        try:
            all_docs = DBDocument.objects.all()
            unindexed = []

            for doc in all_docs:
                if not os.path.exists(doc.path):
                    continue

                if not doc.indexed:
                    unindexed.append(doc)
                    continue

                # Check if file changed
                current_hash = self._calculate_file_hash(doc.path)
                if (
                    current_hash
                    and doc.file_hash
                    and current_hash != doc.file_hash
                ):
                    self.logger.info(
                        f"File changed, needs re-indexing: {doc.path}"
                    )
                    DBDocument.objects.update(pk=doc.id, indexed=False)
                    unindexed.append(doc)

            return unindexed
        except Exception as e:
            self.logger.error(f"Error getting unindexed documents: {e}")
            return []

    def _get_active_document_ids(self) -> List[str]:
        """Get list of document IDs for documents marked as active.

        Returns:
            List of document IDs (generated from file paths)
        """
        try:
            active_docs = DBDocument.objects.filter(
                DBDocument.active == True, DBDocument.indexed == True
            )
            doc_ids = []
            for doc in active_docs:
                if os.path.exists(doc.path):
                    doc_id = self._generate_doc_id(doc.path)
                    doc_ids.append(doc_id)
            return doc_ids
        except Exception as e:
            self.logger.error(f"Error getting active documents: {e}")
            return []

    def _get_active_document_names(self) -> List[str]:
        """Get list of filenames for active documents.

        Returns:
            List of document filenames (not full paths)
        """
        try:
            active_docs = DBDocument.objects.filter(
                DBDocument.active == True, DBDocument.indexed == True
            )
            names = []
            for doc in active_docs:
                if os.path.exists(doc.path):
                    filename = os.path.basename(doc.path)
                    names.append(filename)
            return names
        except Exception as e:
            self.logger.error(f"Error getting active document names: {e}")
            return []

    def _mark_document_indexed(self, file_path: str):
        """Mark a document as indexed in the database with current hash."""
        try:
            docs = DBDocument.objects.filter_by(path=file_path)
            if docs and len(docs) > 0:
                doc = docs[0]
                file_hash = self._calculate_file_hash(file_path)
                file_size = (
                    os.path.getsize(file_path)
                    if os.path.exists(file_path)
                    else None
                )

                DBDocument.objects.update(
                    pk=doc.id,
                    indexed=True,
                    file_hash=file_hash,
                    indexed_at=datetime.utcnow(),
                    file_size=file_size,
                )
                self.logger.debug(f"Marked as indexed: {file_path}")
        except Exception as e:
            self.logger.error(f"Error marking document as indexed: {e}")

    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata for a document."""
        if file_path in self.__doc_metadata_cache:
            return self.__doc_metadata_cache[file_path]

        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()

        metadata = {
            "file_path": file_path,
            "file_name": filename,
            "file_type": file_ext,
            "doc_id": self._generate_doc_id(file_path),
        }

        # Add DB metadata if available
        db_docs = DBDocument.objects.filter_by(path=file_path)
        if db_docs and len(db_docs) > 0:
            db_doc = db_docs[0]
            if hasattr(db_doc, "index_uuid") and db_doc.index_uuid:
                metadata["index_uuid"] = db_doc.index_uuid
            if hasattr(db_doc, "indexed_at") and db_doc.indexed_at:
                metadata["indexed_at"] = db_doc.indexed_at.isoformat()

        self.__doc_metadata_cache[file_path] = metadata
        return metadata

    def _load_registry(self) -> Dict[str, Any]:
        """Load the index registry from disk."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r") as f:
                    registry = json.load(f)
                self.logger.info(
                    f"Loaded registry with {len(registry.get('documents', {}))} documents"
                )
                return registry
            except Exception as e:
                self.logger.error(f"Error loading registry: {e}")

        # Return empty registry
        return {"documents": {}, "version": "1.0"}

    def _save_registry(self):
        """Save the index registry to disk."""
        try:
            os.makedirs(self.doc_indexes_dir, exist_ok=True)
            with open(self.registry_path, "w") as f:
                json.dump(self.__index_registry, f, indent=2)
            self.logger.debug("Registry saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving registry: {e}")

    def _update_registry_entry(
        self,
        doc_id: str,
        file_path: str,
        chunk_count: int,
    ):
        """Update a document entry in the registry.

        Args:
            doc_id: Document ID
            file_path: Path to document
            chunk_count: Number of chunks
        """
        file_hash = self._calculate_file_hash(file_path)
        entry = {
            "path": file_path,
            "file_hash": file_hash,
            "indexed_at": datetime.utcnow().isoformat(),
            "chunk_count": chunk_count,
            "file_name": os.path.basename(file_path),
        }

        self.index_registry["documents"][doc_id] = entry
        self._save_registry()

    def _get_doc_index_dir(self, doc_id: str, file_path: str) -> str:
        """Get the directory path for a document's index."""
        filename = os.path.basename(file_path)
        # Sanitize filename for directory name
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in filename
        )
        return os.path.join(self.doc_indexes_dir, f"{doc_id}_{safe_filename}")

    def _index_single_document(self, db_doc: DBDocument) -> bool:
        """Index a single document into its own per-document index.

        Args:
            db_doc: Database document object

        Returns:
            bool: True if indexing succeeded, False otherwise
        """
        try:
            doc_id = self._generate_doc_id(db_doc.path)

            # Load document
            reader = SimpleDirectoryReader(
                input_files=[db_doc.path],
                file_extractor={
                    ".pdf": PDFReader(),
                    ".epub": CustomEpubReader(),
                    ".html": HtmlFileReader(),
                    ".htm": HtmlFileReader(),
                    ".md": MarkdownReader(),
                    ".zim": LlamaIndexZIMReader(),
                },
                file_metadata=self._extract_metadata,
            )

            docs = reader.load_data()
            if not docs:
                self.logger.warning(f"No content extracted from {db_doc.path}")
                return False

            # Enrich with metadata
            for doc in docs:
                doc.metadata.update(self._extract_metadata(db_doc.path))
                doc.metadata["doc_id"] = doc_id

            # Create per-document index
            doc_index = VectorStoreIndex.from_documents(
                docs,
                embed_model=self.embedding,
                show_progress=False,
            )

            # Save to disk
            index_dir = self._get_doc_index_dir(doc_id, db_doc.path)
            os.makedirs(index_dir, exist_ok=True)
            doc_index.storage_context.persist(persist_dir=index_dir)

            # Update registry
            self._update_registry_entry(doc_id, db_doc.path, len(docs))

            # Mark as indexed in DB
            self._mark_document_indexed(db_doc.path)

            self.logger.info(
                f"Indexed document {os.path.basename(db_doc.path)} ({len(docs)} chunks)"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to index {db_doc.path}: {e}")
            return False

    @property
    def document_reader(self) -> Optional[SimpleDirectoryReader]:
        """Get document reader for all indexed files."""
        if not self.target_files:
            self.logger.debug("No target files specified")
            return None

        if not self.__document_reader:
            self.logger.debug(
                f"Creating unified document reader for {len(self.target_files)} files"
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
                    file_metadata=self._extract_metadata,
                )
                self.logger.debug("Document reader created successfully")
            except Exception as e:
                self.logger.error(f"Error creating document reader: {str(e)}")
                return None
        return self.__document_reader

    @property
    def documents(self) -> List[Document]:
        """Load all documents with rich metadata."""
        if not self.document_reader:
            self.logger.debug("No document reader available")
            return []

        try:
            documents = self.document_reader.load_data()

            # Enrich with metadata from database
            for doc in documents:
                file_path = doc.metadata.get("file_path")
                if file_path:
                    doc.metadata.update(self._extract_metadata(file_path))

            self.logger.debug(
                f"Loaded {len(documents)} documents with metadata"
            )
            return documents
        except Exception as e:
            self.logger.error(f"Error loading documents: {e}")
            return []

    def _load_doc_index(self, doc_id: str) -> Optional[VectorStoreIndex]:
        """Lazy load a document's index from disk.

        Args:
            doc_id: Document ID

        Returns:
            VectorStoreIndex or None if loading fails
        """
        # Check cache first
        if doc_id in self.__doc_indexes_cache:
            return self.__doc_indexes_cache[doc_id]

        # Get doc info from registry
        doc_info = self.index_registry["documents"].get(doc_id)
        if not doc_info:
            self.logger.warning(f"Document {doc_id} not found in registry")
            return None

        # Load from disk
        try:
            index_dir = self._get_doc_index_dir(doc_id, doc_info["path"])
            if not os.path.exists(index_dir):
                self.logger.warning(f"Index directory not found: {index_dir}")
                return None

            storage_context = StorageContext.from_defaults(
                persist_dir=index_dir
            )
            doc_index = load_index_from_storage(storage_context)

            # Cache it
            self.__doc_indexes_cache[doc_id] = doc_index
            self.__loaded_doc_ids.append(doc_id)

            self.logger.debug(
                f"Loaded index for document {doc_info['file_name']}"
            )
            return doc_index

        except Exception as e:
            self.logger.error(f"Error loading index for {doc_id}: {e}")
            return None

    def _unload_doc_index(self, doc_id: str):
        """Unload a document's index from memory."""
        if doc_id in self.__doc_indexes_cache:
            del self.__doc_indexes_cache[doc_id]
            if doc_id in self.__loaded_doc_ids:
                self.__loaded_doc_ids.remove(doc_id)
            self.logger.debug(f"Unloaded index for document {doc_id}")

    @property
    def index(self) -> Optional[VectorStoreIndex]:
        """Get a merged query engine for all per-document indexes (lazy loading).

        Note: In per-document architecture, this loads all indexes which may be slow.
        Prefer using retriever property for queries which lazy loads as needed.
        """
        # Check if we have per-document indexes
        if self.index_registry["documents"]:
            # Load all document indexes (may be slow for many documents)
            all_doc_ids = list(self.index_registry["documents"].keys())

            if not all_doc_ids:
                self.logger.info("No documents in registry")
                return None

            # For now, return the first loaded index as primary
            # (The retriever will handle multi-index queries)
            if all_doc_ids:
                first_doc_id = all_doc_ids[0]
                return self._load_doc_index(first_doc_id)

        return None

    def index_all_documents(self) -> bool:
        """Manually index all documents with progress reporting (per-document architecture).

        Returns:
            bool: True if indexing succeeded, False otherwise
        """
        try:
            self.logger.info(
                "=== Starting per-document indexing (index_all_documents called) ==="
            )

            # Emit initial progress signal
            if hasattr(self, "emit_signal"):
                self.logger.info(
                    "Emitting initial RAG_INDEXING_PROGRESS signal"
                )
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    {
                        "progress": 0,
                        "current": 0,
                        "total": 0,
                        "document_name": "Preparing to index...",
                    },
                )

            # Get all unindexed documents
            self.logger.info("Getting list of unindexed documents...")
            unindexed_docs = self._get_unindexed_documents()
            total_docs = len(unindexed_docs)
            self.logger.info(f"Found {total_docs} unindexed documents")

            if total_docs == 0:
                self.logger.info("No documents need indexing")
                if hasattr(self, "emit_signal"):
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_COMPLETE,
                        {
                            "success": True,
                            "message": "All documents already indexed",
                        },
                    )
                return True

            # Reset any previous interrupt flag
            try:
                if hasattr(self, "do_interrupt"):
                    setattr(self, "do_interrupt", False)
            except Exception:
                pass

            # Index each document separately
            success_count = 0
            for idx, db_doc in enumerate(unindexed_docs, 1):
                # Check for external interrupt/cancel request
                if getattr(self, "do_interrupt", False):
                    self.logger.info("Indexing interrupted by user")
                    if hasattr(self, "emit_signal"):
                        self.emit_signal(
                            SignalCode.RAG_INDEXING_COMPLETE,
                            {
                                "success": False,
                                "message": f"Indexing cancelled by user ({success_count}/{total_docs} completed)",
                            },
                        )
                    # Reset flag
                    try:
                        setattr(self, "do_interrupt", False)
                    except Exception:
                        pass
                    return False

                if not os.path.exists(db_doc.path):
                    self.logger.warning(f"Document not found: {db_doc.path}")
                    continue

                # Emit progress
                doc_name = os.path.basename(db_doc.path)
                if hasattr(self, "emit_signal"):
                    progress_data = {
                        "current": idx,
                        "total": total_docs,
                        "progress": (idx / total_docs) * 100,
                        "document_name": doc_name,
                    }
                    self.logger.debug(
                        f"Emitting RAG_INDEXING_PROGRESS: {progress_data}"
                    )
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_PROGRESS,
                        progress_data,
                    )

                self.logger.info(
                    f"Indexing ({idx}/{total_docs}): {db_doc.path}"
                )

                # Index the document
                if self._index_single_document(db_doc):
                    success_count += 1

            # Emit completion
            self.__cache_validated = True

            if hasattr(self, "emit_signal"):
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": True,
                        "message": f"Successfully indexed {success_count}/{total_docs} document(s)",
                    },
                )

            self.logger.info(
                f"Per-document indexing complete: {success_count}/{total_docs} documents indexed"
            )
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error during per-document indexing: {e}")
            if hasattr(self, "emit_signal"):
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": False,
                        "message": f"Indexing failed: {str(e)}",
                    },
                )
            # Ensure interrupt flag cleared on failure
            try:
                if hasattr(self, "do_interrupt"):
                    setattr(self, "do_interrupt", False)
            except Exception:
                pass
            return False

    def _index_documents_with_progress(
        self, unindexed_docs: List[DBDocument], total: int
    ):
        """Index documents incrementally with progress reporting."""
        for idx, db_doc in enumerate(unindexed_docs, 1):
            # Check for external interrupt/cancel request
            if getattr(self, "do_interrupt", False):
                self.logger.info("Indexing interrupted by user")
                if hasattr(self, "emit_signal"):
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_COMPLETE,
                        {
                            "success": False,
                            "message": "Indexing cancelled by user",
                        },
                    )
                # Reset flag
                try:
                    setattr(self, "do_interrupt", False)
                except Exception:
                    pass
                return

            if not os.path.exists(db_doc.path):
                continue

            # Emit progress - loading phase
            doc_name = os.path.basename(db_doc.path)
            if hasattr(self, "emit_signal"):
                progress_data = {
                    "current": idx,
                    "total": total,
                    "progress": (idx / total) * 100,
                    "document_name": doc_name,
                }
                self.logger.debug(
                    f"Emitting RAG_INDEXING_PROGRESS: {progress_data}"
                )
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    progress_data,
                )

            self.logger.info(f"Indexing ({idx}/{total}): {db_doc.path}")

            try:
                # Load document with error handling
                reader = SimpleDirectoryReader(
                    input_files=[db_doc.path],
                    file_extractor={
                        ".pdf": PDFReader(),
                        ".epub": CustomEpubReader(),
                        ".html": HtmlFileReader(),
                        ".htm": HtmlFileReader(),
                        ".md": MarkdownReader(),
                        ".zim": LlamaIndexZIMReader(),
                    },
                    file_metadata=self._extract_metadata,
                )

                docs = reader.load_data()
                num_chunks = len(docs)

                # Emit progress - embedding phase
                if hasattr(self, "emit_signal"):
                    progress_data = {
                        "current": idx,
                        "total": total,
                        "progress": (idx / total) * 100,
                        "document_name": doc_name,
                    }
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_PROGRESS,
                        progress_data,
                    )

                # Index chunks (this is the slow part)
                for doc in docs:
                    doc.metadata.update(self._extract_metadata(db_doc.path))
                    self.__index.insert(doc)

                self._mark_document_indexed(db_doc.path)

            except Exception as e:
                self.logger.error(f"Failed to index {db_doc.path}: {e}")
                # For PDF errors, log but continue
                if "pypdf" in str(e).lower() or "encoding" in str(e).lower():
                    self.logger.warning(
                        f"PDF encoding issue, skipping: {db_doc.path}"
                    )
                else:
                    self.logger.error(f"Unexpected error: {e}", exc_info=True)
                # Continue with next document instead of failing completely
                continue

    def _full_index_rebuild_with_progress(
        self, unindexed_docs: List[DBDocument], total: int
    ):
        """Rebuild index from scratch with progress reporting."""
        all_docs = []

        # Phase 1: Load all documents (fast)
        for idx, db_doc in enumerate(unindexed_docs, 1):
            # Check for external interrupt/cancel request
            if getattr(self, "do_interrupt", False):
                self.logger.info("Full index rebuild interrupted by user")
                if hasattr(self, "emit_signal"):
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_COMPLETE,
                        {
                            "success": False,
                            "message": "Indexing cancelled by user",
                        },
                    )
                try:
                    setattr(self, "do_interrupt", False)
                except Exception:
                    pass
                return

            if not os.path.exists(db_doc.path):
                continue

            doc_name = os.path.basename(db_doc.path)

            # Emit progress - loading phase
            if hasattr(self, "emit_signal"):
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    {
                        "current": idx,
                        "total": total,
                        "progress": (idx / total) * 70,
                        "document_name": doc_name,
                    },
                )

            self.logger.info(f"Loading ({idx}/{total}): {db_doc.path}")

            try:
                # Load document with error handling
                reader = SimpleDirectoryReader(
                    input_files=[db_doc.path],
                    file_extractor={
                        ".pdf": PDFReader(),
                        ".epub": CustomEpubReader(),
                        ".html": HtmlFileReader(),
                        ".htm": HtmlFileReader(),
                        ".md": MarkdownReader(),
                        ".zim": LlamaIndexZIMReader(),
                    },
                    file_metadata=self._extract_metadata,
                )

                docs = reader.load_data()
                for doc in docs:
                    doc.metadata.update(self._extract_metadata(db_doc.path))
                    all_docs.append(doc)

            except Exception as e:
                self.logger.error(f"Failed to load {db_doc.path}: {e}")
                # For PDF errors, log but continue
                if "pypdf" in str(e).lower() or "encoding" in str(e).lower():
                    self.logger.warning(
                        f"PDF encoding issue, skipping: {db_doc.path}"
                    )
                else:
                    self.logger.error(f"Unexpected error: {e}", exc_info=True)
                # Continue with next document
                continue

        # Phase 2: Create index from all documents (SLOW - embedding generation)
        if hasattr(self, "emit_signal"):
            self.emit_signal(
                SignalCode.RAG_INDEXING_PROGRESS,
                {
                    "current": total,
                    "total": total,
                    "progress": 75,
                    "document_name": f"Generating embeddings for {len(all_docs)} chunks...",
                },
            )

        self.logger.info(
            f"Creating vector index from {len(all_docs)} chunks (this may take a while)..."
        )
        self.__index = VectorStoreIndex.from_documents(
            all_docs,
            embed_model=self.embedding,
            show_progress=True,  # Show progress in console
        )

        # Phase 3: Mark all as indexed
        if hasattr(self, "emit_signal"):
            self.emit_signal(
                SignalCode.RAG_INDEXING_PROGRESS,
                {
                    "current": total,
                    "total": total,
                    "progress": 95,
                    "document_name": "Finalizing index...",
                },
            )

        for db_doc in unindexed_docs:
            if os.path.exists(db_doc.path):
                self._mark_document_indexed(db_doc.path)

    def get_retriever_for_query(
        self,
        query: str,
        similarity_top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
    ) -> Optional[VectorIndexRetriever]:
        """Get a context-aware retriever for a specific query.

        Args:
            query: The user's query
            similarity_top_k: Number of chunks to retrieve
            doc_ids: Optional list of specific document IDs to search within

        Returns:
            Configured retriever with optional metadata filters
        """
        if not self.index:
            self.logger.error("No index available for retriever")
            return None

        try:
            filters = None
            if doc_ids:
                filters = MetadataFilters(
                    filters=[
                        ExactMatchFilter(key="doc_id", value=doc_id)
                        for doc_id in doc_ids
                    ]
                )

            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=similarity_top_k,
                filters=filters,
            )

            self.logger.debug(
                f"Created retriever with top_k={similarity_top_k}, "
                f"filtered_docs={len(doc_ids) if doc_ids else 'all'}"
            )
            return retriever

        except Exception as e:
            self.logger.error(f"Error creating retriever: {e}")
            return None

    @property
    def retriever(self) -> Optional[VectorIndexRetriever]:
        """Get retriever for manually-activated documents.

        Only loads documents marked as active=True in the database.
        No automatic filtering - users manually control which documents to search.
        """
        if not self.__retriever:
            # Create multi-index retriever for active documents only
            try:
                self.__retriever = MultiIndexRetriever(
                    rag_mixin=self,
                    similarity_top_k=5,
                )
                active_count = len(self._get_active_document_ids())
                self.logger.debug(
                    f"Created retriever for {active_count} active document(s)"
                )
            except Exception as e:
                self.logger.error(f"Error creating multi-index retriever: {e}")

        return self.__retriever

    @property
    def rag_system_prompt(self) -> str:
        """Get system prompt for RAG."""
        # Get list of active documents
        active_docs = self._get_active_document_names()

        if active_docs:
            doc_list = "\n".join([f"- {doc}" for doc in active_docs])
            available_docs_text = f"\n\nYou currently have access to the following documents:\n{doc_list}\n"
        else:
            available_docs_text = "\n\nNo documents are currently active.\n"

        return (
            f"{self.system_prompt}\n"
            "------\n"
            "CRITICAL INSTRUCTION: You are an AI assistant with access to a unified document search engine. "
            "You MUST base your answers EXCLUSIVELY on the retrieved document context provided to you. "
            "Do NOT use your general knowledge or training data to answer questions. "
            "ONLY use the specific information found in the retrieved documents. "
            "If the retrieved documents contain relevant information, use it to provide a detailed answer. "
            "If the retrieved documents do not contain relevant information, explicitly state that the information is not available. "
            "Always cite the source document (file_name) when referencing information. "
            f"Always respond as {self.botname} while strictly adhering to the document-based responses."
            f"{available_docs_text}"
            "------\n"
        )

    @property
    def rag_engine(self) -> Optional[ConversationAwareContextChatEngine]:
        """Get RAG chat engine with unified document access."""
        if not self.__rag_engine:
            if not self.retriever:
                self.logger.error("No retriever available for RAG engine")
                return None

            try:
                self.logger.debug(
                    "Creating conversation-aware RAG chat engine..."
                )
                self.__rag_engine = ConversationAwareContextChatEngine(
                    retriever=self.retriever,
                    memory=self.chat_memory,
                    prefix_messages=[],  # Will be set via update_system_prompt
                    llm=self.llm,
                    context_window_turns=3,  # Include last 3 conversation turns for context
                )
                # Set system prompt after creation
                self.__rag_engine.update_system_prompt(self.rag_system_prompt)
                self.logger.debug(
                    "Conversation-aware RAG chat engine created successfully"
                )
            except Exception as e:
                self.logger.error(f"Error creating RAG chat engine: {e}")
                return None
        return self.__rag_engine

    def create_contextual_rag_engine(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        similarity_top_k: int = 5,
    ) -> Optional[ConversationAwareContextChatEngine]:
        """Create a RAG engine for a specific query context.

        Args:
            query: The user's query
            doc_ids: Optional list of document IDs to focus on
            similarity_top_k: Number of chunks to retrieve

        Returns:
            Configured RAG chat engine
        """
        retriever = self.get_retriever_for_query(
            query=query, similarity_top_k=similarity_top_k, doc_ids=doc_ids
        )

        if not retriever:
            return None

        try:
            engine = ConversationAwareContextChatEngine(
                retriever=retriever,
                memory=self.chat_memory,
                prefix_messages=[],
                llm=self.llm,
                context_window_turns=3,
            )
            engine.update_system_prompt(self.rag_system_prompt)
            self.logger.debug(
                "Created contextual conversation-aware RAG engine"
            )
            return engine
        except Exception as e:
            self.logger.error(f"Error creating contextual RAG engine: {e}")
            return None

    @property
    def rag_engine_tool(self) -> Optional[Any]:
        """Get RAG engine tool."""
        if not self._rag_engine_tool:
            if not self.rag_engine:
                self.logger.error("No RAG engine available for tool")
                return None

            try:
                self.logger.info("Creating RAG engine tool")
                # Changed return_direct=False so RAG feeds context to CHAT instead of returning directly
                self._rag_engine_tool = RAGEngineTool.from_defaults(
                    chat_engine=self.rag_engine,
                    agent=self,
                    return_direct=False,
                )
                self.logger.debug("RAG engine tool created successfully")
            except Exception as e:
                self.logger.error(f"Error creating RAG engine tool: {e}")
                return None
        return self._rag_engine_tool

    def _detect_old_unified_index(self) -> bool:
        """Check if old unified index exists."""
        old_index_dir = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "other",
                "cache",
                "unified_index",
            )
        )
        return os.path.exists(old_index_dir) and os.path.exists(
            os.path.join(old_index_dir, "docstore.json")
        )

    def _migrate_from_unified_index(self):
        """Migrate from old unified index to per-document indexes."""
        if not self._detect_old_unified_index():
            return

        self.logger.info("Detected old unified index - migration needed")
        self.logger.info(
            "Marking all documents as unindexed to trigger re-indexing"
        )

        try:
            # Mark all documents as unindexed
            all_docs = DBDocument.objects.all()
            for doc in all_docs:
                DBDocument.objects.update(pk=doc.id, indexed=False)

            # Optionally backup old index
            old_index_dir = os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text",
                    "other",
                    "cache",
                    "unified_index",
                )
            )
            backup_dir = os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text",
                    "other",
                    "cache",
                    "unified_index_backup",
                )
            )

            if os.path.exists(old_index_dir) and not os.path.exists(
                backup_dir
            ):
                shutil.move(old_index_dir, backup_dir)
                self.logger.info(f"Backed up old index to {backup_dir}")

            self.logger.info(
                "Migration setup complete - please re-index all documents"
            )

        except Exception as e:
            self.logger.error(f"Error during migration: {e}")

    def _detect_and_migrate_old_index(self):
        """Check for and migrate old unified index on startup."""
        if self._detect_old_unified_index():
            self._migrate_from_unified_index()

    @property
    def storage_persist_dir(self) -> str:
        """Get storage directory for unified index persistence (legacy)."""
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "other",
                "cache",
                "unified_index",
            )
        )

    def _save_index(self):
        """Save unified index to disk."""
        if not self.__index:
            return

        try:
            persist_dir = str(self.storage_persist_dir)
            os.makedirs(persist_dir, exist_ok=True)
            self.__index.storage_context.persist(persist_dir=persist_dir)
            self.logger.info(f"Unified index saved to {persist_dir}")
        except Exception as e:
            self.logger.error(f"Error saving index: {e}")

    def _load_index(self) -> Optional[VectorStoreIndex]:
        """Load unified index from disk."""
        try:
            persist_dir = self.storage_persist_dir
            if os.path.exists(persist_dir):
                storage_context = StorageContext.from_defaults(
                    persist_dir=persist_dir
                )
                index = load_index_from_storage(storage_context)
                self.logger.info(f"Unified index loaded from {persist_dir}")
                return index
        except Exception as e:
            self.logger.debug(f"Could not load index from disk: {e}")
        return None

    def reload_rag(self):
        """Reload RAG components."""
        self.logger.debug("Reloading RAG...")
        self.__index = None
        self.__retriever = None
        self.__rag_engine = None
        self.__document_reader = None
        self._rag_engine_tool = None
        self.__doc_metadata_cache.clear()
        self.__cache_validated = False

        # Clear per-document index caches
        self.__doc_indexes_cache.clear()
        self.__loaded_doc_ids.clear()
        self.__index_registry = None

    def clear_rag_documents(self):
        """Clear all RAG documents and reset components."""
        self.logger.debug("Clearing RAG documents...")
        self.target_files = None
        # Only reload if not in the process of unloading
        if not getattr(self, "_is_unloading", False):
            self.reload_rag()

    def unload_rag(self):
        """Unload all RAG components."""
        self.logger.debug("Unloading RAG...")
        self._is_unloading = True
        try:
            self.target_files = None

            # Properly unload embedding model
            if self.__embedding is not None:
                try:
                    # Try to access and delete the internal model if it exists
                    if hasattr(self.__embedding, "_model"):
                        self.logger.debug(
                            "Deleting embedding internal model..."
                        )
                        del self.__embedding._model
                    if hasattr(self.__embedding, "model"):
                        self.logger.debug(
                            "Deleting embedding model attribute..."
                        )
                        del self.__embedding.model
                    # Delete the embedding wrapper
                    self.logger.debug("Deleting embedding wrapper...")
                    del self.__embedding
                except Exception as e:
                    self.logger.warning(f"Error deleting embedding: {e}")
            self.__embedding = None
            self.__text_splitter = None

            # Force garbage collection
            gc.collect()
        finally:
            self._is_unloading = False

    def load_html_into_rag(
        self, html_content: str, source_name: str = "web_content"
    ):
        """Load HTML content into the unified RAG index.

        Args:
            html_content: Raw HTML string
            source_name: Identifier for this content source
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            doc = Document(
                text=text,
                metadata={
                    "source": source_name,
                    "doc_id": self._generate_doc_id(source_name),
                    "file_type": ".html",
                },
            )

            if self.__index:
                self.__index.insert(doc)
                self.logger.info(
                    f"Inserted HTML content '{source_name}' into unified index"
                )
            else:
                self.logger.warning(
                    "No index available to insert HTML content"
                )

        except Exception as e:
            self.logger.error(f"Error loading HTML into RAG: {e}")
