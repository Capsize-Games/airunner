# RAG Per-Document Index Architecture

## Problem with Unified Index Approach

**Original issue**: Single unified index with all documents
- 102 documents = 600MB+ index
- Load time: 60+ seconds
- Scales poorly: 1000 docs = 10+ minute load
- **FAISS solution rejected**: Platform compatibility issues (conda-only, no Windows pip support)

## New Solution: Per-Document Indexes + Lazy Loading

Create **separate small indexes per document** and only load what's needed for each query.

### Architecture

```
~/.local/share/airunner/text/other/cache/
├── doc_indexes/
│   ├── abc123_filename1/
│   │   ├── default__vector_store.json    # Small (~1-10MB per doc)
│   │   ├── docstore.json
│   │   ├── index_store.json
│   │   └── metadata.json                 # Document metadata
│   ├── def456_filename2/
│   │   └── ...
│   └── ...
└── index_registry.json                    # Lightweight registry (~1-100KB)
```

### Index Registry Format

```json
{
  "documents": {
    "abc123_filename1": {
      "path": "/path/to/document.pdf",
      "file_hash": "sha256...",
      "indexed_at": "2025-10-09T10:30:00",
      "file_size": 1024000,
      "chunk_count": 42,
      "keywords": ["topic1", "topic2"],
      "doc_type": "pdf",
      "title": "Document Title",
      "last_modified": "2025-10-08T15:20:00"
    },
    "def456_filename2": { ... }
  },
  "version": "1.0"
}
```

## Query Flow

### 1. Fast Metadata Scan (< 1ms)
```python
# Load lightweight registry (JSON, ~100KB even for 1000 docs)
registry = load_registry()  # Fast

# Optional: Use keywords/metadata to pre-filter relevant docs
relevant_docs = filter_by_metadata(query, registry)  # Fast
```

### 2. Lazy Index Loading (on-demand)
```python
# Only load indexes for relevant documents
for doc_id in relevant_docs[:top_k]:
    index = load_doc_index(doc_id)  # Small, fast (1-10MB each)
    results.extend(index.query(query))
```

### 3. Merge and Return
```python
# Combine results from multiple small indexes
merged_results = merge_and_rank(results)
return merged_results
```

## Performance Comparison

| Metric | Unified Index | Per-Doc Indexes |
|--------|---------------|-----------------|
| **Startup time** | 60+ seconds | 0 seconds (no loading) |
| **First query** | Instant (already loaded) | 0.5-2 seconds (load relevant) |
| **Subsequent queries** | Instant | 0.5-2 seconds (load relevant) |
| **Memory usage (100 docs)** | ~600MB | ~5-20MB (only loaded docs) |
| **Memory usage (1000 docs)** | ~6GB | ~5-20MB (same!) |
| **Update single doc** | Rebuild all (slow) | Rebuild one (fast) |
| **Cross-platform** | ✅ (with FAISS issues) | ✅ (fully compatible) |

## Implementation Changes

### 1. Index Creation (Per Document)

```python
def _index_single_document(self, db_doc: DBDocument):
    """Create a separate index for a single document."""
    doc_id = self._generate_doc_id(db_doc.path)
    doc_index_dir = os.path.join(
        self.doc_indexes_dir,
        f"{doc_id}_{sanitize_filename(db_doc.name)}"
    )
    
    # Load single document
    reader = SimpleDirectoryReader(input_files=[db_doc.path], ...)
    docs = reader.load_data()
    
    # Create small index for this document only
    index = VectorStoreIndex.from_documents(
        docs,
        embed_model=self.embedding,
    )
    
    # Save to dedicated directory
    index.storage_context.persist(persist_dir=doc_index_dir)
    
    # Update registry
    self._update_registry(doc_id, db_doc, len(docs))
```

### 2. Query-Time Loading

```python
def query_documents(self, query: str, top_k_docs: int = 5):
    """Query across multiple document indexes (lazy loading)."""
    registry = self._load_registry()
    
    # Optional: Pre-filter by metadata/keywords
    relevant_doc_ids = self._get_relevant_docs(query, registry, top_k_docs)
    
    results = []
    for doc_id in relevant_doc_ids:
        # Load index on-demand (small, fast)
        index = self._load_doc_index(doc_id)
        if index:
            # Query this document's index
            doc_results = index.as_query_engine().query(query)
            results.append(doc_results)
    
    return self._merge_results(results)
```

### 3. Registry Management

```python
def _load_registry(self) -> Dict:
    """Load lightweight index registry (fast)."""
    registry_path = os.path.join(self.cache_dir, "index_registry.json")
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            return json.load(f)
    return {"documents": {}, "version": "1.0"}

def _update_registry(self, doc_id: str, db_doc: DBDocument, chunk_count: int):
    """Update registry with document metadata."""
    registry = self._load_registry()
    registry["documents"][doc_id] = {
        "path": db_doc.path,
        "file_hash": self._calculate_file_hash(db_doc.path),
        "indexed_at": datetime.utcnow().isoformat(),
        "chunk_count": chunk_count,
        # ... more metadata
    }
    self._save_registry(registry)
```

## Advanced: Smart Document Selection

### Option 1: Keyword-Based Pre-filtering
```python
# Extract keywords during indexing
keywords = extract_keywords(document_text)  # RAKE, TextRank, etc.
registry["documents"][doc_id]["keywords"] = keywords

# At query time, match query keywords to doc keywords
relevant_docs = match_by_keywords(query, registry)
```

### Option 2: BM25 Pre-ranking
```python
# Use fast BM25 on document titles/summaries to pre-rank
from rank_bm25 import BM25Okapi

# Build BM25 index from registry summaries (very fast)
corpus = [doc["summary"] for doc in registry["documents"].values()]
bm25 = BM25Okapi(corpus)

# Get top-k most relevant documents
scores = bm25.get_scores(query_tokens)
top_docs = get_top_k(scores, k=5)
```

### Option 3: Load All (for comprehensive search)
```python
# For critical queries, can still load multiple indexes
# But each is small, so total time is manageable
for doc_id in all_doc_ids[:10]:  # Top 10 most relevant
    index = load_doc_index(doc_id)  # 10 x 0.1s = 1 second total
```

## Migration from Unified Index

### Automatic Migration

```python
def _migrate_to_per_doc_indexes(self):
    """Migrate from unified index to per-document indexes."""
    # 1. Mark all documents as unindexed
    all_docs = DBDocument.objects.all()
    for doc in all_docs:
        DBDocument.objects.update(pk=doc.id, indexed=False)
    
    # 2. Remove old unified index
    if os.path.exists(self.old_unified_index_dir):
        shutil.rmtree(self.old_unified_index_dir)
    
    # 3. User rebuilds with new architecture
    self.logger.info(
        "Migrated to per-document index architecture. "
        "Please rebuild index using 'Index All' button."
    )
```

## Edge Cases & Considerations

### 1. Very Large Documents
- **Issue**: Single document = 100s of pages
- **Solution**: Split into sub-indexes by chapter/section

### 2. Very Small Documents
- **Issue**: 1000s of tiny files (each < 1 page)
- **Solution**: Group into batches of 10-20 docs per index

### 3. Cross-Document Search
- **Issue**: Need to search all documents
- **Solution**: Load top-N most relevant (by metadata/BM25), or implement two-phase retrieval

### 4. Memory Constraints
- **Issue**: Limited RAM
- **Solution**: Load indexes sequentially, unload after query (already done with lazy loading)

## Performance Targets

| Scenario | Target Performance |
|----------|-------------------|
| App startup | < 1 second (no index loading) |
| First query (cold) | 1-3 seconds (load relevant indexes) |
| Subsequent queries | 0.5-2 seconds |
| Index single document | 10-30 seconds (one-time per doc) |
| Index 100 documents | 15-45 minutes (parallelizable) |
| Memory usage (1000 docs) | < 100MB (only loaded indexes) |

## Why This is Better Than FAISS

1. ✅ **Cross-platform**: No conda, no platform-specific builds
2. ✅ **No dependencies**: Uses standard LlamaIndex
3. ✅ **Zero startup time**: No index loading required
4. ✅ **Better scaling**: Memory usage stays constant regardless of total docs
5. ✅ **Flexible**: Can load 1 doc or 100 docs as needed
6. ✅ **Easy updates**: Reindex single docs without affecting others
7. ✅ **Metadata-aware**: Can pre-filter by date, type, tags, etc.

## Implementation Priority

**Phase 1**: Core per-document indexing
- [x] Design architecture
- [ ] Implement `_index_single_document()`
- [ ] Implement registry management
- [ ] Implement lazy loading
- [ ] Migration logic

**Phase 2**: Query optimization
- [ ] Implement metadata pre-filtering
- [ ] Implement result merging/ranking
- [ ] Add caching for frequently accessed indexes

**Phase 3**: Advanced features
- [ ] BM25 pre-ranking
- [ ] Keyword extraction
- [ ] Parallel indexing
- [ ] Document grouping for small files

## Conclusion

Per-document indexes with lazy loading provide:
- **Better performance** than unified index (0s startup vs 60s)
- **Better scalability** than FAISS (constant memory vs linear growth)
- **Better compatibility** than FAISS (pure Python vs platform-specific)
- **Better flexibility** than either (selective loading, easy updates)

This is the right architecture for a local-first RAG system that needs to scale to thousands of documents.
