"""LangChain-native document loading helpers for RAG ingestion."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from typing import Any, Callable, Iterator, Optional

from bs4 import BeautifulSoup
from langchain_core.documents import Document

MetadataLoader = Callable[[str], dict[str, Any]]

#: Refuse plain-text reads above this size (OOM guard).
MAX_TEXT_FILE_BYTES = 10 * 1024 * 1024
#: Cap PDF input size and page count (encryption/DoS guard).
MAX_PDF_FILE_BYTES = 100 * 1024 * 1024
MAX_PDF_PAGES = 2000
#: Cap total decompressed bytes read from one EPUB archive.
MAX_EPUB_TOTAL_BYTES = 100 * 1024 * 1024
#: Cap one MOBI extraction (extracted path + unpacked bytes).
MAX_MOBI_TOTAL_BYTES = 200 * 1024 * 1024
#: Bound ZIM ingestion (batching guard).
ZIM_BATCH_SIZE = 50
MAX_ZIM_ARTICLES = 1000


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
    """Load documents for a single file path."""
    if not os.path.exists(file_path):
        return []

    metadata = _resolve_metadata(file_path, metadata_loader)
    extension = os.path.splitext(file_path)[1].lower()
    loader = _FILE_LOADERS.get(extension, _load_text_document)
    return loader(file_path, metadata)


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
    size = os.path.getsize(file_path)
    if size > MAX_TEXT_FILE_BYTES:
        raise ValueError(
            f"Refusing to read {file_path}: "
            f"{size} bytes exceeds {MAX_TEXT_FILE_BYTES} byte cap"
        )
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Strip non-content tags so script/style text never pollutes the index.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
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
    try:
        size = os.path.getsize(file_path)
        if size > MAX_PDF_FILE_BYTES:
            raise ValueError(
                f"Refusing to read {file_path}: "
                f"{size} bytes exceeds {MAX_PDF_FILE_BYTES} byte cap"
            )
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        if getattr(reader, "is_encrypted", False):
            raise ValueError(f"Refusing encrypted PDF: {file_path}")
        page_count = len(reader.pages)
        if page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"Refusing PDF with {page_count} pages "
                f"(cap {MAX_PDF_PAGES}): {file_path}"
            )
        pages = [page.extract_text() or "" for page in reader.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to read PDF {file_path}: {exc}") from exc
    return _build_documents("\n\n".join(pages), metadata)


def _read_epub_entry_capped(
    archive: zipfile.ZipFile, entry: str, remaining: int
) -> tuple[str, int]:
    """Read one EPUB entry, enforcing the total byte budget.

    Returns:
        Tuple of extracted text and updated remaining budget.
    """
    try:
        info = archive.getinfo(entry)
        if info.file_size > remaining:
            raise ValueError(
                f"EPUB entry {entry} exceeds {remaining} byte budget"
            )
        raw = archive.read(entry)
    except (KeyError, ValueError):
        raise
    except Exception:
        return "", remaining
    if len(raw) > remaining:
        raise ValueError(
            f"EPUB entry {entry} exceeds {remaining} byte budget"
        )
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return "", remaining
    return _html_to_text(html), remaining - len(raw)


def _load_epub_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    texts: list[str] = []
    remaining = MAX_EPUB_TOTAL_BYTES
    with zipfile.ZipFile(file_path, "r") as archive:
        for entry in _sorted_epub_entries(archive.namelist()):
            text, remaining = _read_epub_entry_capped(
                archive, entry, remaining
            )
            if text:
                texts.append(text)
    return _build_documents("\n\n".join(texts), metadata)


def _load_mobi_document(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    """Load a MOBI file by unpacking it into an existing document format."""
    import mobi

    if os.path.getsize(file_path) > MAX_MOBI_TOTAL_BYTES:
        raise ValueError(f"Refusing oversized MOBI: {file_path}")
    temp_dir, extracted_path = mobi.extract(file_path)
    try:
        # Containment: the returned path must stay inside the
        # library-created temp dir, never elsewhere on disk.
        resolved = os.path.realpath(extracted_path)
        base = os.path.realpath(temp_dir)
        try:
            confined = os.path.commonpath([resolved, base]) == base
        except ValueError:
            confined = False
        if not confined:
            raise ValueError(
                f"MOBI extraction escaped its directory: {extracted_path}"
            )
        if os.path.getsize(resolved) > MAX_MOBI_TOTAL_BYTES:
            raise ValueError(
                f"Refusing oversized MOBI extraction: {extracted_path}"
            )
        extension = os.path.splitext(resolved)[1].lower()
        loader = _FILE_LOADERS.get(extension, _load_text_document)
        return loader(resolved, metadata)
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
    ordered = sorted(page_entries, key=_extract_page_number)
    # Fall back to the full html list when the page_ heuristic looks
    # partial (covers fewer than half the html entries).
    if len(ordered) * 2 < len(html_entries):
        return html_entries
    return ordered


def _extract_page_number(file_name: str) -> int:
    match = re.search(r"page_(\d+)", file_name)
    if match is None:
        return 0
    return int(match.group(1))


def _iter_zim_documents(
    file_path: str,
    metadata: dict[str, Any],
    batch_size: int = ZIM_BATCH_SIZE,
) -> Iterator[list[Document]]:
    """Yield ZIM articles in bounded batches instead of one list."""
    from airunner_services.zimreader import ZIMReader  # noqa: PLC0415

    zim = ZIMReader(file_path)
    batch: list[Document] = []
    seen = 0
    for article_path in zim.get_all_entry_paths(limit=MAX_ZIM_ARTICLES):
        html = zim.get_article(article_path)
        if not html:
            continue
        article_meta = dict(metadata)
        article_meta["zim_file"] = file_path
        article_meta["zim_path"] = article_path
        built = _build_documents(_html_to_text(html), article_meta)
        if not built:
            continue
        batch.extend(built)
        seen += 1
        if len(batch) >= batch_size:
            yield batch
            batch = []
        if seen >= MAX_ZIM_ARTICLES:
            break
    if batch:
        yield batch


def _load_zim_documents(
    file_path: str,
    metadata: dict[str, Any],
) -> list[Document]:
    documents: list[Document] = []
    for batch in _iter_zim_documents(file_path, metadata):
        documents.extend(batch)
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