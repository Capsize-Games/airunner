# Local E5 embedding identity and index migration

Status: identity checks and staged reindex path are implemented with fake-based tests. No real model has been loaded or measured. The pinned model metadata and associated upstream MIT notice are preserved in an owner-controlled private copy. Model execution and end-to-end acceptance remain unrun.

## Baseline findings before implementation

`RAGPropertiesMixin.embedding` checks required files by presence and minimum size, then constructs `HuggingFaceEmbeddings` from the local E5 directory. It configures `trust_remote_code=False` and uses `local_files_only` from the application setting, but does not verify file contents or pin the Hugging Face revision. The configured local files match model commit `4dc6d853a804b9c8886ede6dda8a073b7dc08a81` for the weight and the required upstream config/tokenizer files; two additional local metadata files differ from or are absent in that commit.

The Ollama fallback accepts an initialized embedder based on its `model_name` resolving to the configured directory. It then assigns the constant identity `intfloat/e5-large@main`, even though the path does not identify the revision or bytes. Directly injected `LocalEmbeddingClient` instances have their own explicit identity and remain a supported path.

`DocumentVectorIndex` persists two files: `documents.json` (chunk text and metadata) and `embeddings.npy` (normalized vectors). It writes no embedding identity. Load accepts either file pair as current. Searches embed a query without checking which model produced stored vectors. `MultiIndexRetriever` embeds once and passes the query vector into both the unified and per-document indexes. The exact E5 model card requires `query: ` on query text and `passage: ` on corpus text for asymmetric retrieval; there are no such prefixes in the current RAG path.

## Identity record

Add a frozen, neutral E5 identity value in `airunner_services.runtimes.e5_model_identity` with:

- model id `intfloat/e5-large`;
- immutable source revision `4dc6d853a804b9c8886ede6dda8a073b7dc08a81`;
- embedding dimension `1024`;
- a SHA-256 for every model file consumed by the loader, including the 1,340,616,616-byte safetensors file;
- a deterministic digest of the sorted file manifest and the E5 input-prefix contract version.

Hash files in bounded chunks once before model construction. Reject missing, changed, non-regular, symlinked, or unexpected model inputs before the loader runs. Do not hash weights on embedding requests. The verifier returns the identity only after every digest matches. After construction, bind that verified identity to an E5 adapter that owns `embed_query` and `embed_documents`; wrappers must receive the verified identity, never derive it from a path.

The default identity uses the canonical runtime files from the pinned upstream revision. The local `config_sentence_transformers.json` is an unreviewed extra and the normal verifier rejects it; do not bake its owner-local digest into the product manifest. Any future reviewed overlay needs a separately explicit manifest. The local README is not a loader input; it remains part of the separate license-notice review and must not be replaced with invented legal text.

The normal RAG loader must set `local_files_only=True` and `trust_remote_code=False` for this pinned local E5 path. A missing or mismatched artifact returns a stable unavailable/review-needed result. The existing asynchronous generic model-download flow is not proof of the pinned revision and must not bypass this verifier.

## Text encoding contract

The verified E5 adapter adds `query: ` exactly once in `embed_query` and `passage: ` exactly once in `embed_documents`. It leaves stored chunk text and metadata unchanged. Ollama document embedding calls use the document method. Directly injected `LocalEmbeddingClient` instances preserve their current explicit identity behavior and do not receive a path-derived E5 label.

## Index format and mismatch handling

Add a versioned `embedding_identity.json` sidecar to newly written RAG indexes. It records the identity fields above. Validate row alignment (`len(documents) == embeddings.shape[0]`) and dimensions before an index can be searched or persisted. Propagate the query identity through both normal and multi-index retrieval so every index can compare its stored identity with the query vector's identity.

Existing index data stays in place. An index without an identity sidecar is legacy/unknown, not presumed to be E5 at the new revision. A verified local E5 query against a missing or different identity raises an explicit `reindex_required` result before ranking. Load/startup does not delete, relabel, or rewrite stored documents or vectors. The existing explicit remote-embedding opt-in can still use an unidentified embedder with an unidentified index; that compatibility path does not establish model provenance and cannot search an identity-bearing local E5 index.

The explicit `POST /api/v1/llm/rag/reindex` operation accepts up to 64 selected paths and passes through the same authentication, admission middleware, path validation, cancellation endpoint, and status tracker as normal indexing. A shared job token serializes all-index, selected-index, and reindex work; a competing HTTP request gets `409 rag_index_busy` without changing the running job's status or cancellation state. The route waits for a token-specific worker-start acknowledgement; if no listener starts the job, it releases that reservation and returns `503 rag_index_worker_unavailable`. A late callback cannot claim an expired token. Cancellation is observed between documents, so the current document finishes its staged operation before the batch stops. Reindex requires an existing persisted index and re-reads the source file; it does not re-embed old stored chunks. It captures the source SHA-256 and size before ingestion, checks that the digest is unchanged after embedding and before promotion, and uses that same digest/size for registry and database metadata. It embeds all chunks under a verified identity into a sibling staging directory, reloads the candidate, and checks document payload, vector contents, identity, row count, and dimension before promotion. The registry `chunk_count` records split chunks. The old index is renamed to a retained sibling backup, then the staged directory is promoted. Promotion failure restores the old directory; metadata failure restores registry bytes and database fields and rolls the previous index back, while retaining the failed candidate directory for diagnosis. Successful reindex retains the old index backup. No query or startup path invokes this operation.

## Implementation phases

1. **Verified model identity:** add the immutable identity/manifest verifier and prefix adapter; wire RAG construction to verify before loading; make the Ollama fallback require a verified identity. Keep direct injection compatibility.
2. **Indexed identity:** add the index identity sidecar, row/dimension checks, identity propagation through `DocumentIndexRetriever` and `MultiIndexRetriever`, and explicit legacy/mismatch errors.
3. **Explicit reindex path:** implemented through the selected-path route and worker. It rebuilds from the source document through staging and retains the prior index on success or failure. It does not run automatically from a query or startup.
4. **Acceptance:** run deterministic tests with fake files and embedders only. A separate later acceptance run can use the owner-local model in CPU mode after the exact runtime dependencies and model inputs pass their review and capacity checks.

The latest integrated deterministic selection passed 53 tests with four existing datetime deprecation warnings. It covers the model manifest, embedding-space serialization, persisted identity, staged replacement/rollback, worker admission, routes, and Ollama fallback. These tests use synthetic model files and fake embedders; they do not prove real inference or retrieval quality. Pyflakes reported no findings in the changed production modules.

## Required tests and exclusions

- Correct file set verifies to the immutable revision; missing, modified, symlinked, and unexpected inputs fail before the loader factory is called.
- One-time verification produces a stable manifest digest. Repeated embedding calls do not rehash model files.
- Query and document prefixes are applied once, and original stored text is unchanged.
- An initialized object with only a matching path is refused by the Ollama fallback; a verified adapter succeeds; a directly injected `LocalEmbeddingClient` remains supported.
- New index identity round-trips. Legacy/no-identity and mismatched identities fail with `reindex_required` without changing documents or vectors. Row-count mismatch fails before index mutation. Staged reindex preserves old data on failure and only switches after validation.
- No test loads the real model, downloads weights, changes the owner model directory, installs packages, or asserts legal notice approval.

The canonical model card declares MIT and documents the E5 prefixes, 512-token maximum, and English-only limitation at the pinned revision: <https://huggingface.co/intfloat/e5-large/blob/4dc6d853a804b9c8886ede6dda8a073b7dc08a81/README.md>. The repository's pinned file list has no LICENSE/NOTICE file, and the local README is a short stub. The pinned checkpoint metadata and LFS pointers are retained in an owner-controlled private copy with Actions disabled. The associated E5 project MIT notice is retained separately from `microsoft/unilm` commit `31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd`; its source is recorded without asserting an additional checkpoint copyright statement. Owner-local weights were hash-matched and remain unchanged. This records static input evidence, not runtime or retrieval-quality acceptance.
