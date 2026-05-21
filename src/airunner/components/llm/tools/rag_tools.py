"""
RAG and document search tools.

Tools for searching loaded documents (RAG), finding documents in knowledge base,
and saving new content to the knowledge base.
"""

import os
import re
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.documents.data.models.document import Document
from airunner.components.data.session_manager import session_scope
from airunner.components.settings.data.path_settings import PathSettings
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.log_hygiene import summarize_text

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _is_document_identity_query(query: str) -> bool:
    """Return whether the query is asking to identify the document."""
    normalized = " ".join(str(query or "").lower().split())
    if not normalized:
        return False

    identity_phrases = (
        "what is this document",
        "what document is this",
        "tell me what this document is",
        "what is this file",
        "what file is this",
        "which document is this",
        "which file is this",
        "identify this document",
        "identify the document",
        "identify this file",
    )
    if any(phrase in normalized for phrase in identity_phrases):
        return True

    asks_identity = any(
        phrase in normalized
        for phrase in ("what is this", "which is this", "identify")
    )
    mentions_document = "document" in normalized or "file" in normalized
    return asks_identity and mentions_document


def _query_mentions_document_reference(query: str) -> bool:
    """Return whether one query refers to one implied document."""
    normalized = " ".join(str(query or "").lower().split())
    if not normalized:
        return False

    patterns = (
        r"\bit\b",
        r"\bits\b",
        r"\bthis document\b",
        r"\bthat document\b",
        r"\bthe document\b",
        r"\bthis file\b",
        r"\bthat file\b",
        r"\bthe file\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _document_query_context(document_name: str) -> str:
    """Return one compact document label for query augmentation."""
    label = os.path.basename(str(document_name or "")).strip()
    if not label:
        return ""

    title_hint, author_hint = _infer_filename_details(label)
    if title_hint and author_hint:
        return f"{title_hint} by {author_hint}"
    if title_hint:
        return title_hint

    stem = os.path.splitext(label)[0].replace("_", " ").strip()
    return stem or label


def _expand_query_with_active_document(
    query: str,
    rag_manager: Any,
) -> str:
    """Augment one pronoun query with the single active document name."""
    if _is_document_identity_query(query):
        return query
    if not _query_mentions_document_reference(query):
        return query

    get_names = getattr(rag_manager, "_get_active_document_names", None)
    if not callable(get_names):
        return query

    active_names = [
        str(name).strip()
        for name in get_names()
        if str(name or "").strip()
    ]
    active_names = list(dict.fromkeys(active_names))
    if len(active_names) != 1:
        return query

    context = _document_query_context(active_names[0])
    if not context:
        return query

    return f"{query.strip()} Document context: {context}"


def _document_label(metadata: dict[str, Any]) -> str:
    """Return one human-readable label for a retrieved document."""
    for key in ("file_name", "source", "file_path"):
        value = str(metadata.get(key, "") or "").strip()
        if not value:
            continue
        if key in {"source", "file_path"}:
            return os.path.basename(value) or value
        return value
    return "unknown"


def _infer_filename_details(
    file_name: str,
) -> tuple[str | None, str | None]:
    """Infer one title/author hint from a filename when possible."""
    stem = os.path.splitext(os.path.basename(file_name))[0].strip()
    normalized_stem = stem.replace("_", " ").strip()
    if not normalized_stem or " - " not in normalized_stem:
        return None, None

    parts = [part.strip() for part in normalized_stem.split(" - ")]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None, None

    title = " - ".join(parts[:-1]).strip() or None
    author = parts[-1].strip() or None
    return title, author


def _format_document_summary(
    position: int,
    metadata: dict[str, Any],
) -> str:
    """Format one matched-document summary for a RAG result."""
    label = _document_label(metadata)
    lines = [f"Document {position}: {label}"]

    title_hint, author_hint = _infer_filename_details(label)
    if title_hint:
        lines.append(f"Inferred title from filename: {title_hint}")
    if author_hint:
        lines.append(f"Inferred author from filename: {author_hint}")

    file_type = str(metadata.get("file_type", "") or "").strip()
    if file_type:
        lines.append(f"File type: {file_type}")

    file_path = str(
        metadata.get("file_path") or metadata.get("source") or ""
    ).strip()
    if file_path:
        lines.append(f"Stored path: {file_path}")

    return "\n".join(lines)


def _format_excerpt(
    position: int,
    metadata: dict[str, Any],
    content: str,
) -> str:
    """Format one retrieved excerpt with its document label."""
    excerpt = content[:500] if len(content) > 500 else content
    label = _document_label(metadata)
    return f"[Excerpt {position} from {label}]\n{excerpt}"


def _format_rag_search_results(
    results: list[Any],
    *,
    include_excerpts: bool = True,
) -> str:
    """Return one user-facing RAG search result string."""
    document_summaries: list[str] = []
    excerpt_sections: list[str] = []
    seen_documents: set[str] = set()

    for index, doc in enumerate(results, 1):
        metadata = getattr(doc, "metadata", {}) or {}
        document_key = str(
            metadata.get("file_path")
            or metadata.get("file_name")
            or metadata.get("source")
            or f"result-{index}"
        )

        if document_key not in seen_documents:
            seen_documents.add(document_key)
            document_summaries.append(
                _format_document_summary(len(document_summaries) + 1, metadata)
            )

        if include_excerpts:
            excerpt_sections.append(
                _format_excerpt(
                    index,
                    metadata,
                    str(getattr(doc, "page_content", "") or ""),
                )
            )

    sections = []
    if document_summaries:
        sections.append(
            "Matched documents:\n" + "\n\n".join(document_summaries)
        )
    if excerpt_sections:
        sections.append(
            "Relevant excerpts:\n" + "\n\n".join(excerpt_sections)
        )
    return "\n\n".join(sections)


@tool(
    name="rag_search",
    category=ToolCategory.RAG,
    description=(
        "Search through LOADED documents in memory for relevant information. "
        "IMPORTANT: Only works if documents have been loaded into memory first. "
        "If this fails because no documents are loaded, inform the user that "
        "documents need to be loaded first."
    ),
    return_direct=False,
    requires_api=True,  # API injection provides access to rag_manager
    keywords=["document", "search", "knowledge", "memory", "loaded"],
    input_examples=[
        {"query": "What is the main topic discussed in chapter 3?"},
        {"query": "Find information about machine learning algorithms"},
        {"query": "Summary of the introduction section"},
    ],
)
def rag_search(
    query: Annotated[
        str, "Search query for finding relevant document content"
    ],
    api: Any = None,  # Injected by ToolManager
) -> str:
    """Search through LOADED documents in memory for relevant information.

    IMPORTANT: This only works if documents have been loaded into memory first.
    Documents must be actively loaded before searching them.

    If this tool fails because documents aren't loaded, inform the user
    that the requested documents need to be loaded first.

    Args:
        query: Search query for finding relevant document content
        api: API instance (injected by ToolManager)

    """
    logger.info(
        "rag_search called (%s)",
        summarize_text(query, label="query"),
    )

    # For RAG tools, api IS the rag_manager (LLMModelManager with RAG search methods)
    rag_manager = api

    logger.debug(
        "rag_manager available=%s has_search=%s",
        rag_manager is not None,
        hasattr(rag_manager, "search") if rag_manager else False,
    )

    if not rag_manager:
        error_msg = (
            "TOOL UNAVAILABLE: No RAG manager available. "
            "This is an internal error - RAG tools should receive the LLM model manager."
        )
        logger.warning(error_msg)
        return error_msg

    # Check if documents are loaded by calling the RAG manager's search method
    try:
        effective_query = _expand_query_with_active_document(
            query,
            rag_manager,
        )
        if effective_query != query:
            logger.info(
                "Expanded RAG query with active document context (%s)",
                summarize_text(
                    effective_query,
                    label="effective_query",
                ),
            )

        results = rag_manager.search(effective_query, k=3)
        logger.info(
            f"rag_manager.search returned "
            f"{len(results) if results else 0} results"
        )

        if not results:
            msg = (
                f"No relevant information found for '{query}' in loaded "
                f"documents. The document may not contain information about this topic, "
                f"or the search query may need to be rephrased."
            )
            logger.info(msg)
            return msg

        for i, doc in enumerate(results, 1):
            source = (getattr(doc, "metadata", {}) or {}).get(
                "source",
                "unknown",
            )
            logger.debug(
                f"Result {i} from source: {source}, "
                f"length: {len(getattr(doc, 'page_content', '') or '')}"
            )

        result_text = _format_rag_search_results(
            results,
            include_excerpts=not _is_document_identity_query(query),
        )
        logger.info(
            f"Returning {len(results)} document excerpts, "
            f"total length: {len(result_text)}"
        )
        return result_text
    except Exception as e:
        error_msg = f"Error searching documents: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@tool(
    name="search_knowledge_base_documents",
    category=ToolCategory.SEARCH,
    description=(
        "Search across ALL knowledge base documents to find the most relevant "
        "ones. This is a broad search across document titles and paths - like "
        "a search engine for your entire knowledge base. Use this BEFORE "
        "rag_search to determine which documents should be loaded. If documents "
        "aren't indexed, this tool will automatically discover and index them."
    ),
    return_direct=False,
    requires_api=True,
)
def search_knowledge_base_documents(
    query: Annotated[
        str,
        "What topics/documents you're looking for (e.g., 'Python programming books')",
    ],
    k: Annotated[int, "Number of document paths to return"] = 10,
    api: Any = None,
) -> str:
    """Search across ALL knowledge base documents to find relevant ones.

    This is a BROAD SEARCH across document titles and paths - like a search
    engine for your entire knowledge base. Use this BEFORE using rag_search
    to determine which documents should be loaded into RAG for detailed
    querying.

    The knowledge base may contain ebooks, PDFs, markdown files, ZIM files,
    and more. This tool helps you discover which documents are relevant to
    the user's question so you can load them for deeper analysis.

    Args:
        query: What topics/documents you're looking for
        k: Number of document paths to return (default 10)


    Examples:
        search_knowledge_base_documents("machine learning tutorials")
        search_knowledge_base_documents("health and fitness guides", k=5)
        search_knowledge_base_documents("cooking recipes")
    """
    try:
        with session_scope() as session:
            # Get all active documents
            docs = session.query(Document).filter_by(active=True).all()

            # Initialize found_files to track discovered files
            found_files = []

            # If no document records exist yet, attempt to discover files
            # on disk and add them to the database so the KB tools can work
            if not docs and api:
                logger.info(
                    f"No docs in DB, attempting discovery. api={type(api).__name__}"
                )
                try:
                    # Discover candidate document directories from PathSettings
                    settings = (
                        api.path_settings or PathSettings.objects.first()
                    )
                    logger.info(f"PathSettings: {settings}")
                    candidate_dirs = []
                    if settings:
                        candidate_dirs.extend(
                            [
                                settings.documents_path,
                                settings.ebook_path,
                                settings.webpages_path,
                                os.path.join(
                                    settings.base_path, "knowledge_base"
                                ),
                            ]
                        )

                    logger.info(
                        f"Candidate dirs for KB discovery: {candidate_dirs}"
                    )
                    for d in candidate_dirs:
                        if not d:
                            logger.debug(f"Skipping empty candidate dir")
                            continue
                        d = os.path.expanduser(d)
                        if not os.path.exists(d):
                            logger.info(f"KB discovery dir not found: {d}")
                            continue
                        logger.info(f"Scanning KB dir for documents: {d}")
                        file_count = 0
                        for root, _, files in os.walk(d):
                            for fname in files:
                                ext = os.path.splitext(fname)[1].lower()
                                if ext in [
                                    ".pdf",
                                    ".epub",
                                    ".html",
                                    ".htm",
                                    ".md",
                                    ".txt",
                                    ".zim",
                                ]:
                                    file_count += 1
                                    found_files.append(
                                        os.path.join(root, fname)
                                    )
                        logger.info(f"Found {file_count} files in {d}")

                    # Create Document DB entries for found files
                    logger.debug(
                        f"Found {len(found_files)} candidate files during discovery"
                    )
                    for fpath in found_files:
                        exists = Document.objects.filter_by(path=fpath)
                        if not exists or len(exists) == 0:
                            logger.info(
                                f"Creating Document record for: {fpath}"
                            )
                            Document.objects.create(
                                path=fpath, active=True, indexed=False
                            )
                            if hasattr(api, "emit_signal"):
                                api.emit_signal(
                                    SignalCode.DOCUMENT_COLLECTION_CHANGED,
                                    {"path": fpath, "action": "discovered"},
                                )
                        else:
                            logger.debug(f"Document already exists: {fpath}")

                    # Re-query after adding files
                    docs = session.query(Document).filter_by(active=True).all()
                    logger.info(
                        f"After discovery, DB now has {len(docs)} active document records"
                    )

                except Exception as e:
                    logger.error(f"Disk discovery failed: {e}", exc_info=True)
            # If no files were found with standard paths, attempt to discover
            # sample files in the repository (booksite) for dev environments
            if docs == [] and not found_files:
                try:
                    # Walk up the directory tree to find repo root with booksite
                    repo_root = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "..",
                            "..",
                            "..",
                            "..",
                        )
                    )
                    # Climb upwards until we find 'booksite' or reach filesystem root
                    candidate = repo_root
                    while True:
                        if os.path.exists(os.path.join(candidate, "booksite")):
                            break
                        parent = os.path.abspath(
                            os.path.join(candidate, os.pardir)
                        )
                        if parent == candidate:
                            candidate = None
                            break
                        candidate = parent
                    if candidate:
                        logger.debug(
                            f"Repo fallback candidate root: {candidate}"
                        )
                        # Known sample locations in repo
                        fallback_dirs = [
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "documents",
                            ),
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "ebooks",
                            ),
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "webpages",
                            ),
                        ]
                        for d in fallback_dirs:
                            if os.path.exists(d):
                                logger.debug(
                                    f"Scanning repo fallback dir for KB files: {d}"
                                )
                                for root, _, files in os.walk(d):
                                    for fname in files:
                                        ext = os.path.splitext(fname)[
                                            1
                                        ].lower()
                                        if ext in [
                                            ".pdf",
                                            ".epub",
                                            ".html",
                                            ".htm",
                                            ".md",
                                            ".txt",
                                            ".zim",
                                        ]:
                                            fpath = os.path.join(root, fname)
                                            exists = (
                                                Document.objects.filter_by(
                                                    path=fpath
                                                )
                                            )
                                            if not exists or len(exists) == 0:
                                                Document.objects.create(
                                                    path=fpath,
                                                    active=True,
                                                    indexed=False,
                                                )
                                                found_files.append(fpath)
                                                if hasattr(api, "emit_signal"):
                                                    api.emit_signal(
                                                        SignalCode.DOCUMENT_COLLECTION_CHANGED,
                                                        {
                                                            "path": fpath,
                                                            "action": "discovered",
                                                        },
                                                    )
                        if found_files:
                            docs = (
                                session.query(Document)
                                .filter_by(active=True)
                                .all()
                            )
                except Exception as e:
                    logger.warning(f"Fallback repo discovery failed: {e}")

            if not docs:
                logger.info(
                    f"[KB SEARCH] No docs found after all discovery attempts. Returning error message."
                )
                return (
                    "No documents found in knowledge base. "
                    "⚠️ Try search_web() to search the internet instead, "
                    "then use record_knowledge() to save any useful facts."
                )

            # If no files were found with standard paths, attempt to discover
            # sample files in the repository (booksite) for dev environments
            if docs == [] and not found_files:
                try:
                    # Walk up the directory tree to find repo root with booksite
                    repo_root = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "..",
                            "..",
                            "..",
                            "..",
                        )
                    )
                    # Climb upwards until we find 'booksite' or reach filesystem root
                    candidate = repo_root
                    while True:
                        if os.path.exists(os.path.join(candidate, "booksite")):
                            break
                        parent = os.path.abspath(
                            os.path.join(candidate, os.pardir)
                        )
                        if parent == candidate:
                            candidate = None
                            break
                        candidate = parent
                    if candidate:
                        # Known sample locations in repo
                        fallback_dirs = [
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "documents",
                            ),
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "ebooks",
                            ),
                            os.path.join(
                                candidate,
                                "booksite",
                                "text",
                                "other",
                                "webpages",
                            ),
                        ]
                        for d in fallback_dirs:
                            if os.path.exists(d):
                                logger.debug(
                                    f"Scanning repo fallback dir for KB files: {d}"
                                )
                                for root, _, files in os.walk(d):
                                    for fname in files:
                                        ext = os.path.splitext(fname)[
                                            1
                                        ].lower()
                                        if ext in [
                                            ".pdf",
                                            ".epub",
                                            ".html",
                                            ".htm",
                                            ".md",
                                            ".txt",
                                            ".zim",
                                        ]:
                                            fpath = os.path.join(root, fname)
                                            exists = (
                                                Document.objects.filter_by(
                                                    path=fpath
                                                )
                                            )
                                            if not exists or len(exists) == 0:
                                                Document.objects.create(
                                                    path=fpath,
                                                    active=True,
                                                    indexed=False,
                                                )
                                                found_files.append(fpath)
                                                if hasattr(api, "emit_signal"):
                                                    api.emit_signal(
                                                        SignalCode.DOCUMENT_COLLECTION_CHANGED,
                                                        {
                                                            "path": fpath,
                                                            "action": "discovered",
                                                        },
                                                    )
                        if found_files:
                            docs = (
                                session.query(Document)
                                .filter_by(active=True)
                                .all()
                            )
                except Exception as e:
                    logger.warning(f"Fallback repo discovery failed: {e}")

            # Simple keyword-based relevance scoring
            query_lower = query.lower()
            query_terms = query_lower.split()

            scored_docs = []
            for doc in docs:
                path_lower = doc.path.lower()
                filename = os.path.basename(path_lower)

                # Score based on query term matches in path/filename
                score = 0
                for term in query_terms:
                    if term in filename:
                        score += 10  # High weight for filename matches
                    elif term in path_lower:
                        score += 5  # Medium weight for path matches

                if score > 0:
                    scored_docs.append((score, doc))

            # Sort by score and take top k
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            top_docs = scored_docs[:k]

            if not top_docs:
                # No file/path matches for query terms. Try to index any unindexed
                # active documents and retry scoring (useful for content-based
                # searching where filenames may not include query terms).
                try:
                    if api and hasattr(api, "rag_manager"):
                        rag_manager = api.rag_manager
                        unindexed = [d.path for d in docs if not d.indexed]
                        if unindexed and hasattr(
                            rag_manager, "ensure_indexed_files"
                        ):
                            logger.info(
                                f"No filepath matches for query '{query}'. Attempting to index {len(unindexed)} documents and retry."
                            )
                            success = rag_manager.ensure_indexed_files(
                                unindexed
                            )
                            if success:
                                # Recompute scoring after indexing
                                docs = (
                                    session.query(Document)
                                    .filter_by(active=True)
                                    .all()
                                )
                                scored_docs = []
                                for doc in docs:
                                    path_lower = doc.path.lower()
                                    filename = os.path.basename(path_lower)
                                    score = 0
                                    for term in query_terms:
                                        if term in filename:
                                            score += 10
                                        elif term in path_lower:
                                            score += 5
                                    if score > 0:
                                        scored_docs.append((score, doc))
                                scored_docs.sort(
                                    reverse=True, key=lambda x: x[0]
                                )
                                top_docs = scored_docs[:k]
                except Exception as e:
                    logger.warning(f"On-demand indexing and retry failed: {e}")

                if not top_docs:
                    return (
                        f"No documents found matching '{query}' in the knowledge base. "
                        f"⚠️ Try search_web('{query}') to search the internet instead, "
                        f"then use record_knowledge() to save any useful facts you find."
                    )

            # Format response
            result_parts = [
                f"Found {len(top_docs)} relevant document(s) "
                f"for '{query}':\n"
            ]
            # If we found documents but they are not indexed, attempt to index them
            to_index_files = [
                doc.path for _, doc in top_docs if not doc.indexed
            ]
            indexed_now_count = 0
            if to_index_files and api:
                logger.debug(
                    f"Attempting to on-demand index {len(to_index_files)} files"
                )
                print(
                    f"DEBUG search_knowledge_base_documents: attempting to index {len(to_index_files)} files"
                )
                rag_manager = getattr(api, "rag_manager", None)
                if rag_manager and hasattr(
                    rag_manager, "ensure_indexed_files"
                ):
                    try:
                        success = rag_manager.ensure_indexed_files(
                            to_index_files
                        )
                        indexed_now_count = (
                            len(to_index_files) if success else 0
                        )
                    except Exception as e:
                        logger.warning(f"Failed to index files on demand: {e}")

            for i, (score, doc) in enumerate(top_docs, 1):
                filename = os.path.basename(doc.path)
                indexed_status = "indexed" if doc.indexed else "not indexed"
                # If we just indexed them, update display status
                if doc.path in to_index_files and indexed_now_count > 0:
                    indexed_status = "indexed"
                result_parts.append(f"{i}. {filename} ({indexed_status})")
                result_parts.append(f"   Path: {doc.path}")

            result_parts.append(
                "\nTip: Use these document paths with rag_search to get "
                "detailed content."
            )

            # If we performed indexing, append summary of what happened
            if indexed_now_count > 0:
                result_parts.insert(
                    0,
                    f"Automatically indexed {indexed_now_count} document(s) and refreshed the KB.\n",
                )
            return "\n".join(result_parts)
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return f"Error searching knowledge base: {str(e)}"


@tool(
    name="save_to_knowledge_base",
    category=ToolCategory.RAG,
    description=(
        "Save content to the knowledge base for future RAG retrieval. "
        "This allows the agent to build its own knowledge base over time "
        "by saving important information for later reference."
    ),
    return_direct=False,
    requires_api=True,
)
def save_to_knowledge_base(
    content: Annotated[str, "Text content to save"],
    title: Annotated[str, "Title/identifier for this knowledge"],
    category: Annotated[
        str, "Category for organization (e.g., 'research', 'documentation')"
    ] = "general",
    api: Any = None,
) -> str:
    """Save content to the knowledge base for future RAG retrieval.

    This tool allows the agent to build its own knowledge base over time
    by saving important information for later reference.

    Args:
        content: Text content to save
        title: Title/identifier for this knowledge
        category: Category for organization
        api: API instance (injected)

    """
    try:
        # Create a document file
        settings = PathSettings.objects.first()
        base_path = os.path.expanduser(settings.base_path)
        kb_path = os.path.join(base_path, "knowledge_base", category)
        os.makedirs(kb_path, exist_ok=True)

        # Sanitize filename
        filename = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        filename = filename.replace(" ", "_") + ".txt"

        file_path = os.path.join(kb_path, filename)

        # Write content
        with open(file_path, "w") as f:
            f.write(f"Title: {title}\n")
            f.write(f"Category: {category}\n")
            f.write("\n---\n\n")
            f.write(content)

        # Emit signal to reload RAG if API available
        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.RAG_DOCUMENT_ADDED,
                {"file_path": file_path, "title": title},
            )

        return f"Content saved to knowledge base: {title}"
    except Exception as e:
        return f"Error saving to knowledge base: {str(e)}"
