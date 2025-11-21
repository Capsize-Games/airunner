"""RAG index management and registry operations.

This mixin provides:
- Index registry loading/saving
- Per-document index CRUD operations
- Index directory management
- Cache validation
- Legacy index migration
"""

import os
import json
import shutil
from typing import Optional, Dict, Any
from datetime import datetime

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)


class RAGIndexManagementMixin:
    """Mixin for RAG index management and registry operations."""

    def _load_registry(self) -> Dict[str, Any]:
        """Load the index registry from disk.

        Returns:
            Registry dictionary with documents and version
        """
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
                json.dump(self._index_registry, f, indent=2)
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
        """Get the directory path for a document's index.

        Args:
            doc_id: Document ID
            file_path: Path to the document file

        Returns:
            Absolute path to the document's index directory
        """
        filename = os.path.basename(file_path)
        # Sanitize filename for directory name
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in filename
        )
        return os.path.join(self.doc_indexes_dir, f"{doc_id}_{safe_filename}")

    def _load_doc_index(self, doc_id: str) -> Optional[VectorStoreIndex]:
        """Lazy load a document's index from disk.

        Args:
            doc_id: Document ID

        Returns:
            VectorStoreIndex or None if loading fails
        """
        # Check cache first
        if doc_id in self._doc_indexes_cache:
            return self._doc_indexes_cache[doc_id]

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
            self._doc_indexes_cache[doc_id] = doc_index
            self._loaded_doc_ids.append(doc_id)

            self.logger.debug(
                f"Loaded index for document {doc_info['file_name']}"
            )
            return doc_index

        except Exception as e:
            self.logger.error(f"Error loading index for {doc_id}: {e}")
            return None

    def _unload_doc_index(self, doc_id: str):
        """Unload a document's index from memory.

        Args:
            doc_id: Document ID to unload
        """
        if doc_id in self._doc_indexes_cache:
            del self._doc_indexes_cache[doc_id]
            if doc_id in self._loaded_doc_ids:
                self._loaded_doc_ids.remove(doc_id)
            self.logger.debug(f"Unloaded index for document {doc_id}")

    def _save_index(self):
        """Save the unified index to disk (legacy).

        This method is kept for backward compatibility with old unified index.
        """
        if self._index:
            try:
                os.makedirs(self.storage_persist_dir, exist_ok=True)
                self._index.storage_context.persist(
                    persist_dir=self.storage_persist_dir
                )
                self.logger.info("Unified index saved to storage")
            except Exception as e:
                self.logger.error(f"Error saving index: {e}")

    def _load_index(self) -> Optional[VectorStoreIndex]:
        """Load the unified index from disk (legacy).

        Returns:
            VectorStoreIndex or None if loading fails
        """
        if os.path.exists(self.storage_persist_dir):
            try:
                storage_context = StorageContext.from_defaults(
                    persist_dir=self.storage_persist_dir
                )
                index = load_index_from_storage(storage_context)
                self.logger.info("Unified index loaded from storage")
                return index
            except Exception as e:
                self.logger.error(f"Error loading index: {e}")
        return None

    def _detect_old_unified_index(self) -> bool:
        """Check if there's an old unified index that needs migration.

        Returns:
            True if old unified index exists
        """
        docstore_path = os.path.join(self.storage_persist_dir, "docstore.json")
        return os.path.exists(docstore_path)

    def _migrate_from_unified_index(self):
        """Migrate from old unified index to per-document architecture.

        This is a one-time migration that:
        1. Loads the old unified index
        2. Extracts documents
        3. Creates per-document indexes
        4. Archives the old index
        """
        self.logger.info(
            "Starting migration from unified index to per-document indexes"
        )

        try:
            # Load old unified index
            old_index = self._load_index()
            if not old_index:
                self.logger.warning("Could not load old index for migration")
                return

            # Get all documents from unified index
            # Note: This requires accessing internal docstore
            docstore = old_index.docstore
            all_docs = list(docstore.docs.values())

            self.logger.info(f"Found {len(all_docs)} documents in old index")

            # Group documents by file_path
            docs_by_file: Dict[str, list] = {}
            for doc in all_docs:
                file_path = doc.metadata.get("file_path")
                if file_path:
                    if file_path not in docs_by_file:
                        docs_by_file[file_path] = []
                    docs_by_file[file_path].append(doc)

            # Create per-document indexes
            for file_path, file_docs in docs_by_file.items():
                try:
                    doc_id = self._generate_doc_id(file_path)

                    # Create index for this file
                    doc_index = VectorStoreIndex.from_documents(
                        file_docs,
                        embed_model=self.embedding,
                        show_progress=False,
                    )

                    # Save to new location
                    index_dir = self._get_doc_index_dir(doc_id, file_path)
                    os.makedirs(index_dir, exist_ok=True)
                    doc_index.storage_context.persist(persist_dir=index_dir)

                    # Update registry
                    self._update_registry_entry(
                        doc_id, file_path, len(file_docs)
                    )

                    self.logger.info(f"Migrated {file_path}")

                except Exception as e:
                    self.logger.error(f"Error migrating {file_path}: {e}")

            # Archive old unified index
            archive_path = f"{self.storage_persist_dir}_archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(self.storage_persist_dir, archive_path)

            self.logger.info(
                f"Migration complete. Old index archived to {archive_path}"
            )

        except Exception as e:
            self.logger.error(f"Error during migration: {e}")

    def _detect_and_migrate_old_index(self):
        """Detect and migrate old unified index if present."""
        if self._detect_old_unified_index():
            self.logger.info("Old unified index detected, migrating...")
            self._migrate_from_unified_index()

    def _validate_cache_integrity(self) -> bool:
        """Validate that cached indexes match registry and disk state.

        Returns:
            True if cache is valid
        """
        if self._cache_validated:
            return True

        try:
            # Check all documents in registry
            for doc_id, doc_info in self.index_registry["documents"].items():
                file_path = doc_info["path"]

                # Check if file still exists
                if not os.path.exists(file_path):
                    self.logger.warning(
                        f"Indexed file no longer exists: {file_path}"
                    )
                    continue

                # Check if index directory exists
                index_dir = self._get_doc_index_dir(doc_id, file_path)
                if not os.path.exists(index_dir):
                    self.logger.warning(
                        f"Index directory missing for {file_path}"
                    )
                    continue

                # Check file hash to detect changes
                current_hash = self._calculate_file_hash(file_path)
                if current_hash != doc_info.get("file_hash"):
                    self.logger.info(
                        f"File changed since indexing: {file_path}"
                    )

            self._cache_validated = True
            return True

        except Exception as e:
            self.logger.error(f"Error validating cache integrity: {e}")
            return False
