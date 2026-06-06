"""Service-owned knowledge base helpers."""

import re
import threading
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from airunner_services.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner_services.data.tenant import get_tenant_key
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

KNOWLEDGE_DIR = Path(AIRUNNER_BASE_PATH) / "text" / "knowledge"

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

_knowledge_base_instances: dict[str, "KnowledgeBase"] = {}
_lock = threading.Lock()


def get_daily_template(date_str: str) -> str:
    """Return the template for one new daily knowledge file."""
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


def _safe_tenant_dir_name(raw: str) -> str:
    """Return one filesystem-safe identifier for a tenant key."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return "default"

    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", cleaned)
    return cleaned[:120] or "default"


def get_knowledge_base() -> "KnowledgeBase":
    """Return a tenant-scoped knowledge-base instance."""
    tenant_key = (get_tenant_key() or "").strip()
    tenant_id = _safe_tenant_dir_name(tenant_key)

    with _lock:
        instance = _knowledge_base_instances.get(tenant_id)
        if instance is None:
            tenant_dir = KNOWLEDGE_DIR / "tenants" / tenant_id
            instance = KnowledgeBase(knowledge_dir=tenant_dir)
            _knowledge_base_instances[tenant_id] = instance

    return instance


def _extract_entities(text: str) -> set[str]:
    """Extract simple capitalized entities from one fact string."""
    return set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text or ""))


class KnowledgeBase:
    """Markdown-based knowledge storage with daily files."""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.logger = logger
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self._rag_indexed = False
        self.logger.info(
            "KnowledgeBase initialized: %s",
            self.knowledge_dir,
        )

    def _get_today_path(self) -> Path:
        return self.knowledge_dir / f"{date.today().isoformat()}.md"

    def _get_file_path(self, date_str: Optional[str] = None) -> Path:
        if date_str is None:
            return self._get_today_path()
        return self.knowledge_dir / f"{date_str}.md"

    def _ensure_today_file(self) -> Path:
        path = self._get_today_path()
        if not path.exists():
            today = date.today().isoformat()
            path.write_text(get_daily_template(today), encoding="utf-8")
            self.logger.info("Created new knowledge file: %s", path)
        return path

    def list_files(self) -> List[Path]:
        files = list(self.knowledge_dir.glob("*.md"))
        files.sort(key=lambda path: path.stem, reverse=True)
        return files

    def read_file(self, date_str: Optional[str] = None) -> str:
        path = self._get_file_path(date_str)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def read_all(self, max_files: int = 30) -> str:
        parts = []
        for path in self.list_files()[:max_files]:
            content = path.read_text(encoding="utf-8")
            if content.strip():
                parts.append(f"# From {path.stem}\n\n{content}")
        return "\n\n---\n\n".join(parts)

    def _normalize_fact(self, fact: str) -> str:
        normalized = fact.strip()
        if normalized.startswith(("-", "*", "•")):
            normalized = normalized[1:].strip()
        return normalized.lower()

    def _is_duplicate_fact(self, fact: str, section_content: str) -> bool:
        normalized_new = self._normalize_fact(fact)
        existing_facts = []
        for line in section_content.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                existing_facts.append(self._normalize_fact(stripped))

        for existing in existing_facts:
            if not existing:
                continue
            if normalized_new == existing or normalized_new in existing:
                self.logger.debug(
                    "Duplicate fact detected (%s)",
                    summarize_text(fact, label="fact"),
                )
                return True

            new_entities = _extract_entities(fact)
            existing_entities = _extract_entities(existing)
            if not new_entities or not existing_entities:
                continue

            overlap = len(new_entities & existing_entities)
            total = max(len(new_entities), len(existing_entities))
            if overlap / total <= 0.8:
                continue

            new_words = set(normalized_new.split())
            existing_words = set(existing.split())
            word_overlap = len(new_words & existing_words) / max(
                len(new_words),
                len(existing_words),
            )
            if word_overlap > 0.7:
                self.logger.debug(
                    "Duplicate fact semantic match (%s)",
                    summarize_text(fact, label="fact"),
                )
                return True

        return False

    def add_fact(
        self,
        fact: str,
        section: str = "Notes",
        date_str: Optional[str] = None,
    ) -> bool:
        path = (
            self._ensure_today_file()
            if date_str is None
            else self._get_file_path(date_str)
        )
        if date_str is not None and not path.exists():
            path.write_text(get_daily_template(date_str), encoding="utf-8")

        content = path.read_text(encoding="utf-8")
        section_pattern = rf"^## {re.escape(section)}\s*$"
        match = re.search(section_pattern, content, re.MULTILINE)
        if not match:
            self.logger.warning("Section '%s' not found", section)
            return False

        section_start = match.end()
        next_section = re.search(
            r"^## ", content[section_start:], re.MULTILINE
        )
        section_end = (
            section_start + next_section.start()
            if next_section
            else len(content)
        )
        section_content = content[section_start:section_end]
        if self._is_duplicate_fact(fact, section_content):
            self.logger.info(
                "Skipping duplicate fact (%s)",
                summarize_text(fact, label="fact"),
            )
            return False

        if not fact.strip().startswith(("-", "*", "•")):
            fact = f"- {fact}"

        new_content = (
            content[:section_end].rstrip()
            + "\n\n"
            + fact.strip()
            + "\n\n"
            + content[section_end:].lstrip()
        )
        path.write_text(new_content, encoding="utf-8")
        self.logger.info(
            "Added fact to %s (%s)",
            section,
            summarize_text(fact, label="fact"),
        )
        self._rag_indexed = False
        return True

    def update_fact(
        self,
        old_text: str,
        new_text: str,
        date_str: Optional[str] = None,
        is_regex: bool = False,
    ) -> Tuple[bool, int]:
        files = (
            [self._get_file_path(date_str)] if date_str else self.list_files()
        )
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
                self.logger.info("Updated %d in %s", count, path.name)

        if total_count > 0:
            self._rag_indexed = False
        return total_count > 0, total_count

    def delete_fact(
        self,
        text: str,
        date_str: Optional[str] = None,
        is_regex: bool = False,
    ) -> Tuple[bool, int]:
        files = (
            [self._get_file_path(date_str)] if date_str else self.list_files()
        )
        total_count = 0

        for path in files:
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8").split("\n")
            new_lines = []
            deleted = 0
            for line in lines:
                matches = re.search(text, line) if is_regex else text in line
                if matches:
                    deleted += 1
                    continue
                new_lines.append(line)

            if deleted > 0:
                new_content = re.sub(r"\n{3,}", "\n\n", "\n".join(new_lines))
                path.write_text(new_content, encoding="utf-8")
                total_count += deleted
                self.logger.info("Deleted %d in %s", deleted, path.name)

        if total_count > 0:
            self._rag_indexed = False
        return total_count > 0, total_count

    def search(
        self, query: str, max_results: int = 10
    ) -> List[Dict[str, str]]:
        query_words = query.lower().split()
        min_score = (
            max(2, len(query_words) // 2) if len(query_words) > 2 else 1
        )
        results = []

        for path in self.list_files():
            lines = path.read_text(encoding="utf-8").split("\n")
            for index, line in enumerate(lines):
                line_lower = line.lower()
                score = sum(1 for word in query_words if word in line_lower)
                if (
                    score < min_score
                    or not line.strip()
                    or line.startswith("#")
                ):
                    continue

                start = max(0, index - 1)
                end = min(len(lines), index + 2)
                results.append(
                    {
                        "file": path.stem,
                        "line": line.strip(),
                        "context": "\n".join(lines[start:end]),
                        "score": score,
                    }
                )

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:max_results]

    def get_context(self, max_chars: int = 3000) -> str:
        facts = []
        for path in self.list_files()[:7]:
            content = path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if (
                    stripped
                    and not stripped.startswith("#")
                    and not stripped.startswith("<!--")
                    and not stripped.endswith("-->")
                ):
                    facts.append(stripped)

        if not facts:
            return ""

        seen = set()
        unique_facts = []
        for fact in facts:
            key = fact.lower()
            if key not in seen:
                seen.add(key)
                unique_facts.append(fact)

        context = (
            "## Background Information (Previously Stored Facts)\n"
            "⚠️ NOTE: This is stored background knowledge, NOT the user's "
            "current request.\n"
            "Only use this information if directly relevant to what the user "
            "is asking NOW.\n\n"
        )
        current_len = len(context)
        for fact in unique_facts:
            if current_len + len(fact) + 3 > max_chars:
                break
            context += f"- {fact}\n"
            current_len += len(fact) + 3
        return context

    def get_all_files_for_rag(self) -> List[str]:
        return [str(path.absolute()) for path in self.list_files()]

    def ensure_rag_indexed(self, agent=None) -> bool:
        if self._rag_indexed:
            return True

        try:
            files = self.get_all_files_for_rag()
            if not files:
                self._rag_indexed = True
                return True

            self._register_knowledge_documents(files)
            if agent and hasattr(agent, "ensure_indexed_files"):
                success = agent.ensure_indexed_files(files)
                self._rag_indexed = success
                self.logger.info(
                    "Indexed %d knowledge files in RAG",
                    len(files),
                )
                return success

            self.logger.debug("No agent available for RAG indexing")
            return True
        except Exception as exc:
            self.logger.error("Failed to index knowledge files: %s", exc)
            return False

    def _register_knowledge_documents(self, files: List[str]) -> None:
        try:
            from airunner_services.database.models.document import Document
            from airunner_services.database.session import session_scope

            with session_scope() as session:
                for file_path in files:
                    existing = (
                        session.query(Document)
                        .filter_by(path=file_path)
                        .first()
                    )
                    if existing:
                        continue
                    session.add(
                        Document(
                            path=file_path,
                            active=True,
                            indexed=False,
                        )
                    )
                    self.logger.debug(
                        "Registered knowledge doc: %s",
                        file_path,
                    )
                session.commit()
        except Exception as exc:
            self.logger.error(
                "Failed to register knowledge documents: %s", exc
            )

    def search_rag(
        self,
        query: str,
        k: int = 5,
        agent=None,
    ) -> List[str]:
        try:
            if agent and hasattr(agent, "search"):
                self.ensure_rag_indexed(agent)
                results = agent.search(query, k=k * 2)
                knowledge_results = []
                knowledge_dir_str = str(self.knowledge_dir)
                for result in results:
                    metadata = getattr(result, "metadata", {})
                    source = metadata.get(
                        "source", metadata.get("file_path", "")
                    )
                    if knowledge_dir_str not in source:
                        continue
                    knowledge_results.append(result.page_content)
                    if len(knowledge_results) >= k:
                        break
                if knowledge_results:
                    return knowledge_results

            self.logger.debug("Using keyword search (no RAG agent)")
            return [item["line"] for item in self.search(query, max_results=k)]
        except Exception as exc:
            self.logger.error("RAG search failed: %s", exc)
            return [item["line"] for item in self.search(query, max_results=k)]


__all__ = ["KNOWLEDGE_DIR", "KnowledgeBase", "get_knowledge_base"]
