# Implementation Plan: Per-Document Index Architecture

## Overview

Replace the unified index approach with per-document indexes for better scalability and performance.

## Step-by-Step Implementation

### Step 1: Add New Properties and Methods (rag_mixin.py)

```python
import json
import re

class RAGMixin:
    def __init__(self):
        # ... existing init ...
        self.__doc_indexes_cache: Dict[str, VectorStoreIndex] = {}  # NEW: In-memory cache
        self.__index_registry: Optional[Dict] = None  # NEW: Registry cache
        
    @property
    def doc_indexes_dir(self) -> str:
        """Directory for per-document indexes."""
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
        return os.path.join(
            os.path.dirname(self.doc_indexes_dir),
            "index_registry.json"
        )
```

### Step 2: Registry Management

```python
def _load_registry(self) -> Dict:
    """Load the index registry (lightweight, ~100KB even for 1000 docs)."""
    if self.__index_registry is not None:
        return self.__index_registry
    
    if os.path.exists(self.registry_path):
        try:
            with open(self.registry_path, 'r') as f:
                self.__index_registry = json.load(f)
                self.logger.debug(f"Loaded registry with {len(self.__index_registry.get('documents', {}))} documents")
                return self.__index_registry
        except Exception as e:
            self.logger.error(f"Error loading registry: {e}")
    
    self.__index_registry = {"documents": {}, "version": "1.0"}
    return self.__index_registry

def _save_registry(self, registry: Dict):
    """Save the index registry."""
    try:
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        self.__index_registry = registry
        self.logger.debug(f"Saved registry with {len(registry.get('documents', {}))} documents")
    except Exception as e:
        self.logger.error(f"Error saving registry: {e}")

def _update_registry_entry(self, doc_id: str, db_doc: DBDocument, chunk_count: int):
    """Add or update a document in the registry."""
    registry = self._load_registry()
    
    registry["documents"][doc_id] = {
        "path": db_doc.path,
        "file_name": os.path.basename(db_doc.path),
        "file_hash": self._calculate_file_hash(db_doc.path),
        "indexed_at": datetime.utcnow().isoformat(),
        "file_size": os.path.getsize(db_doc.path) if os.path.exists(db_doc.path) else 0,
        "chunk_count": chunk_count,
        "doc_type": os.path.splitext(db_doc.path)[1].lower(),
    }
    
    self._save_registry(registry)

def _remove_registry_entry(self, doc_id: str):
    """Remove a document from the registry."""
    registry = self._load_registry()
    if doc_id in registry.get("documents", {}):
        del registry["documents"][doc_id]
        self._save_registry(registry)
```

### Step 3: Per-Document Index Creation

```python
def _get_doc_index_dir(self, doc_id: str, db_doc: DBDocument) -> str:
    """Get the directory path for a document's index."""
    # Sanitize filename for use in path
    safe_name = re.sub(r'[^\w\-.]', '_', os.path.basename(db_doc.path))[:50]
    return os.path.join(self.doc_indexes_dir, f"{doc_id}_{safe_name}")

def _index_single_document(self, db_doc: DBDocument) -> bool:
    """Create a separate index for a single document.
    
    Returns:
        bool: True if indexing succeeded, False otherwise
    """
    doc_id = self._generate_doc_id(db_doc.path)
    doc_index_dir = self._get_doc_index_dir(doc_id, db_doc)
    
    try:
        self.logger.info(f"Indexing document: {db_doc.path}")
        
        # Load single document
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
            self.logger.warning(f"No content loaded from {db_doc.path}")
            return False
        
        # Enrich metadata
        for doc in docs:
            doc.metadata.update(self._extract_metadata(db_doc.path))
        
        # Create index for this document
        index = VectorStoreIndex.from_documents(
            docs,
            embed_model=self.embedding,
            show_progress=False,
        )
        
        # Save to dedicated directory
        os.makedirs(doc_index_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=doc_index_dir)
        
        # Update registry
        self._update_registry_entry(doc_id, db_doc, len(docs))
        
        # Mark as indexed in database
        self._mark_document_indexed(db_doc.path)
        
        self.logger.info(f"Successfully indexed {db_doc.path} ({len(docs)} chunks)")
        return True
        
    except Exception as e:
        self.logger.error(f"Error indexing {db_doc.path}: {e}", exc_info=True)
        return False
```

### Step 4: Lazy Index Loading

```python
def _load_doc_index(self, doc_id: str) -> Optional[VectorStoreIndex]:
    """Load a single document's index (lazy loading).
    
    Args:
        doc_id: Document ID
        
    Returns:
        VectorStoreIndex if found, None otherwise
    """
    # Check cache first
    if doc_id in self.__doc_indexes_cache:
        return self.__doc_indexes_cache[doc_id]
    
    # Find the index directory
    registry = self._load_registry()
    if doc_id not in registry.get("documents", {}):
        self.logger.warning(f"Document {doc_id} not in registry")
        return None
    
    doc_info = registry["documents"][doc_id]
    
    # Find index directory (may need to match by pattern since filename could vary)
    for dir_name in os.listdir(self.doc_indexes_dir):
        if dir_name.startswith(doc_id):
            doc_index_dir = os.path.join(self.doc_indexes_dir, dir_name)
            break
    else:
        self.logger.warning(f"Index directory not found for {doc_id}")
        return None
    
    try:
        # Load the index
        storage_context = StorageContext.from_defaults(persist_dir=doc_index_dir)
        index = load_index_from_storage(storage_context)
        
        # Cache it
        self.__doc_indexes_cache[doc_id] = index
        
        self.logger.debug(f"Loaded index for {doc_info['file_name']}")
        return index
        
    except Exception as e:
        self.logger.error(f"Error loading index for {doc_id}: {e}")
        return None

def _unload_doc_index(self, doc_id: str):
    """Unload a document index from cache to free memory."""
    if doc_id in self.__doc_indexes_cache:
        del self.__doc_indexes_cache[doc_id]
```

### Step 5: Query Across Multiple Document Indexes

```python
@property
def index(self) -> Optional[VectorStoreIndex]:
    """Get a composite index that queries across all document indexes.
    
    Note: This loads indexes on-demand during query.
    """
    # For compatibility, return None to signal lazy loading is in effect
    # Actual querying happens in retriever/rag_engine
    return None

@property
def retriever(self) -> Optional[VectorIndexRetriever]:
    """Get a retriever that queries across multiple document indexes."""
    # Return a custom retriever that handles multi-index querying
    # For now, return None and handle in rag_engine
    return None

@property
def rag_engine(self) -> Optional[ConversationAwareContextChatEngine]:
    """Create RAG engine with multi-index support."""
    if not self.__rag_engine:
        registry = self._load_registry()
        if not registry.get("documents"):
            self.logger.debug("No indexed documents available")
            return None
        
        try:
            # Create a custom query engine that handles multiple indexes
            self.__rag_engine = self._create_multi_index_chat_engine()
            self.logger.debug("Multi-index RAG chat engine created")
        except Exception as e:
            self.logger.error(f"Error creating RAG engine: {e}")
            return None
    
    return self.__rag_engine

def _create_multi_index_chat_engine(self) -> ConversationAwareContextChatEngine:
    """Create a chat engine that queries across multiple document indexes."""
    # Implementation: Create a custom retriever that:
    # 1. Loads relevant document indexes based on query
    # 2. Queries each index
    # 3. Merges and ranks results
    
    # For initial implementation, load all indexes (can optimize later)
    registry = self._load_registry()
    doc_ids = list(registry.get("documents", {}).keys())
    
    # Load top N most recently indexed documents
    # (Can be smarter with metadata filtering later)
    top_n = min(10, len(doc_ids))  # Load max 10 indexes
    
    indexes_to_query = []
    for doc_id in doc_ids[:top_n]:
        index = self._load_doc_index(doc_id)
        if index:
            indexes_to_query.append(index)
    
    if not indexes_to_query:
        raise ValueError("No indexes loaded")
    
    # For now, use the first index as primary (can merge later)
    # TODO: Implement proper multi-index querying
    primary_index = indexes_to_query[0]
    
    retriever = VectorIndexRetriever(
        index=primary_index,
        similarity_top_k=5,
    )
    
    return ConversationAwareContextChatEngine.from_defaults(
        retriever=retriever,
        llm=self.llm,
        system_prompt=self.rag_system_prompt,
        verbose=True,
    )
```

### Step 6: Update index_all_documents()

```python
def index_all_documents(self) -> bool:
    """Index all documents using per-document architecture."""
    try:
        self.logger.info("=== Starting per-document indexing ===")
        
        # Emit initial progress
        if hasattr(self, "emit_signal"):
            self.emit_signal(
                SignalCode.RAG_INDEXING_PROGRESS,
                {
                    "progress": 0,
                    "current": 0,
                    "total": 0,
                    "document_name": "Preparing to index...",
                },
            )
        
        # Get unindexed documents
        unindexed_docs = self._get_unindexed_documents()
        if not unindexed_docs:
            self.logger.info("No documents need indexing")
            if hasattr(self, "emit_signal"):
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {"success": True, "message": "All documents already indexed"},
                )
            return True
        
        total = len(unindexed_docs)
        self.logger.info(f"Indexing {total} documents using per-document architecture")
        
        # Index each document separately
        success_count = 0
        for idx, db_doc in enumerate(unindexed_docs, 1):
            if not os.path.exists(db_doc.path):
                continue
            
            doc_name = os.path.basename(db_doc.path)
            
            # Emit progress
            if hasattr(self, "emit_signal"):
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    {
                        "current": idx,
                        "total": total,
                        "progress": (idx / total) * 100,
                        "document_name": doc_name,
                    },
                )
            
            # Index this document
            if self._index_single_document(db_doc):
                success_count += 1
        
        # Emit completion
        if hasattr(self, "emit_signal"):
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": True,
                    "message": f"Successfully indexed {success_count}/{total} documents",
                },
            )
        
        self.logger.info(f"Indexing complete: {success_count}/{total} documents")
        return success_count > 0
        
    except Exception as e:
        self.logger.error(f"Error during indexing: {e}", exc_info=True)
        if hasattr(self, "emit_signal"):
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {"success": False, "message": str(e)},
            )
        return False
```

### Step 7: Migration Logic

```python
@property
def storage_persist_dir(self) -> str:
    """OLD unified index directory (for migration detection)."""
    return os.path.expanduser(
        os.path.join(
            self.path_settings.base_path,
            "text",
            "other",
            "cache",
            "unified_index",
        )
    )

def _detect_old_unified_index(self) -> bool:
    """Detect if old unified index exists."""
    return os.path.exists(self.storage_persist_dir)

def _migrate_from_unified_index(self):
    """Migrate from old unified index to per-document architecture."""
    if not self._detect_old_unified_index():
        return
    
    self.logger.info(
        "Detected old unified index. Migrating to per-document architecture..."
    )
    
    # Backup old index
    backup_dir = self.storage_persist_dir + "_backup"
    if not os.path.exists(backup_dir):
        import shutil
        shutil.copytree(self.storage_persist_dir, backup_dir)
        self.logger.info(f"Backed up old index to {backup_dir}")
    
    # Mark all documents as unindexed
    try:
        all_docs = DBDocument.objects.all()
        for doc in all_docs:
            DBDocument.objects.update(pk=doc.id, indexed=False)
        self.logger.info("Marked all documents as unindexed for rebuild")
    except Exception as e:
        self.logger.error(f"Error marking documents unindexed: {e}")
    
    # Delete old unified index
    import shutil
    shutil.rmtree(self.storage_persist_dir)
    self.logger.info("Removed old unified index")
    
    self.logger.info(
        "Migration complete. Per-document indexing architecture is now active. "
        "Please rebuild index using 'Index All' button."
    )
```

### Step 8: Update _setup_rag()

```python
def _setup_rag(self):
    """Setup RAG components."""
    try:
        # Check for old unified index and migrate if needed
        if self._detect_old_unified_index():
            self._migrate_from_unified_index()
        
        # Set up LlamaIndex settings
        Settings.llm = self.llm
        Settings.embed_model = self.embedding
        Settings.node_parser = self.text_splitter
        self.logger.info("RAG system initialized (per-document architecture)")
    except Exception as e:
        self.logger.error(f"Error setting up RAG: {str(e)}")
```

## Testing Checklist

- [ ] Create index for single document
- [ ] Verify registry.json is created and updated
- [ ] Verify document index directory is created
- [ ] Load document index from disk
- [ ] Query single document index
- [ ] Index multiple documents (10)
- [ ] Query across multiple documents
- [ ] Verify fast startup (no index loading)
- [ ] Verify fast query (lazy loading)
- [ ] Test migration from old unified index
- [ ] Test with 100 documents
- [ ] Test with 1000 documents (if available)
- [ ] Verify memory usage stays low
- [ ] Test update single document (reindex)
- [ ] Test delete document (cleanup)

## Performance Expectations

| Scenario | Expected Performance |
|----------|---------------------|
| App startup | < 1 second (no loading) |
| Index single doc | 10-30 seconds |
| Index 100 docs | 15-45 minutes (sequential) |
| First query | 1-3 seconds (load + query) |
| Subsequent queries | 0.5-2 seconds |
| Memory (1000 docs) | < 100MB (only loaded indexes) |

## Future Optimizations

1. **Parallel Indexing**: Use multiprocessing to index multiple docs simultaneously
2. **Smart Document Selection**: Use BM25 or keywords to pre-filter relevant docs
3. **Index Caching**: Keep frequently accessed indexes in memory
4. **Document Grouping**: Group small docs into single indexes
5. **Incremental Updates**: Only reindex changed portions of documents
6. **Metadata Extraction**: Extract keywords, topics, entities during indexing
