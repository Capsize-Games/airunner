"""LangChain-native document loading helpers for RAG ingestion."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from typing import Any, Callable, Optional

from bs4 import BeautifulSoup
from langchain_core.documents import Document

from airunner_services.zimreader import ZIMReader

MetadataLoader = Callable[[str], dict[str, Any]]


class DocumentBatchLoader:
    """Load multiple files into LangChain documents."""

    def __init__(
        self,
        input_files: list[str],
        metadata_loader: Optional[MetadataLoader] = None,
    ):
        self._input_files = list(input_files)
        self._metadata_loader = metadata_loader

    def load_data(self) -> list[Document]:
        """Load all configured files into documents."""
        return load_documents_from_files(
            self._input_files,
            self._metadata_loader,
        )


def load_documents_from_files(
    file_paths: list[str],
    metadata_loader: Optional[MetadataLoader] = None,
) -> list[Document]:
    """Load documents from the provided file paths."""
    documents: list[Document] = []
    for file_path in file_paths:
        documents.extend(load_documents_from_file(file_path, metadata_loader))
    return documents


def load_documents_from_file(
    file_path: str,
    metadata_loader: Optional[MetadataLoader] = None,
) -> list[Document]:
    """Load documents for a single file path.

    ``file_path`` may be a local filesystem path (dev) or a storage-backend
    key (object storage / uploaded docs). Keys are materialised to a local
    temp file for reading; metadata keeps the original path/key.
    """
    real_path, cleanup = _materialize_local(file_path)
    try:
        if not real_path or not os.path.exists(real_path):
            return []
        metadata = _resolve_metadata(file_path, metadata_loader)
        extension = os.path.splitext(file_path)[1].lower()
        loader = _FILE_LOADERS.get(extension, _load_text_document)
        return loader(real_path, metadata)
    finally:
        cleanup()


def _materialize_local(file_path: str):
    """Return ``(local_path, cleanup)`` for a path or storage-backend key.

    No-op for paths that already exist on disk (local/dev). For object
    storage keys, downloads to a temp file and returns a cleanup callable.
    """

    def _noop() -> None:
        return None

    if os.path.exists(file_path):
        return file_path, _noop
    try:
        from airunner_services.storage.backends import get_storage_backend

        backend = get_storage_backend()
        existing = backend.local_path(file_path)
        if existing:
            return existing, _noop
        if backend.exists(file_path):
            import tempfile

            data = backend.open(file_path)
            suffix = os.path.splitext(file_path)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(data)
            tmp.close()

            def _cleanup() -> None:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

            return tmp.name, _cleanup
    except Exception:
        pass
    return file_path, _noop


def extract_text_from_file(file_path: str) -> Optional[str]:
    """Extract plain text from a file for previews or indexing."""
    documents = load_documents_from_file(file_path)
    if not documents:
        return None
    return "\n\n".join(doc.page_content for doc in documents).strip()


def _resolve_metadata(
    file_path: str,
    metadata_loader: Optional[MetadataLoader],
) -> dict[str, Any]:
    if metadata_loader is None:
        return _default_metadata(file_path)
    return metadata_loader(file_path)


def _default_metadata(file_path: str) -> dict[str, Any]:
    file_name = os.path.basename(file_path)
    file_type = os.path.splitext(file_name)[1].lower()
    return {
        "file_path": file_path,
        "file_name": file_name,
        "file_type": file_type,
    }


def _build_documents(
    text: str,
    metadata: dict[str, Any],
) -> list[Document]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    return [Document(page_content=cleaned, metadata=metadata)]


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n\n".join(lines).strip()


def _read_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def _load_text_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    return _build_documents(_read_text_file(file_path), metadata)


def _load_html_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    text = _html_to_text(_read_text_file(file_path))
    return _build_documents(text, metadata)


def _load_pdf_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return _build_documents("\n\n".join(pages), metadata)


def _load_epub_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    texts: list[str] = []
    with zipfile.ZipFile(file_path, "r") as archive:
        for entry in _sorted_epub_entries(archive.namelist()):
            texts.append(_read_epub_entry(archive, entry))
    return _build_documents("\n\n".join(filter(None, texts)), metadata)


def _load_mobi_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    """Load a MOBI file by unpacking it into an existing document format."""
    import mobi

    temp_dir, extracted_path = mobi.extract(file_path)
    try:
        extension = os.path.splitext(extracted_path)[1].lower()
        loader = _FILE_LOADERS.get(extension, _load_text_document)
        return loader(extracted_path, metadata)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _sorted_epub_entries(entries: list[str]) -> list[str]:
    html_entries = [
        entry
        for entry in entries
        if entry.lower().endswith((".html", ".htm", ".xhtml"))
    ]
    page_entries = [
        entry
        for entry in html_entries
        if "page_" in entry and not entry.endswith("nav.xhtml")
    ]
    if not page_entries:
        return html_entries
    return sorted(page_entries, key=_extract_page_number)


def _read_epub_entry(archive: zipfile.ZipFile, entry: str) -> str:
    try:
        raw = archive.read(entry)
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return _html_to_text(html)


def _extract_page_number(file_name: str) -> int:
    match = re.search(r"page_(\d+)", file_name)
    if match is None:
        return 0
    return int(match.group(1))


def _load_zim_documents(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    zim = ZIMReader(file_path)
    documents: list[Document] = []
    for article_path in zim.get_all_entry_paths(limit=1000):
        html = zim.get_article(article_path)
        if not html:
            continue
        article_meta = dict(metadata)
        article_meta["zim_file"] = file_path
        article_meta["zim_path"] = article_path
        documents.extend(_build_documents(_html_to_text(html), article_meta))
    return documents


_FILE_LOADERS = {
    ".epub": _load_epub_document,
    ".htm": _load_html_document,
    ".html": _load_html_document,
    ".md": _load_text_document,
    ".mobi": _load_mobi_document,
    ".pdf": _load_pdf_document,
    ".zim": _load_zim_documents,
}
