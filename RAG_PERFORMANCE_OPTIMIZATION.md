# RAG Performance Optimization: FAISS Vector Store Migration

## Problem

The current unified RAG index implementation uses LlamaIndex's `SimpleVectorStore` which persists to JSON files:
- **102 documents = 600MB+ on disk**
- **Load time: 60+ seconds** (parsing large JSON files)
- **Scalability**: Will not scale to hundreds or thousands of documents
- **Memory intensive**: Entire JSON must be parsed into memory

## Root Cause

`SimpleVectorStore` serializes all vectors and metadata to JSON:
```
unified_index/
  ├── docstore.json          # Document storage (large)
  ├── vector_store.json      # Vector embeddings (very large)
  ├── index_store.json       # Index metadata
  └── graph_store.json       # Graph relationships
```

JSON parsing is slow for large files and Python's JSON decoder becomes a bottleneck.

## Solution: FAISS Vector Store

Use FAISS (Facebook AI Similarity Search) instead of SimpleVectorStore:
- **Binary format**: Efficient storage and loading
- **Fast loading**: 10-100x faster than JSON parsing
- **Memory efficient**: Can use memory-mapped files
- **Scalability**: Handles millions of vectors efficiently
- **Already included**: `llama-index-vector-stores-faiss==0.5.0` is in dependencies

### Expected Performance Improvements

| Metric | Current (SimpleVectorStore) | With FAISS |
|--------|----------------------------|------------|
| 100 docs load time | ~60 seconds | ~1-3 seconds |
| 1000 docs load time | ~10+ minutes | ~5-10 seconds |
| Disk size (100 docs) | 600MB | ~200-300MB |
| Search speed | Good | Excellent |

## Implementation Plan

### 1. Update RAG Mixin to Use FAISS

Changes to `src/airunner/components/llm/managers/agent/rag_mixin.py`:

1. Import FAISS vector store:
```python
from llama_index.vector_stores.faiss import FaissVectorStore
import faiss
```

2. Modify `_save_index()` to use FAISS:
```python
def _save_index(self):
    """Save unified index to disk with FAISS."""
    if not self.__index:
        return
    
    try:
        persist_dir = str(self.storage_persist_dir)
        os.makedirs(persist_dir, exist_ok=True)
        
        # Save vector store separately with FAISS
        vector_store = self.__index.vector_store
        if hasattr(vector_store, 'persist'):
            vector_store.persist(persist_path=os.path.join(persist_dir, "faiss_index"))
        
        # Save other stores (docstore, index_store, etc.)
        self.__index.storage_context.persist(persist_dir=persist_dir)
        self.logger.info(f"FAISS index saved to {persist_dir}")
    except Exception as e:
        self.logger.error(f"Error saving FAISS index: {e}")
```

3. Modify `_load_index()` to use FAISS:
```python
def _load_index(self) -> Optional[VectorStoreIndex]:
    """Load unified index from disk with FAISS."""
    try:
        persist_dir = self.storage_persist_dir
        if not os.path.exists(persist_dir):
            return None
        
        faiss_index_path = os.path.join(persist_dir, "faiss_index")
        
        # Load FAISS vector store
        vector_store = FaissVectorStore.from_persist_path(faiss_index_path)
        
        # Load storage context with FAISS vector store
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir,
            vector_store=vector_store
        )
        
        index = load_index_from_storage(storage_context)
        self.logger.info(f"FAISS index loaded from {persist_dir}")
        return index
    except Exception as e:
        self.logger.debug(f"Could not load FAISS index from disk: {e}")
        return None
```

4. Modify index creation in `_full_index_rebuild_with_progress()`:
```python
# Create FAISS vector store
dimension = 1024  # e5-large embedding dimension
faiss_index = faiss.IndexFlatL2(dimension)
vector_store = FaissVectorStore(faiss_index=faiss_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

self.__index = VectorStoreIndex.from_documents(
    all_docs,
    storage_context=storage_context,
    embed_model=self.embedding,
    show_progress=True,
)
```

### 2. Migration Strategy

**One-time migration** required:
1. Existing users will need to rebuild index in FAISS format
2. On first load with new code, detect old JSON format and prompt rebuild
3. Delete old `unified_index` directory
4. Run `index_all_documents()` to rebuild with FAISS

**Detection code**:
```python
def _detect_old_format(self) -> bool:
    """Detect if old JSON format is present."""
    persist_dir = self.storage_persist_dir
    if not os.path.exists(persist_dir):
        return False
    
    # Old format has vector_store.json but not faiss_index directory
    old_vector_store = os.path.join(persist_dir, "default__vector_store.json")
    new_faiss_index = os.path.join(persist_dir, "faiss_index")
    
    return os.path.exists(old_vector_store) and not os.path.exists(new_faiss_index)
```

### 3. User Communication

Add logging/UI message:
```
INFO: Detected old index format. Rebuilding index with optimized FAISS storage for faster loading...
This is a one-time migration. Future loads will be 10-100x faster.
```

## Alternative Solutions Considered

### 1. ChromaDB
- **Pros**: Full-featured vector database, persistent, supports filtering
- **Cons**: Additional service to run, more complex setup, overkill for local use

### 2. Qdrant
- **Pros**: High performance, cloud-ready, great features
- **Cons**: Requires running separate service, more dependencies

### 3. Per-document indexes
- **Pros**: Can load only needed documents
- **Cons**: Can't search across all documents efficiently, management overhead

### 4. Lazy loading
- **Pros**: Only load on first query
- **Cons**: First query still slow, doesn't solve core problem

## FAISS Was Chosen Because:
1. ✅ Already in dependencies
2. ✅ Minimal code changes
3. ✅ No external services needed
4. ✅ 10-100x faster load times
5. ✅ Scales to millions of vectors
6. ✅ Maintains unified index benefits
7. ✅ Can upgrade to ChromaDB/Qdrant later if needed

## Implementation Checklist

- [ ] Update `_save_index()` to use FAISS
- [ ] Update `_load_index()` to use FAISS
- [ ] Update `_full_index_rebuild_with_progress()` to create FAISS vector store
- [ ] Add old format detection
- [ ] Add migration logging
- [ ] Test with small dataset (10 docs)
- [ ] Test with medium dataset (100 docs)
- [ ] Test with large dataset (1000+ docs)
- [ ] Update user documentation
- [ ] Add migration guide

## Expected User Experience

**Before (SimpleVectorStore)**:
```bash
$ airunner
# ... app starts ...
# User clicks on chat
# 60 second freeze while loading index
# App responds
```

**After (FAISS)**:
```bash
$ airunner
# ... app starts ...
# User clicks on chat
# 1-2 second load
# App responds immediately
```

## Rollout Plan

1. **Phase 1**: Implement FAISS backend (this PR)
2. **Phase 2**: Test with beta users
3. **Phase 3**: Add auto-migration on first run
4. **Phase 4**: Document migration in release notes
5. **Future**: Consider ChromaDB for multi-user/cloud scenarios

## References

- FAISS Documentation: https://github.com/facebookresearch/faiss
- LlamaIndex FAISS Integration: https://docs.llamaindex.ai/en/stable/examples/vector_stores/FaissIndexDemo/
- Performance benchmarks: FAISS is 10-100x faster than JSON deserialization for vector data
