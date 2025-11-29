"""
Knowledge Base - Daily markdown files for persistent memory.

Facts are stored in daily markdown files under:
  ~/.local/share/airunner/text/knowledge/YYYY-MM-DD.md

Each file has sections, and facts within sections are separated by blank lines
for easy parsing and LLM manipulation.

All files are indexed into RAG for semantic retrieval during thinking/response.
"""

import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import threading
from glob import glob

from airunner.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Knowledge base directory
KNOWLEDGE_DIR = Path(AIRUNNER_BASE_PATH) / "text" / "knowledge"

# Sections for organizing facts
SECTIONS = [
    "Identity",
    "Work & Projects", 
    "Interests & Hobbies",
    "Preferences",
    "Health & Wellness",
    "Relationships",
    "Goals",
    "Notes",
]


def get_daily_template(date_str: str) -> str:
    """Get template for a new daily knowledge file."""
    return f"""# Knowledge - {date_str}

## Identity

## Work & Projects

## Interests & Hobbies

## Preferences

## Health & Wellness

## Relationships

## Goals

## Notes

"""


# Singleton instance
_knowledge_base_instance: Optional["KnowledgeBase"] = None
_lock = threading.Lock()


def get_knowledge_base() -> "KnowledgeBase":
    """Get the singleton KnowledgeBase instance.
    
    Returns:
        KnowledgeBase instance (created on first call)
    """
    global _knowledge_base_instance
    with _lock:
        if _knowledge_base_instance is None:
            _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance


class KnowledgeBase:
    """
    Markdown-based knowledge storage with daily files.
    
    Facts are stored in daily markdown files and indexed for RAG retrieval.
    Sections organize facts, and blank lines separate individual facts.
    """
    
    def __init__(self, knowledge_dir: Optional[Path] = None):
        """Initialize the knowledge base.
        
        Args:
            knowledge_dir: Optional custom path for knowledge files.
                          Defaults to ~/.local/share/airunner/text/knowledge/
        """
        self.logger = logger
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self._rag_indexed = False
        
        self.logger.info(f"KnowledgeBase initialized: {self.knowledge_dir}")
    
    def _get_today_path(self) -> Path:
        """Get path for today's knowledge file."""
        today = date.today().isoformat()  # YYYY-MM-DD
        return self.knowledge_dir / f"{today}.md"
    
    def _get_file_path(self, date_str: Optional[str] = None) -> Path:
        """Get path for a specific date's knowledge file.
        
        Args:
            date_str: Date string (YYYY-MM-DD) or None for today
            
        Returns:
            Path to the knowledge file
        """
        if date_str is None:
            return self._get_today_path()
        return self.knowledge_dir / f"{date_str}.md"
    
    def _ensure_today_file(self) -> Path:
        """Ensure today's knowledge file exists.
        
        Returns:
            Path to today's file
        """
        path = self._get_today_path()
        if not path.exists():
            today = date.today().isoformat()
            path.write_text(get_daily_template(today), encoding="utf-8")
            self.logger.info(f"Created new knowledge file: {path}")
        return path
    
    def list_files(self) -> List[Path]:
        """List all knowledge files sorted by date (newest first).
        
        Returns:
            List of knowledge file paths
        """
        files = list(self.knowledge_dir.glob("*.md"))
        # Sort by filename (which is date-based) in reverse order
        files.sort(key=lambda p: p.stem, reverse=True)
        return files
    
    def read_file(self, date_str: Optional[str] = None) -> str:
        """Read a knowledge file.
        
        Args:
            date_str: Date string (YYYY-MM-DD) or None for today
            
        Returns:
            File content or empty string if not found
        """
        path = self._get_file_path(date_str)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    
    def read_all(self, max_files: int = 30) -> str:
        """Read all knowledge files combined (most recent first).
        
        Args:
            max_files: Maximum number of files to read
            
        Returns:
            Combined content from all files
        """
        files = self.list_files()[:max_files]
        parts = []
        for f in files:
            content = f.read_text(encoding="utf-8")
            if content.strip():
                parts.append(f"# From {f.stem}\n\n{content}")
        return "\n\n---\n\n".join(parts)
    
    def _normalize_fact(self, fact: str) -> str:
        """Normalize a fact for comparison (remove bullets, lowercase, strip).
        
        Args:
            fact: The fact string to normalize
            
        Returns:
            Normalized string for comparison
        """
        # Remove bullet points and leading/trailing whitespace
        normalized = fact.strip()
        if normalized.startswith(('-', '*', '•')):
            normalized = normalized[1:].strip()
        return normalized.lower()
    
    def _is_duplicate_fact(self, fact: str, section_content: str) -> bool:
        """Check if a fact is semantically duplicate of existing content.
        
        Uses multiple strategies:
        1. Exact match (normalized)
        2. Substring match (new fact contained in existing)
        3. Key entity overlap (for facts about the same subject)
        
        Args:
            fact: The fact to check
            section_content: Content of the section to check against
            
        Returns:
            True if duplicate, False otherwise
        """
        normalized_new = self._normalize_fact(fact)
        
        # Extract existing facts from section content
        lines = section_content.split('\n')
        existing_facts = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                existing_facts.append(self._normalize_fact(line))
        
        for existing in existing_facts:
            if not existing:
                continue
                
            # Exact match
            if normalized_new == existing:
                self.logger.debug(f"Duplicate (exact): '{fact[:50]}...'")
                return True
            
            # Substring match - new fact is contained in existing
            if normalized_new in existing:
                self.logger.debug(f"Duplicate (substring): '{fact[:50]}...' in existing")
                return True
            
            # Existing fact is contained in new fact (new is more detailed, allow it)
            # This is NOT a duplicate - we want to add more detailed facts
            
            # Check key entity overlap (e.g., both about "AI Runner")
            # Extract key entities (capitalized words, quoted strings)
            import re as re_module
            new_entities = set(re_module.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', fact))
            existing_entities = set(re_module.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', 
                                                       line if line else ''))
            
            # If >80% entity overlap and similar length, likely duplicate
            if new_entities and existing_entities:
                overlap = len(new_entities & existing_entities)
                total = max(len(new_entities), len(existing_entities))
                if overlap / total > 0.8:
                    # Check if they're saying essentially the same thing
                    new_words = set(normalized_new.split())
                    existing_words = set(existing.split())
                    word_overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
                    if word_overlap > 0.7:
                        self.logger.debug(f"Duplicate (semantic): '{fact[:50]}...'")
                        return True
        
        return False

    def add_fact(
        self, 
        fact: str, 
        section: str = "Notes",
        date_str: Optional[str] = None
    ) -> bool:
        """Add a fact to a section with a blank line before it.
        
        Includes deduplication - will not add facts that are semantically
        equivalent to existing facts in the section.
        
        Args:
            fact: The fact to add
            section: Section name (e.g., "Identity", "Notes")
            date_str: Target date or None for today
            
        Returns:
            True if successful, False if duplicate or error
        """
        # Ensure today's file exists
        if date_str is None:
            path = self._ensure_today_file()
        else:
            path = self._get_file_path(date_str)
            if not path.exists():
                path.write_text(get_daily_template(date_str), encoding="utf-8")
        
        content = path.read_text(encoding="utf-8")
        
        # Find the section
        section_pattern = rf'^## {re.escape(section)}\s*$'
        match = re.search(section_pattern, content, re.MULTILINE)
        
        if not match:
            self.logger.warning(f"Section '{section}' not found")
            return False
        
        # Find the end of this section (next section or end of file)
        section_start = match.end()
        next_section = re.search(r'^## ', content[section_start:], re.MULTILINE)
        
        if next_section:
            section_end = section_start + next_section.start()
        else:
            section_end = len(content)
        
        # Get section content for deduplication check
        section_content = content[section_start:section_end]
        
        # Check for duplicates
        if self._is_duplicate_fact(fact, section_content):
            self.logger.info(f"Skipping duplicate fact: {fact[:50]}...")
            return False
        
        # Format the fact with blank lines
        # Ensure fact starts with "- " if it doesn't have a bullet
        if not fact.strip().startswith(('-', '*', '•')):
            fact = f"- {fact}"
        
        # Add with proper spacing (blank line before, newline after)
        new_content = (
            content[:section_end].rstrip() + 
            "\n\n" + fact.strip() + "\n\n" + 
            content[section_end:].lstrip()
        )
        
        path.write_text(new_content, encoding="utf-8")
        self.logger.info(f"Added fact to {section}: {fact[:50]}...")
        
        # Invalidate RAG index
        self._rag_indexed = False
        
        return True
    
    def update_fact(
        self,
        old_text: str,
        new_text: str,
        date_str: Optional[str] = None,
        is_regex: bool = False
    ) -> Tuple[bool, int]:
        """Update/replace a fact in a knowledge file.
        
        Args:
            old_text: Text to find (or regex pattern)
            new_text: Replacement text
            date_str: Target date or None to search all files
            is_regex: Treat old_text as regex pattern
            
        Returns:
            (success, count of replacements)
        """
        if date_str:
            files = [self._get_file_path(date_str)]
        else:
            files = self.list_files()
        
        total_count = 0
        for path in files:
            if not path.exists():
                continue
            
            content = path.read_text(encoding="utf-8")
            
            if is_regex:
                new_content, count = re.subn(old_text, new_text, content)
            else:
                count = content.count(old_text)
                new_content = content.replace(old_text, new_text)
            
            if count > 0:
                path.write_text(new_content, encoding="utf-8")
                total_count += count
                self.logger.info(f"Updated {count} in {path.name}")
        
        if total_count > 0:
            self._rag_indexed = False
        
        return (total_count > 0, total_count)
    
    def delete_fact(
        self,
        text: str,
        date_str: Optional[str] = None,
        is_regex: bool = False
    ) -> Tuple[bool, int]:
        """Delete a fact (line) from knowledge files.
        
        Removes the line containing the text and any surrounding blank lines.
        
        Args:
            text: Text to find (or regex pattern)
            date_str: Target date or None to search all files
            is_regex: Treat text as regex pattern
            
        Returns:
            (success, count of deletions)
        """
        if date_str:
            files = [self._get_file_path(date_str)]
        else:
            files = self.list_files()
        
        total_count = 0
        for path in files:
            if not path.exists():
                continue
            
            content = path.read_text(encoding="utf-8")
            lines = content.split('\n')
            new_lines = []
            deleted = 0
            
            for i, line in enumerate(lines):
                should_delete = False
                if is_regex:
                    if re.search(text, line):
                        should_delete = True
                else:
                    if text in line:
                        should_delete = True
                
                if should_delete:
                    deleted += 1
                    # Skip blank line after if exists
                    continue
                else:
                    new_lines.append(line)
            
            if deleted > 0:
                # Clean up extra blank lines
                new_content = re.sub(r'\n{3,}', '\n\n', '\n'.join(new_lines))
                path.write_text(new_content, encoding="utf-8")
                total_count += deleted
                self.logger.info(f"Deleted {deleted} in {path.name}")
        
        if total_count > 0:
            self._rag_indexed = False
        
        return (total_count > 0, total_count)
    
    def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, str]]:
        """Simple keyword search across all knowledge files.
        
        Args:
            query: Keywords to search for
            max_results: Maximum results to return
            
        Returns:
            List of {file, line, context} dicts
        """
        query_words = query.lower().split()
        results = []
        
        # Require minimum match threshold based on query length
        # For multi-word queries, require at least 2 words to match (or 50% of words)
        if len(query_words) > 2:
            min_score = max(2, len(query_words) // 2)
        else:
            min_score = 1
        
        for path in self.list_files():
            content = path.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                score = sum(1 for w in query_words if w in line_lower)
                
                if score >= min_score and line.strip() and not line.startswith('#'):
                    # Get surrounding context
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    context = '\n'.join(lines[start:end])
                    
                    results.append({
                        'file': path.stem,
                        'line': line.strip(),
                        'context': context,
                        'score': score
                    })
        
        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    def get_context(self, max_chars: int = 3000) -> str:
        """Get knowledge context for system prompt injection.
        
        Extracts facts from recent files, prioritizing content with
        actual facts (not empty sections).
        
        Args:
            max_chars: Maximum characters to return
            
        Returns:
            Context string suitable for system prompt
        """
        files = self.list_files()[:7]  # Last week
        
        facts = []
        for path in files:
            content = path.read_text(encoding="utf-8")
            
            # Extract non-empty lines that aren't headers or comments
            for line in content.split('\n'):
                line = line.strip()
                if (line and 
                    not line.startswith('#') and 
                    not line.startswith('<!--') and
                    not line.endswith('-->')):
                    facts.append(line)
        
        if not facts:
            return ""
        
        # Deduplicate while preserving order
        seen = set()
        unique_facts = []
        for f in facts:
            f_lower = f.lower()
            if f_lower not in seen:
                seen.add(f_lower)
                unique_facts.append(f)
        
        # Build context string with clear framing
        context = "## Background Information (Previously Stored Facts)\n"
        context += "⚠️ NOTE: This is stored background knowledge, NOT the user's current request.\n"
        context += "Only use this information if directly relevant to what the user is asking NOW.\n\n"
        current_len = len(context)
        
        for fact in unique_facts:
            if current_len + len(fact) + 2 > max_chars:
                break
            context += f"- {fact}\n"
            current_len += len(fact) + 3
        
        return context
    
    def get_all_files_for_rag(self) -> List[str]:
        """Get all knowledge file paths for RAG indexing.
        
        Returns:
            List of absolute file paths
        """
        return [str(p.absolute()) for p in self.list_files()]
    
    def ensure_rag_indexed(self, agent=None) -> bool:
        """Ensure all knowledge files are indexed in RAG.
        
        The agent should have RAGMixin with ensure_indexed_files method.
        Knowledge files are registered in the documents table and indexed
        like any other document.
        
        Args:
            agent: Optional agent instance with RAGMixin (has ensure_indexed_files)
            
        Returns:
            True if indexing succeeded or not needed
        """
        if self._rag_indexed:
            return True
        
        try:
            files = self.get_all_files_for_rag()
            if not files:
                self._rag_indexed = True
                return True
            
            # Register knowledge files in documents table if not already
            self._register_knowledge_documents(files)
            
            # If agent provided, use its RAG indexing
            if agent and hasattr(agent, 'ensure_indexed_files'):
                success = agent.ensure_indexed_files(files)
                self._rag_indexed = success
                self.logger.info(f"Indexed {len(files)} knowledge files in RAG")
                return success
            
            # No agent available - will be indexed when agent is available
            self.logger.debug("No agent available for RAG indexing")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to index knowledge files: {e}")
            return False
    
    def _register_knowledge_documents(self, files: List[str]) -> None:
        """Register knowledge files in the documents database.
        
        This ensures they appear in the document list and can be indexed.
        
        Args:
            files: List of absolute file paths
        """
        try:
            from airunner.components.documents.data.models.document import Document
            from airunner.components.data.session_manager import session_scope
            
            with session_scope() as session:
                for file_path in files:
                    # Check if already registered
                    existing = session.query(Document).filter_by(path=file_path).first()
                    if not existing:
                        doc = Document(
                            path=file_path,
                            active=True,
                            indexed=False,
                        )
                        session.add(doc)
                        self.logger.debug(f"Registered knowledge doc: {file_path}")
                session.commit()
        except Exception as e:
            self.logger.error(f"Failed to register knowledge documents: {e}")
    
    def search_rag(
        self,
        query: str,
        k: int = 5,
        agent=None
    ) -> List[str]:
        """Search knowledge using RAG semantic search.
        
        Args:
            query: Search query
            k: Number of results
            agent: Optional agent instance with RAGMixin (has search method)
            
        Returns:
            List of relevant text chunks
        """
        try:
            # Try RAG search if agent available
            if agent and hasattr(agent, 'search'):
                self.ensure_rag_indexed(agent)
                
                # Search and filter for knowledge directory
                results = agent.search(query, k=k * 2)  # Get more, filter later
                
                # Filter to only knowledge directory results
                knowledge_results = []
                knowledge_dir_str = str(self.knowledge_dir)
                for r in results:
                    source = r.metadata.get('source', r.metadata.get('file_path', ''))
                    if knowledge_dir_str in source:
                        knowledge_results.append(r.page_content)
                        if len(knowledge_results) >= k:
                            break
                
                if knowledge_results:
                    return knowledge_results
            
            # Fallback to keyword search
            self.logger.debug("Using keyword search (no RAG agent)")
            keyword_results = self.search(query, max_results=k)
            return [r['line'] for r in keyword_results]
            
        except Exception as e:
            self.logger.error(f"RAG search failed: {e}")
            # Fallback to keyword search
            keyword_results = self.search(query, max_results=k)
            return [r['line'] for r in keyword_results]
