"""RAG index management and registry operations."""

import os
import json
import shutil
from typing import Optional, Dict, Any
from datetime import datetime

from airunner_model.models.document import (
    Document as DBDocument,
)
from airunner_services.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)


class RAGIndexManagementMixin:
    """Mixin for RAG index management and registry operations."""

    def _load_registry(self) -> Dict[str, Any]:
        """Load the index registry from disk.

        Returns:
            Registry dictionary with documents and version
        """
        for registry_path in self._registry_candidates():
            if not os.path.exists(registry_path):
                continue
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                self.logger.info(
                    f"Loaded registry with {len(registry.get('documents', {}))} documents"
                )
                return registry
            except Exception as e:
                self.logger.error(f"Error loading registry: {e}")

        return {"documents": {}, "version": "2.0"}

    def _save_registry(self):
        """Save the index registry to disk."""
        try:
            os.makedirs(self.doc_indexes_dir, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._index_registry, f, indent=2)
            self.logger.debug("Registry saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving registry: {e}")

    def _registry_candidates(self) -> list[str]:
        paths = [self.registry_path]
        legacy_path = os.path.join(
            self.legacy_doc_indexes_dir,
            "index_registry.json",
        )
        if legacy_path not in paths:
            paths.append(legacy_path)
        return paths

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

    def _get_legacy_doc_index_dir(self, doc_id: str, file_path: str) -> str:
        """Return the legacy directory path for a document index."""
        filename = os.path.basename(file_path)
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in filename
        )
        return os.path.join(
            self.legacy_doc_indexes_dir,
            f"{doc_id}_{safe_filename}",
        )

    def _load_doc_index(self, doc_id: str) -> Optional[DocumentVectorIndex]:
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
            index_dir = self._resolve_doc_index_dir(doc_id, doc_info["path"])
            if index_dir is None:
                return None

            doc_index = DocumentVectorIndex.load(index_dir)

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

    def _resolve_doc_index_dir(
        self,
        doc_id: str,
        file_path: str,
    ) -> Optional[str]:
        candidates = [
            self._get_doc_index_dir(doc_id, file_path),
            self._get_legacy_doc_index_dir(doc_id, file_path),
        ]
        for index_dir in candidates:
            if DocumentVectorIndex.is_persisted(index_dir):
                return index_dir
        self.logger.warning(f"Index directory not found for {file_path}")
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
                self._index.persist(self.storage_persist_dir)
                self.logger.info("Unified index saved to storage")
            except Exception as e:
                self.logger.error(f"Error saving index: {e}")

    def _load_index(self) -> Optional[DocumentVectorIndex]:
        """Load the unified index from disk (legacy).

        Returns:
            VectorStoreIndex or None if loading fails
        """
        for persist_dir in self._index_candidates():
            if not DocumentVectorIndex.is_persisted(persist_dir):
                continue
            try:
                index = DocumentVectorIndex.load(persist_dir)
                self.logger.info("Unified index loaded from storage")
                return index
            except Exception as e:
                self.logger.error(f"Error loading index: {e}")
        return None

    def _index_candidates(self) -> list[str]:
        paths = [self.storage_persist_dir]
        if self.legacy_storage_persist_dir not in paths:
            paths.append(self.legacy_storage_persist_dir)
        return paths

    def _detect_old_unified_index(self) -> Optional[str]:
        """Check if there's an old unified index that needs migration.

        Returns:
            Path to the old unified index directory if it exists
        """
        for storage_dir in self._index_candidates():
            docstore_path = os.path.join(storage_dir, "docstore.json")
            if os.path.exists(docstore_path):
                return storage_dir
        return None

    def _migrate_from_unified_index(self, storage_dir: str):
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
            migrated = 0
            for document in DBDocument.objects.all():
                if not os.path.exists(document.path):
                    continue
                if self._index_single_document(document):
                    migrated += 1

            archive_path = (
                f"{storage_dir}_archived_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.move(storage_dir, archive_path)
            self.logger.info(
                f"Migrated {migrated} documents and archived {storage_dir}"
            )
        except Exception as e:
            self.logger.error(f"Error during migration: {e}")

    def _detect_and_migrate_old_index(self):
        """Detect and migrate old unified index if present."""
        storage_dir = self._detect_old_unified_index()
        if storage_dir:
            self.logger.info("Old unified index detected, migrating...")
            self._migrate_from_unified_index(storage_dir)

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
