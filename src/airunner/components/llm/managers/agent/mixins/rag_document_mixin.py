"""RAG document database operations and metadata management.

This mixin provides:
- Document database queries (active, unindexed)
- Document status tracking
- Metadata extraction and caching
- File hash calculation
"""

import os
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime

from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)


class RAGDocumentMixin:
    """Mixin for RAG document database operations."""

    def _get_unindexed_documents(self) -> List[DBDocument]:
        """Get list of documents that need to be indexed.

        Checks both indexed flag and file hash to detect changes.

        Returns:
            List of DBDocument instances that need indexing
        """
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

        Only returns IDs for documents that are both active and indexed,
        and whose files still exist on disk.

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
            List of document filenames (basenames, not full paths)
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
        """Mark a document as indexed in the database with current hash.

        Updates the document's indexed flag, file hash, timestamp, and size.

        Args:
            file_path: Path to the document file
        """
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
        """Extract metadata for a document.

        Uses cache to avoid repeated extraction. Includes file path,
        name, type, and database metadata if available.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing document metadata
        """
        if file_path in self._doc_metadata_cache:
            return self._doc_metadata_cache[file_path]

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

        self._doc_metadata_cache[file_path] = metadata
        return metadata

    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA256 hash of a file for change detection.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal SHA256 hash string, or None on error
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(
                f"Error calculating file hash for {file_path}: {e}"
            )
            return None

    def _generate_doc_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path.

        Uses MD5 hash of the normalized absolute path.

        Args:
            file_path: Path to the document file

        Returns:
            Hexadecimal MD5 hash string (document ID)
        """
        normalized_path = os.path.normpath(os.path.abspath(file_path))
        return hashlib.md5(normalized_path.encode()).hexdigest()
