"""RAG index management and registry operations."""

import os
import json
import shutil
import copy
import tempfile
import uuid
import base64
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

_HEX_UUID = re.compile(r"^[0-9a-f]{32}$")

from airunner_services.database.models.document import (
    Document as DBDocument,
)
from airunner_services.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)
from airunner_services.database.session import session_scope
from airunner_services.llm.managers.agent.mixins.runtime_activity import (
    runtime_activity_locked,
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

    @runtime_activity_locked
    def delete_document_records(self, document_ids: list[int]) -> dict[str, Any]:
        """Delete rows and generated indexes transactionally, preserving sources."""
        requested_ids = tuple(dict.fromkeys(int(value) for value in document_ids))
        if not requested_ids:
            return {"deleted": True, "count": 0, "cleanup_pending": []}

        self._retry_pending_index_cleanup()
        registry_path = os.path.abspath(self.registry_path)
        _validate_generated_index_path(registry_path, (self.doc_indexes_dir,))
        registry_before = copy.deepcopy(self.index_registry)
        registry_before_bytes = (
            Path(registry_path).read_bytes()
            if os.path.isfile(registry_path)
            else None
        )
        if registry_before_bytes is not None and len(registry_before_bytes) > 6 * 1024 * 1024:
            raise ValueError("registry snapshot exceeds deletion journal limit")
        operation_id = uuid.uuid4().hex
        removed_doc_ids: list[str] = []
        try:
            with session_scope() as session:
                records = (
                    session.query(DBDocument)
                    .filter(DBDocument.id.in_(requested_ids))
                    .all()
                )
                record_ids = {int(record.id) for record in records}
                if record_ids != set(requested_ids):
                    raise LookupError("one or more documents were not found")

                next_registry = copy.deepcopy(registry_before)
                document_records = []
                directory_entries = []
                planned_index_paths = set()
                for record in records:
                    doc_id = self._generate_doc_id(record.path)
                    removed_doc_ids.append(doc_id)
                    document_records.append(
                        {"id": int(record.id), "path": os.path.abspath(record.path), "doc_id": doc_id}
                    )
                    for index_path in (
                        self._get_doc_index_dir(doc_id, record.path),
                        self._get_legacy_doc_index_dir(doc_id, record.path),
                    ):
                        index_path = os.path.abspath(index_path)
                        if index_path in planned_index_paths:
                            continue
                        planned_index_paths.add(index_path)
                        if not os.path.lexists(index_path):
                            continue
                        _validate_generated_index_path(
                            index_path,
                            (self.doc_indexes_dir, self.legacy_doc_indexes_dir),
                        )
                        if not os.path.isdir(index_path):
                            raise ValueError("generated index path is not a directory")
                        staged_path = f"{index_path}.delete-pending-{uuid.uuid4().hex}"
                        directory_entries.append(
                            {
                                "doc_id": doc_id,
                                "source_path": os.path.abspath(record.path),
                                "original": os.path.abspath(index_path),
                                "staged": os.path.abspath(staged_path),
                            }
                        )
                    next_registry.setdefault("documents", {}).pop(doc_id, None)

                operation = {
                    "operation_id": operation_id,
                    "phase": "preparing",
                    "document_records": document_records,
                    "directories": directory_entries,
                    "registry_path": registry_path,
                    "registry_before_b64": (
                        base64.b64encode(registry_before_bytes).decode("ascii")
                        if registry_before_bytes is not None
                        else None
                    ),
                }
                self._store_deletion_operation(operation)
                for entry in directory_entries:
                    os.replace(entry["original"], entry["staged"])
                _write_json_atomically(registry_path, next_registry)
                self._index_registry = next_registry
                for record in records:
                    session.delete(record)
                session.flush()
        except Exception:
            try:
                self._retry_pending_index_cleanup()
                self._index_registry = registry_before
            except Exception as rollback_exc:
                raise RuntimeError(
                    f"document deletion failed; recovery journal retained: {rollback_exc}"
                ) from rollback_exc
            raise

        operation["phase"] = "committed"
        try:
            self._store_deletion_operation(operation)
        except Exception as exc:
            # The preparing journal remains recoverable from the committed DB
            # state. Keep the in-memory registry aligned with the DB commit.
            self.logger.error("Could not mark deletion journal committed: %s", exc)

        self._index_registry = next_registry
        self._invalidate_deleted_document_cache(set(removed_doc_ids))
        try:
            pending = self._retry_pending_index_cleanup()
        except Exception:
            # The DB delete has committed. Preserve the durable journal as the
            # cleanup owner and report the incomplete recovery to the caller.
            return {
                "deleted": True,
                "count": len(requested_ids),
                "cleanup_pending": [self._pending_index_cleanup_path()],
            }
        cleanup_pending = pending.get(operation_id, [])
        return {
            "deleted": True,
            "count": len(requested_ids),
            "cleanup_pending": cleanup_pending,
        }

    def _invalidate_deleted_document_cache(self, deleted_doc_ids: set[str]) -> None:
        """Remove deleted chunks from live caches before another query can run."""
        for doc_id in deleted_doc_ids:
            self._unload_doc_index(doc_id)
        if self._index is not None:
            retained = [
                position
                for position, document in enumerate(self._index.documents)
                if document.metadata.get("doc_id") not in deleted_doc_ids
            ]
            if len(retained) != len(self._index.documents):
                self._index = DocumentVectorIndex(
                    [self._index.documents[position] for position in retained],
                    self._index.embeddings[retained],
                    self._index.embedding_identity,
                )
        self._retriever = None

    def _pending_index_cleanup_path(self) -> str:
        return os.path.join(self.doc_indexes_dir, "pending_index_cleanup.json")

    def _read_deletion_journal(self) -> list[dict[str, Any]]:
        manifest_path = self._pending_index_cleanup_path()
        _validate_generated_index_path(manifest_path, (self.doc_indexes_dir,))
        if not os.path.lexists(manifest_path):
            return []
        if os.path.islink(manifest_path) or not os.path.isfile(manifest_path):
            raise ValueError("deletion journal must be a regular file")
        if os.path.getsize(manifest_path) > 16 * 1024 * 1024:
            raise ValueError("deletion journal exceeds the size limit")
        with open(manifest_path, "r", encoding="utf-8") as stream:
            journal = json.load(stream)
        if (
            not isinstance(journal, dict)
            or journal.get("schema_version") != 1
            or not isinstance(journal.get("operations"), list)
            or len(journal["operations"]) > 128
        ):
            raise ValueError("deletion journal schema is invalid")
        if not all(isinstance(operation, dict) for operation in journal["operations"]):
            raise ValueError("deletion journal operation is invalid")
        return journal["operations"]

    def _store_deletion_operation(self, operation: dict[str, Any]) -> None:
        operations = self._read_deletion_journal()
        operations = [
            item
            for item in operations
            if item.get("operation_id") != operation.get("operation_id")
        ]
        operations.append(operation)
        if len(operations) > 128:
            raise ValueError("too many pending deletion operations")
        _write_json_atomically(
            self._pending_index_cleanup_path(),
            {"schema_version": 1, "operations": operations},
        )


    def _retry_pending_index_cleanup(self) -> dict[str, list[str]]:
        """Recover interrupted deletions and retry committed staged cleanup."""
        operations = self._read_deletion_journal()
        pending_by_operation: dict[str, list[str]] = {}
        remaining = []
        for operation in operations:
            self._validate_deletion_operation(operation)
            operation_id = operation["operation_id"]
            document_ids = [int(record["id"]) for record in operation["document_records"]]
            with session_scope() as session:
                existing_ids = {
                    int(value)
                    for (value,) in session.query(DBDocument.id)
                    .filter(DBDocument.id.in_(document_ids))
                    .all()
                }
            if operation["phase"] == "preparing":
                if existing_ids and existing_ids != set(document_ids):
                    raise RuntimeError(
                        "deletion recovery found mixed database state; journal retained"
                    )
                if existing_ids == set(document_ids):
                    self._restore_deletion_operation(operation)
                    continue
                operation["phase"] = "committed"
                self._store_deletion_operation(operation)
            elif operation["phase"] != "committed":
                raise ValueError("deletion journal phase is invalid")

            if existing_ids:
                raise RuntimeError(
                    "committed deletion journal conflicts with database rows"
                )
            failures = self._purge_deletion_staging(operation)
            if failures:
                pending_by_operation[operation_id] = failures
                remaining.append(operation)
        self._write_deletion_journal(remaining)
        return pending_by_operation

    def _validate_deletion_operation(self, operation: dict[str, Any]) -> None:
        operation_id = operation.get("operation_id")
        if not isinstance(operation_id, str) or not _HEX_UUID.fullmatch(operation_id):
            raise ValueError("deletion journal operation ID is invalid")
        if operation.get("phase") not in {"preparing", "committed"}:
            raise ValueError("deletion journal phase is invalid")
        records = operation.get("document_records")
        directories = operation.get("directories")
        if (
            not isinstance(records, list)
            or not records
            or len(records) > 1000
            or not isinstance(directories, list)
            or len(directories) > 2000
        ):
            raise ValueError("deletion journal records are invalid")
        if os.path.abspath(str(operation.get("registry_path", ""))) != os.path.abspath(self.registry_path):
            raise ValueError("deletion journal registry path is invalid")
        _validate_generated_index_path(self.registry_path, (self.doc_indexes_dir,))
        snapshot = operation.get("registry_before_b64")
        if snapshot is not None:
            if not isinstance(snapshot, str) or len(snapshot) > 8 * 1024 * 1024:
                raise ValueError("deletion journal registry snapshot is invalid")
            try:
                decoded_snapshot = base64.b64decode(snapshot, validate=True)
                parsed_snapshot = json.loads(decoded_snapshot)
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    "deletion journal registry snapshot is invalid"
                ) from exc
            if (
                not isinstance(parsed_snapshot, dict)
                or not isinstance(parsed_snapshot.get("documents"), dict)
            ):
                raise ValueError("deletion journal registry snapshot schema is invalid")
        records_by_id = {}
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("deletion journal document record is invalid")
            record_id = record.get("id")
            source_path = record.get("path")
            doc_id = record.get("doc_id")
            if (
                not isinstance(record_id, int)
                or record_id <= 0
                or not isinstance(source_path, str)
                or not source_path
                or not os.path.isabs(source_path)
                or os.path.abspath(source_path) != source_path
                or not isinstance(doc_id, str)
                or self._generate_doc_id(source_path) != doc_id
                or record_id in records_by_id
            ):
                raise ValueError("deletion journal document identity is invalid")
            records_by_id[record_id] = (source_path, doc_id)
        for entry in directories:
            if not isinstance(entry, dict):
                raise ValueError("deletion journal directory entry is invalid")
            source_path = entry.get("source_path")
            doc_id = entry.get("doc_id")
            original = entry.get("original")
            staged = entry.get("staged")
            if not isinstance(source_path, str) or not isinstance(doc_id, str):
                raise ValueError("deletion journal directory identity is invalid")
            if not os.path.isabs(source_path) or os.path.abspath(source_path) != source_path:
                raise ValueError("deletion journal source path is invalid")
            if (source_path, doc_id) not in records_by_id.values():
                raise ValueError("deletion journal directory has no matching document")
            canonical = {
                os.path.abspath(self._get_doc_index_dir(doc_id, source_path)),
                os.path.abspath(self._get_legacy_doc_index_dir(doc_id, source_path)),
            }
            if not isinstance(original, str) or os.path.abspath(original) not in canonical:
                raise ValueError("deletion journal original path is invalid")
            if not isinstance(staged, str):
                raise ValueError("deletion journal staged path is invalid")
            staged = os.path.abspath(staged)
            if (
                os.path.dirname(staged) != os.path.dirname(original)
                or not os.path.basename(staged).startswith(
                    os.path.basename(original) + ".delete-pending-"
                )
                or not _HEX_UUID.fullmatch(
                    os.path.basename(staged).rsplit(".delete-pending-", 1)[-1]
                )
            ):
                raise ValueError("deletion journal staged suffix is invalid")
            root = (
                self.doc_indexes_dir
                if os.path.dirname(original) == os.path.abspath(self.doc_indexes_dir)
                else self.legacy_doc_indexes_dir
            )
            _validate_generated_index_path(original, (root,))
            _validate_generated_index_path(staged, (root,))

    def _restore_deletion_operation(self, operation: dict[str, Any]) -> None:
        snapshot = operation.get("registry_before_b64")
        _restore_registry(
            self.registry_path,
            base64.b64decode(snapshot, validate=True) if snapshot is not None else None,
        )
        self._index_registry = None
        for entry in reversed(operation["directories"]):
            original = entry["original"]
            staged = entry["staged"]
            if not os.path.lexists(staged):
                continue
            if os.path.lexists(original):
                raise RuntimeError("both original and staged index paths exist")
            os.replace(staged, original)

    def _purge_deletion_staging(self, operation: dict[str, Any]) -> list[str]:
        failures = []
        for entry in operation["directories"]:
            staged = entry["staged"]
            if not os.path.lexists(staged):
                continue
            try:
                if os.path.isdir(staged) and not os.path.islink(staged):
                    shutil.rmtree(staged)
                else:
                    os.unlink(staged)
            except OSError:
                failures.append(staged)
        return failures

    def _write_deletion_journal(self, operations: list[dict[str, Any]]) -> None:
        path = self._pending_index_cleanup_path()
        _validate_generated_index_path(path, (self.doc_indexes_dir,))
        if operations:
            _write_json_atomically(
                path, {"schema_version": 1, "operations": operations}
            )
        elif os.path.exists(path):
            os.unlink(path)

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
        *,
        file_hash: Optional[str] = None,
    ):
        """Update a document entry in the registry.

        Args:
            doc_id: Document ID
            file_path: Path to document
            chunk_count: Number of chunks
        """
        file_hash = (
            self._calculate_file_hash(file_path) if file_hash is None else file_hash
        )
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


def _restore_registry(registry_path: str, registry_before_bytes: bytes | None) -> None:
    if registry_before_bytes is None:
        if os.path.exists(registry_path):
            os.unlink(registry_path)
        return
    directory = os.path.dirname(registry_path)
    os.makedirs(directory, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=directory, prefix=".registry-rollback-", delete=False
    ) as stream:
        stream.write(registry_before_bytes)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    os.replace(temporary, registry_path)


def _write_json_atomically(path: str, payload: Any) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=directory,
        prefix=".registry-update-",
        delete=False,
    ) as stream:
        json.dump(payload, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    os.replace(temporary, path)




def _validate_generated_index_path(path: str, roots: tuple[str, ...]) -> None:
    """Require a generated index path directly under a configured index root."""
    if os.path.islink(path):
        raise ValueError("generated index path may not be a symlink")
    parent = os.path.realpath(os.path.dirname(path))
    if any(parent == os.path.realpath(root) for root in roots):
        return
    raise ValueError("generated index path escapes configured roots")
