"""Searchable registry for workflow-generated helper projects."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os

from airunner.components.document_editor.project.airunner_helper_project_record import (
    AirunnerHelperProjectRecord,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    HELPER_PROJECT_FILE,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.settings import AIRUNNER_PROJECTS_PATH


def _utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class AirunnerHelperProjectRegistryService:
    """Register and search reusable helper projects."""

    def __init__(self, projects_root: str | None = None):
        """Initialize the registry for one helper-project root."""
        root = projects_root or AIRUNNER_PROJECTS_PATH
        self.projects_root = os.path.expanduser(os.path.abspath(root))
        os.makedirs(self.projects_root, exist_ok=True)

    def metadata_path(self, project_path: str) -> str:
        """Return the metadata file path for one helper project."""
        project_service = AirunnerProjectService(project_path)
        return project_service.resolve_path(HELPER_PROJECT_FILE)

    def register_project(
        self,
        project_path: str,
        record: AirunnerHelperProjectRecord,
    ) -> AirunnerHelperProjectRecord:
        """Persist helper-project metadata for one project."""
        normalized_path = self._normalize_project_path(project_path)
        project_service = AirunnerProjectService(normalized_path)
        if not project_service.exists():
            raise ValueError(
                "Helper project must be an initialized AIRunner project."
            )

        errors = record.validate()
        if errors:
            raise ValueError("\n".join(errors))

        existing = self.load_project(normalized_path)
        now = _utc_now_iso()
        created_at = record.created_at or (
            existing.created_at if existing else now
        )
        updated_at = record.updated_at or now
        last_used_at = record.last_used_at or (
            existing.last_used_at if existing else ""
        )
        persisted = record.with_timestamps(
            created_at=created_at,
            updated_at=updated_at,
            last_used_at=last_used_at,
        )
        payload = json.dumps(persisted.to_dict(), indent=2, sort_keys=True)
        project_service.write_file(
            HELPER_PROJECT_FILE,
            payload + "\n",
            backup=False,
        )
        return persisted

    def load_project(
        self,
        project_path: str,
    ) -> AirunnerHelperProjectRecord | None:
        """Return helper-project metadata when it exists."""
        normalized_path = self._normalize_project_path(project_path)
        project_service = AirunnerProjectService(normalized_path)
        metadata_path = self.metadata_path(normalized_path)
        if not project_service.exists() or not os.path.exists(metadata_path):
            return None
        payload = json.loads(project_service.read_file(HELPER_PROJECT_FILE))
        return AirunnerHelperProjectRecord.from_dict(payload)

    def list_projects(self) -> list[tuple[str, AirunnerHelperProjectRecord]]:
        """Return helper projects with persisted registry metadata."""
        matches: list[tuple[str, AirunnerHelperProjectRecord]] = []
        if not os.path.isdir(self.projects_root):
            return matches
        for name in sorted(os.listdir(self.projects_root)):
            project_path = os.path.join(self.projects_root, name)
            if not os.path.isdir(project_path):
                continue
            record = self.load_project(project_path)
            if record is not None:
                matches.append((project_path, record))
        matches.sort(key=self._project_sort_key, reverse=True)
        return matches

    def search_projects(
        self,
        query: str,
        *,
        workflow_kind: str | None = None,
        limit: int = 5,
    ) -> list[tuple[str, AirunnerHelperProjectRecord]]:
        """Return helper projects matching one reuse query."""
        query_terms = self._query_terms(query)
        scored: list[tuple[int, str, AirunnerHelperProjectRecord]] = []
        for project_path, record in self.list_projects():
            if workflow_kind and record.workflow_kind != workflow_kind:
                continue
            score = self._match_score(project_path, record, query_terms)
            if query_terms and score <= 0:
                continue
            scored.append((score, project_path, record))
        scored.sort(
            key=lambda item: (item[0], self._record_timestamp(item[2])),
            reverse=True,
        )
        return [
            (project_path, record)
            for _score, project_path, record in scored[: max(1, limit)]
        ]

    def record_use(
        self,
        project_path: str,
    ) -> AirunnerHelperProjectRecord:
        """Update the last-used timestamp for one helper project."""
        normalized_path = self._normalize_project_path(project_path)
        record = self.load_project(normalized_path)
        if record is None:
            raise ValueError("Helper project is not registered.")
        updated = record.with_last_used_at(_utc_now_iso())
        return self.register_project(normalized_path, updated)

    def _normalize_project_path(self, project_path: str) -> str:
        """Return one normalized helper-project path under the root."""
        normalized = os.path.expanduser(os.path.abspath(project_path))
        if not self._is_within(normalized, self.projects_root):
            raise ValueError(
                "Helper project must live under the AIRunner Projects root."
            )
        return normalized

    def _is_within(self, candidate_path: str, root_path: str) -> bool:
        """Return whether a candidate path is inside the registry root."""
        candidate = os.path.abspath(candidate_path)
        root = os.path.abspath(root_path)
        return os.path.commonpath([candidate, root]) == root

    def _project_sort_key(
        self,
        item: tuple[str, AirunnerHelperProjectRecord],
    ) -> tuple[str, str]:
        """Return the default list ordering for helper projects."""
        project_path, record = item
        return self._record_timestamp(record), project_path

    def _record_timestamp(self, record: AirunnerHelperProjectRecord) -> str:
        """Return the best timestamp available for sorting."""
        return record.last_used_at or record.updated_at or record.created_at

    def _query_terms(self, query: str) -> list[str]:
        """Return normalized query terms for helper-project search."""
        return [term for term in query.lower().split() if term.strip()]

    def _match_score(
        self,
        project_path: str,
        record: AirunnerHelperProjectRecord,
        query_terms: list[str],
    ) -> int:
        """Return a simple relevance score for one helper project."""
        if not query_terms:
            return 1
        name = record.name.lower()
        tags = {tag.lower() for tag in record.tags}
        blob = "\n".join(
            [
                os.path.basename(project_path).lower(),
                name,
                record.description.lower(),
                record.workflow_kind.lower(),
                record.input_contract.lower(),
                record.output_contract.lower(),
                record.origin_artifact.lower(),
                record.reuse_notes.lower(),
                " ".join(sorted(tags)),
            ]
        )
        score = 0
        for term in query_terms:
            if term in name:
                score += 3
                continue
            if term in tags:
                score += 2
                continue
            if term in blob:
                score += 1
        return score