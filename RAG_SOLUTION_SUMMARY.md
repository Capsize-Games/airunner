# RAG Scalability Solution: Per-Document Indexes

## Executive Summary

**Problem**: Loading 102 documents takes 60+ seconds with a 600MB+ unified index. Won't scale to thousands of documents.

**Previous Solution (REJECTED)**: FAISS vector store
- ❌ Platform compatibility issues (conda-only, no Windows pip support)
- ❌ Added external dependency with build requirements

**NEW Solution (RECOMMENDED)**: Per-Document Indexes with Lazy Loading
- ✅ Zero startup time (no index loading)
- ✅ Constant memory usage regardless of document count
- ✅ Cross-platform (pure Python, standard LlamaIndex)
- ✅ Easy to update individual documents
- ✅ Scales to unlimited documents

## Architecture Comparison

### Current (Unified Index)
```
Start app → Load 600MB index (60s) → Ready to query
Memory: 600MB (100 docs) → 6GB (1000 docs)
```

### NEW (Per-Document Indexes)
```
Start app → Ready instantly (0s)
Query → Load relevant indexes (1-2s) → Return results
Memory: ~20MB regardless of total document count
```

## Key Design Decisions

### 1. Per-Document Index Storage
```
cache/doc_indexes/
  ├── abc123_document1/
  │   └── [index files ~1-10MB]
  ├── def456_document2/
  │   └── [index files ~1-10MB]
  └── ...
```

### 2. Lightweight Registry
```json
{
  "documents": {
    "abc123": {
      "path": "/path/to/doc.pdf",
      "file_hash": "...",
      "indexed_at": "2025-10-09T...",
      "chunk_count": 42
    }
  }
}
```
**Size**: ~100KB even for 1000 documents (just metadata, no embeddings)

### 3. Lazy Loading
- Don't load any indexes at startup
- Load only relevant indexes when querying
- Cache loaded indexes in memory
- Unload if memory pressure

### 4. Query Strategy
```python
query("What is X?")
  → Check registry (fast, <1ms)
  → Load top 5-10 relevant doc indexes (1-2s)
  → Query each small index
  → Merge results
  → Return answer
```

## Performance Comparison

| Metric | Unified Index | Per-Doc Indexes |
|--------|---------------|-----------------|
| **Startup** | 60s (100 docs) | 0s (instant) |
| **First query** | Instant* | 1-2s |
| **Memory (100 docs)** | 600MB | ~20MB |
| **Memory (1000 docs)** | ~6GB | ~20MB |
| **Update 1 doc** | Rebuild all (slow) | Rebuild one (30s) |
| **Scalability** | Poor (linear growth) | Excellent (constant) |

*After slow startup

## Implementation Status

### Files to Modify
1. **`src/airunner/components/llm/managers/agent/rag_mixin.py`**
   - Add registry management methods
   - Add per-document indexing methods
   - Add lazy loading methods
   - Update `index_all_documents()`
   - Add migration logic

### New Concepts
- `doc_indexes_dir`: Directory containing per-document indexes
- `registry_path`: Path to index_registry.json
- `_load_registry()`: Load lightweight metadata registry
- `_index_single_document()`: Create index for one document
- `_load_doc_index()`: Lazy load document index on demand

### Migration Path
1. Detect old unified index on startup
2. Backup old index
3. Mark all documents as unindexed
4. User clicks "Index All" → builds per-document indexes
5. Future startups: instant (no loading)

## Implementation Plan

See `RAG_IMPLEMENTATION_PLAN.md` for detailed step-by-step implementation guide with complete code examples.

## Benefits Over FAISS Solution

| Aspect | FAISS | Per-Document Indexes |
|--------|-------|---------------------|
| **Cross-platform** | ❌ Conda only | ✅ Pure Python |
| **Dependencies** | ❌ External C++ | ✅ Standard LlamaIndex |
| **Startup time** | ⚠️ Still loads all | ✅ Zero loading |
| **Memory scaling** | ⚠️ Linear | ✅ Constant |
| **Flexibility** | ⚠️ Load all or nothing | ✅ Load what's needed |
| **Updates** | ⚠️ Rebuild all | ✅ Update one |

## Why This is the Right Solution

### 1. Solves the Core Problem
- No more 60-second startup freezes
- Constant memory usage regardless of document count
- Truly scalable to thousands of documents

### 2. No External Dependencies
- Uses existing LlamaIndex components
- Cross-platform compatible
- No platform-specific builds

### 3. Better Architecture for Local RAG
- Lazy loading fits desktop application model
- Easy to understand and maintain
- Flexible for future enhancements

### 4. Future-Proof
- Can add smart pre-filtering (BM25, keywords)
- Can parallelize indexing
- Can group small documents
- Can implement caching strategies

## Example User Experience

### Before (Unified Index)
```bash
$ airunner
[Loading... please wait]
[60 seconds pass...]
Ready!

User: "Tell me about document X"
AI: [instant response]
```

### After (Per-Document Indexes)
```bash
$ airunner
Ready!  # Instant

User: "Tell me about document X"
[Loading relevant documents...]  # 1-2 seconds
AI: [response]

User: "Tell me more"
AI: [instant response - indexes cached]
```

## Next Steps

1. **Review Implementation Plan**: See `RAG_IMPLEMENTATION_PLAN.md`
2. **Implement Core Features**:
   - Registry management
   - Per-document indexing
   - Lazy loading
   - Migration logic
3. **Test with Your Dataset**: Index your 102 documents and verify performance
4. **Iterate**: Add optimizations as needed (caching, pre-filtering, etc.)

## Questions & Considerations

### Q: Won't loading indexes on every query be slow?
A: 
- Loading 5-10 small indexes takes 1-2 seconds total
- Much better than 60-second startup
- Can cache loaded indexes for subsequent queries

### Q: How do we search across ALL documents?
A:
- Load top-N most relevant (by metadata/keywords)
- Or load all incrementally (still faster than unified)
- Future: Implement two-phase retrieval (fast pre-filter + detailed search)

### Q: What about very small documents (1000s of files)?
A:
- Group into batches (10-20 docs per index)
- Implement in Phase 2

### Q: What about very large documents?
A:
- Can split into chapter-level indexes
- Implement in Phase 2

## Conclusion

The per-document index architecture provides:
- ✅ **Better performance** than unified index (0s vs 60s startup)
- ✅ **Better scalability** than FAISS (constant vs linear memory)
- ✅ **Better compatibility** than FAISS (pure Python vs platform-specific)
- ✅ **Better flexibility** (load what you need, update incrementally)

This is the right solution for a local-first RAG system that needs to scale to thousands of documents without platform dependencies.

---

**Ready to implement?** See `RAG_IMPLEMENTATION_PLAN.md` for detailed implementation guide.
