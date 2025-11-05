"""
Knowledge management system for long-term memory.

This package provides persistent knowledge storage beyond conversation history,
including:
- User-specific facts and preferences
- Document summaries and key concepts
- Web content caching
- Semantic indexing for retrieval

Knowledge is stored in human-readable formats (markdown) and indexed
with RAG for efficient retrieval.
"""

# Global instances (initialized on first import)
_extraction_worker = None
_auto_handler = None


def initialize_knowledge_system():
    """
    Initialize the knowledge extraction system.

    This creates the extraction worker and auto-extraction handler,
    which will listen for signals and automatically extract knowledge
    from conversations when enabled.

    Should be called once during application startup.
    """
    global _extraction_worker, _auto_handler

    # Lazy imports to avoid circular dependencies during Alembic migrations
    from airunner.components.knowledge.workers.knowledge_extraction_worker import (
        KnowledgeExtractionWorker,
    )
    from airunner.components.knowledge.auto_extraction_handler import (
        AutoExtractionHandler,
    )

    if _extraction_worker is None:
        _extraction_worker = KnowledgeExtractionWorker()

    if _auto_handler is None:
        _auto_handler = AutoExtractionHandler()

    return _extraction_worker, _auto_handler


__all__ = [
    "initialize_knowledge_system",
]
