"""Shared constants for RAG tool helpers."""

SUMMARY_RETRIEVAL_K = 12
STANDARD_RETRIEVAL_K = 6
SUMMARY_EVIDENCE_LIMIT = 8

FRONT_MATTER_HEADINGS = {
    "INTRODUCTION",
    "PROLOGUE",
    "FOREWORD",
    "PREFACE",
}

SUPPORTED_DOCUMENT_EXTENSIONS = (
    ".mobi",
    ".pdf",
    ".epub",
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".zim",
)

__all__ = [
    "FRONT_MATTER_HEADINGS",
    "STANDARD_RETRIEVAL_K",
    "SUMMARY_EVIDENCE_LIMIT",
    "SUMMARY_RETRIEVAL_K",
    "SUPPORTED_DOCUMENT_EXTENSIONS",
]
