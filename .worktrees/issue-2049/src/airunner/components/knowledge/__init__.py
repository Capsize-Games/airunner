"""
Knowledge management system for long-term memory.

Facts are stored in daily markdown files under:
  ~/.local/share/airunner/text/knowledge/YYYY-MM-DD.md

Each file has sections, and facts within sections are separated by blank lines.
All files are indexed into RAG for semantic retrieval during responses.

Key components:
- KnowledgeBase: Daily markdown file storage with CRUD operations
- get_knowledge_base(): Singleton accessor
"""

from airunner.components.knowledge.knowledge_base import (
    KnowledgeBase,
    get_knowledge_base,
    KNOWLEDGE_DIR,
)

__all__ = [
    "KnowledgeBase",
    "get_knowledge_base",
    "KNOWLEDGE_DIR",
]
