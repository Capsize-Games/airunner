import os
from typing import Optional

from llama_index.readers.file import PDFReader


def _naive_read(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _clean_text(text: str) -> str:
    """Apply simple cleaning heuristics to remove ebook boilerplate.

    This looks for common headings and trims front/back matter heuristically.
    Not perfect — intended as a best-effort improvement over raw text.
    """
    if not text:
        return text
    # Normalize whitespace and remove empty lines
    s = "\n".join(
        [line.rstrip() for line in text.splitlines() if line.strip()]
    )

    # Cut at common front-matter markers
    front_markers = [
        "table of contents",
        "contents",
        "copyright",
        "all rights reserved",
        "preface",
        "introduction",
    ]
    lower = s.lower()
    front_pos = None
    for m in front_markers:
        idx = lower.find(m)
        if idx != -1:
            if front_pos is None or idx < front_pos:
                front_pos = idx
    if front_pos and front_pos < 200:
        s = s[front_pos:]

    # Drop trailing common end markers
    end_markers = ["acknowledg", "about the author", "publisher", "references"]
    lower = s.lower()
    end_pos = None
    for m in end_markers:
        idx = lower.rfind(m)
        if idx != -1:
            if end_pos is None or idx > end_pos:
                end_pos = idx
    if end_pos and end_pos > len(s) - 2000:
        s = s[:end_pos]

    # Collapse multiple blank lines
    lines = [ln for ln in s.splitlines() if ln.strip()]
    return "\n\n".join(lines)


def extract_text_from_epub(path: str) -> Optional[str]:
    """Attempt to extract text from an EPUB file using ebooklib.

    Falls back to a naive binary decode when ebooklib isn't available or fails.
    """
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except Exception:
        # If ebooklib or bs4 isn't available, try a lightweight zip/html fallback
        try:
            import zipfile
            import re

            texts = []
            with zipfile.ZipFile(path, "r") as z:
                for name in z.namelist():
                    lower = name.lower()
                    if lower.endswith((".xhtml", ".html", ".htm", ".xml")):
                        try:
                            raw = z.read(name)
                            try:
                                html = raw.decode("utf-8")
                            except Exception:
                                html = raw.decode("latin-1", errors="ignore")
                            # crude tag stripper
                            text = re.sub(r"<[^>]+>", " ", html)
                            texts.append(text)
                        except Exception:
                            continue
            raw = "\n\n".join(t for t in texts if t).strip()
            if raw:
                return _clean_text(raw)
        except Exception:
            pass
        return _naive_read(path)

    try:
        book = epub.read_epub(path)
        texts = []
        for item in book.get_items():
            try:
                name = getattr(item, "get_name", lambda: None)()
            except Exception:
                name = None
            try:
                media_type = (
                    getattr(item, "media_type", None)
                    or getattr(item, "get_type", lambda: None)()
                )
            except Exception:
                media_type = None

            is_html = False
            if name and isinstance(name, str):
                if name.lower().endswith((".xhtml", ".html", ".htm", ".xml")):
                    is_html = True
            if media_type and isinstance(media_type, str):
                if (
                    "html" in media_type.lower()
                    or "xhtml" in media_type.lower()
                ):
                    is_html = True
            # Some ebooklib versions expose EpubHtml type; check that too
            try:
                if (
                    not is_html
                    and hasattr(epub, "EpubHtml")
                    and item.get_type() == epub.EpubHtml
                ):
                    is_html = True
            except Exception:
                pass

            if not is_html:
                continue

            try:
                html = item.get_content()
                soup = BeautifulSoup(html, "html.parser")
                texts.append(soup.get_text(separator="\n"))
            except Exception:
                continue

        raw = "\n\n".join(t for t in texts if t).strip()
        if raw:
            return _clean_text(raw)
        # fallback to zip/html parsing if ebooklib path produced nothing
        try:
            import zipfile
            import re

            texts = []
            with zipfile.ZipFile(path, "r") as z:
                for name in z.namelist():
                    lower = name.lower()
                    if lower.endswith((".xhtml", ".html", ".htm", ".xml")):
                        try:
                            rawb = z.read(name)
                            try:
                                html = rawb.decode("utf-8")
                            except Exception:
                                html = rawb.decode("latin-1", errors="ignore")
                            text = re.sub(r"<[^>]+>", " ", html)
                            texts.append(text)
                        except Exception:
                            continue
            raw2 = "\n\n".join(t for t in texts if t).strip()
            if raw2:
                return _clean_text(raw2)
        except Exception:
            pass
        return _naive_read(path)
    except Exception:
        return _naive_read(path)


def extract_text_from_pdf(path: str) -> Optional[str]:
    """Extract text from PDF using llama_index PDFReader (same as RAG)."""
    try:
        pdf_reader = PDFReader()
        documents = pdf_reader.load_data(file=path)

        if not documents:
            return None

        # Combine all pages into one text
        text_parts = [doc.text for doc in documents if doc.text]
        if text_parts:
            combined_text = "\n\n".join(text_parts)
            return _clean_text(combined_text)

        return None
    except Exception:
        # Log error but don't fail completely
        return None


def extract_text(path: str) -> Optional[str]:
    """Dispatch extraction based on file extension with graceful fallback."""
    if not os.path.exists(path):
        return None
    _, ext = os.path.splitext(path.lower())
    if ext == ".epub":
        return extract_text_from_epub(path)
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    # default: read as text
    return _naive_read(path)


def prepare_examples_for_preview(
    path: str, fmt: str = "qa", max_chars: int = 2000
):
    """Prepare training examples for a single file path using the selected format.

    Returns a list of (title, chunk) tuples.
    """
    text = extract_text(path) or ""
    title = path and os.path.basename(path) or ""

    def _chunk_text_to_examples(title: str, text: str, max_chars: int = 2000):
        examples = []
        if not text:
            return examples
        start = 0
        idx = 1
        length = len(text)
        while start < length:
            chunk = text[start : start + max_chars]
            examples.append((f"{title} - part {idx}", chunk))
            start += max_chars
            idx += 1
        return examples

    if fmt == "long":
        max_l = 10000
        if len(text) <= max_l:
            return [(title, text)]
        return _chunk_text_to_examples(title, text, max_chars=max_l)

    if fmt == "author":
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        examples = []
        idx = 1
        for p in paragraphs:
            if len(p) > max_chars:
                examples.extend(
                    _chunk_text_to_examples(
                        f"{title} - part {idx}", p, max_chars
                    )
                )
                idx += 1
            else:
                examples.append((f"{title} - para {idx}", p))
                idx += 1
        return examples

    # default qa
    return _chunk_text_to_examples(title, text, max_chars=max_chars)
