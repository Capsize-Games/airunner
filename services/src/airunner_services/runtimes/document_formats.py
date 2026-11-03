"""Document formats supported by the service-owned RAG loaders."""

SUPPORTED_DOCUMENT_EXTENSIONS: tuple[str, ...] = (
    ".epub",
    ".mobi",
    ".pdf",
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".zim",
)

# These containers require parsers that the service does not provide. Never
# decode their binary bytes through the unknown-text compatibility fallback.
UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS = frozenset({".doc", ".docx", ".odt"})

__all__ = [
    "SUPPORTED_DOCUMENT_EXTENSIONS",
    "UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS",
]
