"""Project-scoped indexing and retrieval for coding workspace context."""

from dataclasses import dataclass, field
import ast
import json
import os
import re
from typing import Any

from airunner.components.agents.runtime.agent_run_record import AgentRunRecord
from airunner.components.agents.runtime.agent_runtime_support import (
    copy_dict,
    utc_now_iso,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    PROJECT_DIR_NAME,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)


@dataclass(slots=True)
class AirunnerProjectContextIndexEntry:
    """One searchable project-context index entry."""

    artifact_type: str
    root_name: str
    rel_path: str
    title: str
    summary: str
    search_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the index entry to JSON-compatible data."""
        return {
            "artifact_type": self.artifact_type,
            "root_name": self.root_name,
            "rel_path": self.rel_path,
            "title": self.title,
            "summary": self.summary,
            "search_text": self.search_text,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "AirunnerProjectContextIndexEntry":
        """Deserialize one persisted context index entry."""
        return cls(
            artifact_type=payload.get("artifact_type", "artifact"),
            root_name=payload.get("root_name", "workspace"),
            rel_path=payload.get("rel_path", ""),
            title=payload.get("title", ""),
            summary=payload.get("summary", ""),
            search_text=payload.get("search_text", ""),
            metadata=copy_dict(payload.get("metadata")),
        )


@dataclass(slots=True)
class AirunnerProjectContextIndex:
    """Persisted project-context index stored under .airunner/indexes/."""

    generated_at: str = field(default_factory=utc_now_iso)
    schema_version: int = 1
    entries: list[AirunnerProjectContextIndexEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full project context index."""
        return {
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "AirunnerProjectContextIndex":
        """Deserialize the persisted project context index."""
        return cls(
            generated_at=payload.get("generated_at") or utc_now_iso(),
            schema_version=int(payload.get("schema_version", 1)),
            entries=[
                AirunnerProjectContextIndexEntry.from_dict(item)
                for item in payload.get("entries", [])
            ],
        )


class AirunnerProjectContextIndexService:
    """Build and query a simple persisted project context index."""

    _text_extensions = {".md", ".py", ".txt", ".json", ".yaml", ".yml"}

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service
        self._workspace_manager = project_service.workspace_manager

    def build_index(
        self,
        *,
        persist: bool = True,
        max_entries: int = 500,
    ) -> AirunnerProjectContextIndex:
        """Build an index over project sources and .airunner artifacts."""
        entries = self._workspace_entries(max_entries)
        remaining = max(0, max_entries - len(entries))
        entries.extend(self._airunner_artifact_entries(remaining))
        index = AirunnerProjectContextIndex(entries=entries[:max_entries])
        if persist:
            self._save_index(index)
        return index

    def load_index(self) -> AirunnerProjectContextIndex | None:
        """Load the persisted project context index if it exists."""
        rel_path = self._index_path()
        if not self._workspace_manager.exists(rel_path):
            return None
        return AirunnerProjectContextIndex.from_dict(
            json.loads(self._workspace_manager.read_file(rel_path))
        )

    def query_index(
        self,
        query: str,
        *,
        limit: int = 5,
        rebuild_if_missing: bool = True,
    ) -> dict[str, object]:
        """Query the project context index with a simple keyword scorer."""
        index = self.load_index()
        if index is None and rebuild_if_missing:
            index = self.build_index(persist=False)
        if index is None:
            return {
                "generated_at": None,
                "match_count": 0,
                "results": [],
                "context": "",
            }
        query_words = self._query_words(query)
        matches: list[tuple[int, AirunnerProjectContextIndexEntry]] = []
        for entry in index.entries:
            score = self._score_entry(entry, query_words)
            if score > 0:
                matches.append((score, entry))
        matches.sort(
            key=lambda item: (
                -item[0],
                item[1].artifact_type,
                item[1].root_name,
                item[1].rel_path,
            )
        )
        limited = matches[:limit]
        return {
            "generated_at": index.generated_at,
            "match_count": len(limited),
            "results": [
                {**entry.to_dict(), "score": score}
                for score, entry in limited
            ],
            "context": self._render_context(limited),
        }

    def _workspace_entries(
        self,
        max_entries: int,
    ) -> list[AirunnerProjectContextIndexEntry]:
        entries: list[AirunnerProjectContextIndexEntry] = []
        for root in self.project_service.list_roots():
            manager = self.project_service.get_workspace_manager(root.name)
            for rel_path in manager.list_files("", pattern="*", recursive=True):
                if rel_path.startswith(PROJECT_DIR_NAME):
                    continue
                if len(entries) >= max_entries:
                    return entries
                file_info = manager.get_file_info(rel_path)
                if not file_info.get("is_file"):
                    continue
                extension = os.path.splitext(rel_path)[1].lower()
                if extension not in self._text_extensions:
                    continue
                entry = self._workspace_entry(root.name, rel_path)
                if entry is not None:
                    entries.append(entry)
        return entries

    def _workspace_entry(
        self,
        root_name: str,
        rel_path: str,
    ) -> AirunnerProjectContextIndexEntry | None:
        content = self.project_service.read_file(rel_path, root_name)
        extension = os.path.splitext(rel_path)[1].lower()
        if extension == ".py":
            return self._python_entry(root_name, rel_path, content)
        return self._text_entry(
            artifact_type="project-file",
            root_name=root_name,
            rel_path=rel_path,
            content=content,
        )

    def _python_entry(
        self,
        root_name: str,
        rel_path: str,
        content: str,
    ) -> AirunnerProjectContextIndexEntry:
        symbols: list[str] = []
        docstring = ""
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree) or ""
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(node.name)
                if isinstance(node, ast.ClassDef):
                    symbols.append(node.name)
        except SyntaxError:
            docstring = ""
        snippet = docstring.splitlines()[0] if docstring else "Python source file"
        symbol_text = ", ".join(symbols[:8])
        summary = snippet
        if symbol_text:
            summary = f"{snippet}. Symbols: {symbol_text}"
        return AirunnerProjectContextIndexEntry(
            artifact_type="source",
            root_name=root_name,
            rel_path=rel_path,
            title=os.path.basename(rel_path),
            summary=summary,
            search_text=" ".join([rel_path, snippet, symbol_text]).strip(),
            metadata={"symbols": symbols[:20]},
        )

    def _text_entry(
        self,
        *,
        artifact_type: str,
        root_name: str,
        rel_path: str,
        content: str,
    ) -> AirunnerProjectContextIndexEntry:
        title = self._first_heading(content) or os.path.basename(rel_path)
        snippet = self._content_excerpt(content)
        search_text = " ".join([rel_path, title, snippet]).strip()
        return AirunnerProjectContextIndexEntry(
            artifact_type=artifact_type,
            root_name=root_name,
            rel_path=rel_path,
            title=title,
            summary=snippet,
            search_text=search_text,
        )

    def _airunner_artifact_entries(
        self,
        max_entries: int,
    ) -> list[AirunnerProjectContextIndexEntry]:
        rel_paths = [
            ("plan", os.path.join(PROJECT_DIR_NAME, "plans"), "*.md"),
            ("memory", os.path.join(PROJECT_DIR_NAME, "memory"), "*.md"),
        ]
        entries: list[AirunnerProjectContextIndexEntry] = []
        for artifact_type, directory, pattern in rel_paths:
            for rel_path in self._workspace_manager.list_files(
                directory,
                pattern=pattern,
                recursive=False,
            ):
                if len(entries) >= max_entries:
                    return entries
                content = self._workspace_manager.read_file(rel_path)
                entries.append(
                    self._text_entry(
                        artifact_type=artifact_type,
                        root_name=PROJECT_DIR_NAME,
                        rel_path=rel_path,
                        content=content,
                    )
                )
        for rel_path in self._workspace_manager.list_files(
            os.path.join(PROJECT_DIR_NAME, "audit", "runs"),
            pattern="*.json",
            recursive=False,
        ):
            if len(entries) >= max_entries:
                return entries
            run = AgentRunRecord.from_dict(
                json.loads(self._workspace_manager.read_file(rel_path))
            )
            entries.append(self._run_entry(rel_path, run))
        return entries

    def _run_entry(
        self,
        rel_path: str,
        run: AgentRunRecord,
    ) -> AirunnerProjectContextIndexEntry:
        summary = run.summary or self._content_excerpt(
            "\n".join(message.content for message in run.messages[-3:])
        )
        title = f"Run {run.record_id} ({run.status.value})"
        search_text = " ".join([title, summary, run.role.value])
        return AirunnerProjectContextIndexEntry(
            artifact_type="run-summary",
            root_name=PROJECT_DIR_NAME,
            rel_path=rel_path,
            title=title,
            summary=summary,
            search_text=search_text,
            metadata={
                "task_id": run.task_id,
                "status": run.status.value,
                "role": run.role.value,
            },
        )

    def _save_index(self, index: AirunnerProjectContextIndex) -> None:
        self._workspace_manager.write_file(
            self._index_path(),
            json.dumps(index.to_dict(), indent=2, sort_keys=True) + "\n",
            backup=True,
            create_dirs=True,
        )

    def _index_path(self) -> str:
        return os.path.join(
            PROJECT_DIR_NAME,
            "indexes",
            "project_context_index.json",
        )

    def _query_words(self, query: str) -> list[str]:
        return [item for item in re.split(r"[^a-z0-9_./-]+", query.lower()) if item]

    def _score_entry(
        self,
        entry: AirunnerProjectContextIndexEntry,
        query_words: list[str],
    ) -> int:
        if not query_words:
            return 0
        rel_path = entry.rel_path.lower()
        title = entry.title.lower()
        search_text = entry.search_text.lower()
        score = 0
        for word in query_words:
            if word in rel_path:
                score += 4
            if word in title:
                score += 3
            if word in search_text:
                score += 1
        return score

    def _render_context(
        self,
        matches: list[tuple[int, AirunnerProjectContextIndexEntry]],
    ) -> str:
        sections = []
        for score, entry in matches:
            sections.append(
                "\n".join(
                    [
                        (
                            f"- [{entry.artifact_type}] {entry.root_name}:"
                            f"{entry.rel_path} (score {score})"
                        ),
                        f"  {entry.summary}",
                    ]
                )
            )
        return "\n\n".join(sections)

    def _first_heading(self, content: str) -> str | None:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("# ")
        return None

    def _content_excerpt(self, content: str, limit: int = 180) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        snippet = " ".join(lines[:3]) if lines else "No summary available."
        return snippet[:limit]