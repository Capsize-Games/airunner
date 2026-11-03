"""
RAG and document search tools.

Tools for searching loaded documents (RAG), finding documents in knowledge base,
and saving new content to the knowledge base.
"""

import errno
import os
import re
from typing import Annotated, Any
from langchain_core.runnables import RunnableConfig

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.database.models.document import Document
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.models.target_files import TargetFiles
from airunner_services.database.session import session_scope
from airunner_common.contract_enums import SignalCode
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text
from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_search import (
    search_knowledge_base_documents_impl,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
    config: RunnableConfig = None,
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
        configurable = (config or {}).get("configurable", {})
        scope = configurable.get("rag_document_scope")
        results = rag_manager.search(query, k=3, doc_ids=scope)
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

        context_parts = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "unknown")
            content = (
                doc.page_content[:500]
                if len(doc.page_content) > 500
                else doc.page_content
            )
            context_parts.append(f"[Source {i}: {source}]\n{content}")
            logger.debug(
                f"Result {i} from source: {source}, "
                f"length: {len(doc.page_content)}"
            )

        result_text = "\n\n".join(context_parts)
        logger.info(
            f"Returning {len(context_parts)} document excerpts, "
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
        "Search registered knowledge-base document names and paths. When the "
        "request provides a document scope, results are limited to those "
        "documents. This search does not discover or index files."
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
    config: RunnableConfig = None,
) -> str:
    """Search registered knowledge-base documents by path and filename.

    This is a BROAD SEARCH across document titles and paths - like a search
    engine for your entire knowledge base. Use this BEFORE using rag_search
    to determine which documents should be loaded into RAG for detailed
    querying.

    Search only the document registry. Request-scoped calls are restricted to
    the supplied document IDs. Adding or indexing files is a separate action.

    Args:
        query: What topics/documents you're looking for
        k: Number of document paths to return (default 10)


    Examples:
        search_knowledge_base_documents("machine learning tutorials")
        search_knowledge_base_documents("health and fitness guides", k=5)
        search_knowledge_base_documents("cooking recipes")
    """
    configurable = (config or {}).get("configurable", {})
    scope = configurable.get("rag_document_scope")
    return search_knowledge_base_documents_impl(
        query=query,
        k=k,
        api=api,
        session_scope=session_scope,
        document_model=Document,
        logger=logger,
        document_scope=tuple(scope) if scope is not None else None,
    )


@tool(
    name="save_to_knowledge_base",
    category=ToolCategory.RAG,
    description=(
        "Save bounded text in managed knowledge-base storage and register it "
        "as a document. Existing files are never replaced."
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
    config: RunnableConfig = None,
) -> str:
    """Save and register a new text document in managed knowledge storage.

    Args:
        content: Text content to save
        title: Title/identifier for this knowledge
        category: Category for organization
        api: API instance (injected)

    """
    try:
        validated = _validate_knowledge_save(content, title, category, config)
        if isinstance(validated, str):
            return validated
        filename, chatbot_id = validated
        base_path = _knowledge_base_base_path()
        file_path = _write_managed_knowledge_file(
            base_path,
            category,
            filename,
            title,
            content,
        )
        registration_error = _register_knowledge_document(file_path, chatbot_id)
        if registration_error:
            return registration_error
        if not _notify_knowledge_document_added(api, file_path, title):
            return _knowledge_notification_failure(title)
        return f"Content saved and registered in the knowledge base: {title}"
    except Exception as e:
        return f"Error saving to knowledge base: {str(e)}"


def _validate_knowledge_save(
    content: Any,
    title: Any,
    category: Any,
    config: RunnableConfig,
) -> tuple[str, int | None] | str:
    """Validate save input and resolve trusted request ownership metadata."""
    if not isinstance(content, str) or not content.strip():
        return "Error saving to knowledge base: content must not be empty."
    if len(content.encode("utf-8")) > 65536:
        return "Error saving to knowledge base: content exceeds 65536 UTF-8 bytes."
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        return "Error saving to knowledge base: title must contain 1 to 160 characters."
    if not isinstance(category, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", category
    ):
        return (
            "Error saving to knowledge base: category must be a single safe "
            "name of at most 64 characters."
        )

    configurable = (config or {}).get("configurable", {})
    chatbot_id = configurable.get("chatbot_id")
    if configurable.get("rag_document_scope") is not None and chatbot_id is None:
        return (
            "Error saving to knowledge base: this request has a scoped "
            "document set but no chatbot ownership identity."
        )
    if chatbot_id is not None and (
        isinstance(chatbot_id, bool)
        or not isinstance(chatbot_id, int)
        or chatbot_id < 1
    ):
        return "Error saving to knowledge base: chatbot assignment is invalid."

    filename = "".join(
        char for char in title if char.isalnum() or char in (" ", "-", "_")
    ).strip()
    filename = filename.replace(" ", "_")
    if not filename:
        return (
            "Error saving to knowledge base: title has no usable filename "
            "characters."
        )
    return f"{filename}.txt", chatbot_id


def _knowledge_base_base_path() -> str:
    """Return the configured base path for managed knowledge storage."""
    settings = PathSettings.objects.first()
    if not settings or not settings.base_path:
        raise ValueError("managed storage path is unavailable")
    return os.path.expanduser(settings.base_path)


def _register_knowledge_document(
    file_path: str, chatbot_id: int | None
) -> str | None:
    """Register persisted content and attach it to its owning chatbot."""
    try:
        registered = Document.objects.create(
            path=file_path,
            active=True,
            indexed=False,
        )
    except Exception as error:
        return (
            f"Content was written to {file_path}, but document registration "
            f"failed: {error}"
        )
    if registered is None:
        return f"Content was written to {file_path}, but document registration failed."

    if chatbot_id is None:
        return None
    try:
        assignment = TargetFiles.objects.create(
            chatbot_id=chatbot_id,
            file_path=file_path,
        )
    except Exception as error:
        return (
            "Document was saved and registered, but assignment to chatbot "
            f"{chatbot_id} failed: {error}"
        )
    if assignment is None:
        return (
            "Document was saved and registered, but its chatbot assignment "
            "failed. It will not appear in that chatbot's document scope."
        )
    return None


def _notify_knowledge_document_added(api: Any, file_path: str, title: str) -> bool:
    """Emit the existing best-effort document refresh notification."""
    if not api or not hasattr(api, "emit_signal"):
        return True
    try:
        api.emit_signal(
            SignalCode.RAG_DOCUMENT_ADDED,
            {"file_path": file_path, "title": title},
        )
    except Exception as error:
        logger.warning("Saved knowledge file but notification failed: %s", error)
        return False
    return True


def _knowledge_notification_failure(title: str) -> str:
    """Describe a successful save whose refresh signal could not be sent."""
    return f"Content saved and registered, but refresh notification failed: {title}"


def _write_managed_knowledge_file(
    base_path: str, category: str, filename: str, title: str, content: str
) -> str:
    """Create a new managed KB file without following symlinks or overwriting.

    Each directory component is opened relative to a held directory descriptor
    with ``O_NOFOLLOW``. The leaf is created with ``O_EXCL`` so concurrent or
    repeated saves cannot replace existing data.
    """
    if not os.path.isabs(base_path):
        raise ValueError("managed storage path must be absolute")
    components = [part for part in base_path.split(os.sep) if part]
    if any(part in {".", ".."} for part in components):
        raise ValueError("managed storage path must not contain dot components")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open("/", flags)
    current_fd = root_fd
    try:
        for component in components:
            next_fd = _open_or_create_directory(current_fd, component, flags)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        kb_fd = _open_or_create_directory(current_fd, "knowledge_base", flags)
        try:
            category_fd = _open_or_create_directory(kb_fd, category, flags)
            try:
                payload = (
                    f"Title: {title}\nCategory: {category}\n\n---\n\n{content}"
                ).encode("utf-8")
                file_fd = os.open(
                    filename,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=category_fd,
                )
                created_stat = os.fstat(file_fd)
                phase = "write"
                try:
                    view = memoryview(payload)
                    while view:
                        written = os.write(file_fd, view)
                        view = view[written:]
                    phase = "file fsync"
                    os.fsync(file_fd)
                    os.close(file_fd)
                    file_fd = -1
                    phase = "directory fsync"
                    os.fsync(category_fd)
                except Exception as error:
                    if file_fd >= 0:
                        try:
                            os.close(file_fd)
                        except OSError:
                            pass
                    removed = _remove_created_knowledge_file(
                        category_fd,
                        filename,
                        created_stat.st_dev,
                        created_stat.st_ino,
                    )
                    if removed:
                        raise OSError(
                            f"knowledge file {phase} failed; the newly created "
                            "file was removed and was not registered"
                        ) from error
                    raise OSError(
                        f"knowledge file {phase} failed; an unregistered file "
                        "may remain and needs reconciliation"
                    ) from error
                return os.path.join(base_path, "knowledge_base", category, filename)
            finally:
                os.close(category_fd)
        finally:
            os.close(kb_fd)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError("managed storage path contains an unsafe directory component") from error
        if error.errno == errno.EEXIST:
            raise FileExistsError("a knowledge-base item with that title already exists") from error
        raise
    finally:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


def _open_or_create_directory(parent_fd: int, name: str, flags: int) -> int:
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        return os.open(name, flags, dir_fd=parent_fd)


def _remove_created_knowledge_file(
    directory_fd: int, filename: str, device: int, inode: int
) -> bool:
    """Remove only the leaf inode created by this save call, then sync it."""
    try:
        current = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        current = None
    except OSError:
        return False
    if current is not None:
        if (current.st_dev, current.st_ino) != (device, inode):
            return False
        try:
            os.unlink(filename, dir_fd=directory_fd)
        except OSError:
            return False
    try:
        os.fsync(directory_fd)
    except OSError:
        return False
    return True
