"""Project manager for long-running agent projects.

Handles CRUD operations for projects, features, progress entries,
and session state through the daemon-backed workspace state API.
"""

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from airunner.components.llm.long_running.data.project_state import (
    create_workspace_record,
    delete_workspace_record,
    DecisionMemory,
    DecisionOutcome,
    FeatureCategory,
    FeatureStatus,
    first_workspace_record,
    get_workspace_record,
    ProgressEntry,
    ProjectFeature,
    ProjectState,
    ProjectStatus,
    query_workspace_records,
    SessionState,
    update_workspace_record,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.log_hygiene import summarize_text

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ProjectManager:
    """Manages long-running agent projects.

    Provides methods for creating projects, managing features,
    logging progress, and maintaining session state.

    Example:
        ```python
        manager = ProjectManager()

        # Create a new project
        project = manager.create_project(
            name="My Web App",
            description="Build a chat application clone",
            working_directory="/path/to/project"
        )

        # Add features
        manager.add_feature(
            project_id=project.id,
            name="User can send messages",
            description="User types a message and it appears in the chat",
            category=FeatureCategory.FUNCTIONAL,
            verification_steps=["Open chat", "Type message", "Click send", "See message"]
        )

        # Start a session
        session = manager.start_session(project.id)

        # Log progress
        manager.log_progress(
            project_id=project.id,
            session_id=session.id,
            action="Implemented message sending",
            outcome="Messages now appear in chat"
        )

        # Mark feature as passing
        manager.update_feature_status(feature_id, FeatureStatus.PASSING)

        # End session
        manager.end_session(session.id, next_action="Add message timestamps")
        ```
    """

    def __init__(self):
        """Initialize project manager."""
        self._logger = logger

    @staticmethod
    def _enum_value(value: Any) -> Any:
        """Return the comparable primitive for enum-like values."""
        return getattr(value, "value", value)

    def _matches(self, value: Any, expected: Any) -> bool:
        """Return True when two enum-like values represent the same state."""
        return self._enum_value(value) == self._enum_value(expected)

    @staticmethod
    def _timestamp_key(value: Any) -> str:
        """Return a stable sort key for datetime-like values."""
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    # =========================================================================
    # Project Operations
    # =========================================================================

    def create_project(
        self,
        name: str,
        description: str,
        working_directory: Optional[str] = None,
        system_prompt: Optional[str] = None,
        init_git: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProjectState:
        """Create a new long-running project.

        Args:
            name: Human-readable project name
            description: What the project aims to achieve
            working_directory: Filesystem path for project files
            system_prompt: Base system prompt for agents
            init_git: Whether to initialize git repository
            metadata: Additional metadata

        Returns:
            Created ProjectState instance

        Raises:
            ValueError: If project with name already exists
        """
        existing = first_workspace_record(
            "ProjectState",
            filters={"name": name},
        )
        if existing is not None:
            raise ValueError(f"Project '{name}' already exists")

        git_path = None
        if working_directory:
            work_dir = Path(working_directory)
            work_dir.mkdir(parents=True, exist_ok=True)
            if init_git:
                git_path = self._init_git_repo(work_dir)

        project = create_workspace_record(
            "ProjectState",
            {
                "name": name,
                "description": description,
                "working_directory": working_directory,
                "git_repo_path": (
                    git_path if working_directory and init_git else None
                ),
                "status": ProjectStatus.INITIALIZING,
                "system_prompt": system_prompt,
                "project_metadata": metadata or {},
            },
        )
        self._logger.info(f"Created project '{name}' (ID: {project.id})")
        return project

    def get_project(self, project_id: int) -> Optional[ProjectState]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            ProjectState or None if not found
        """
        return get_workspace_record("ProjectState", project_id)

    def get_project_by_name(self, name: str) -> Optional[ProjectState]:
        """Get project by name.

        Args:
            name: Project name

        Returns:
            ProjectState or None if not found
        """
        return first_workspace_record(
            "ProjectState",
            filters={"name": name},
        )

    def list_projects(
        self, status: Optional[ProjectStatus] = None
    ) -> List[ProjectState]:
        """List all projects, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of ProjectState instances
        """
        projects = query_workspace_records("ProjectState")
        if status is not None:
            projects = [
                project
                for project in projects
                if self._matches(project.status, status)
            ]
        return sorted(
            projects,
            key=lambda project: self._timestamp_key(
                getattr(project, "updated_at", None)
            ),
            reverse=True,
        )

    def update_project_status(
        self, project_id: int, status: ProjectStatus
    ) -> None:
        """Update project status.

        Args:
            project_id: Project ID
            status: New status
        """
        project = self.get_project(project_id)
        if project is None:
            return
        if update_workspace_record(
            "ProjectState",
            project_id,
            {"status": status},
        ):
            self._logger.info(
                f"Project {project_id} status updated to {status.value}"
            )

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all related data.

        Args:
            project_id: Project ID

        Returns:
            True if deleted, False if not found
        """
        if not delete_workspace_record("ProjectState", project_id):
            return False
            self._logger.info(f"Deleted project {project_id}")
            return True

    # =========================================================================
    # Feature Operations
    # =========================================================================

    def add_feature(
        self,
        project_id: int,
        name: str,
        description: str,
        category: FeatureCategory = FeatureCategory.FUNCTIONAL,
        verification_steps: Optional[List[str]] = None,
        priority: int = 5,
        depends_on: Optional[List[int]] = None,
    ) -> ProjectFeature:
        """Add a feature to a project.

        Args:
            project_id: Parent project ID
            name: Short feature name
            description: Detailed description
            category: Feature category
            verification_steps: Steps to verify feature works
            priority: 1-10 priority
            depends_on: IDs of features this depends on

        Returns:
            Created ProjectFeature instance
        """
        feature = create_workspace_record(
            "ProjectFeature",
            {
                "project_id": project_id,
                "name": name,
                "description": description,
                "category": category,
                "verification_steps": verification_steps or [],
                "priority": priority,
                "depends_on": depends_on or [],
                "status": FeatureStatus.NOT_STARTED,
            },
        )

        project = self.get_project(project_id)
        if project is not None:
            update_workspace_record(
                "ProjectState",
                project_id,
                {"total_features": (project.total_features or 0) + 1},
            )

        self._logger.info(f"Added feature '{name}' to project {project_id}")
        return feature

    def add_features_bulk(
        self, project_id: int, features: List[Dict[str, Any]]
    ) -> List[ProjectFeature]:
        """Add multiple features at once.

        Args:
            project_id: Parent project ID
            features: List of feature dicts with keys:
                - name (required)
                - description (required)
                - category (optional)
                - verification_steps (optional)
                - priority (optional)
                - depends_on (optional)

        Returns:
            List of created features
        """
        created = []
        for feature_data in features:
            created.append(
                create_workspace_record(
                    "ProjectFeature",
                    {
                        "project_id": project_id,
                        "name": feature_data["name"],
                        "description": feature_data.get(
                            "description",
                            "",
                        ),
                        "category": FeatureCategory(
                            feature_data.get("category", "functional")
                        ),
                        "verification_steps": feature_data.get(
                            "verification_steps",
                            [],
                        ),
                        "priority": feature_data.get("priority", 5),
                        "depends_on": feature_data.get(
                            "depends_on",
                            [],
                        ),
                        "status": FeatureStatus.NOT_STARTED,
                    },
                )
            )

        project = self.get_project(project_id)
        if project is not None:
            update_workspace_record(
                "ProjectState",
                project_id,
                {
                    "total_features": (
                        project.total_features or 0
                    ) + len(features)
                },
            )

        self._logger.info(
            f"Added {len(created)} features to project {project_id}"
        )
        return created

    def get_feature(self, feature_id: int) -> Optional[ProjectFeature]:
        """Get feature by ID.

        Args:
            feature_id: Feature ID

        Returns:
            ProjectFeature or None
        """
        return get_workspace_record("ProjectFeature", feature_id)

    def get_project_features(
        self,
        project_id: int,
        status: Optional[FeatureStatus] = None,
        category: Optional[FeatureCategory] = None,
    ) -> List[ProjectFeature]:
        """Get features for a project with optional filters.

        Args:
            project_id: Project ID
            status: Optional status filter
            category: Optional category filter

        Returns:
            List of features
        """
        features = query_workspace_records(
            "ProjectFeature",
            filters={"project_id": project_id},
        )
        if status is not None:
            features = [
                feature
                for feature in features
                if self._matches(feature.status, status)
            ]
        if category is not None:
            features = [
                feature
                for feature in features
                if self._matches(feature.category, category)
            ]
        return sorted(
            features,
            key=lambda feature: getattr(feature, "priority", 0) or 0,
            reverse=True,
        )

    def get_next_feature_to_work_on(
        self, project_id: int
    ) -> Optional[ProjectFeature]:
        """Get the next feature that should be worked on.

        Prioritizes by:
        1. In-progress features (resume)
        2. Not-started features with met dependencies
        3. Failing features (retry)

        Args:
            project_id: Project ID

        Returns:
            Next feature to work on, or None if all passing
        """
        all_features = self.get_project_features(project_id)

        for feature in all_features:
            if self._matches(feature.status, FeatureStatus.IN_PROGRESS):
                return feature

        passing_ids = {
            feature.id
            for feature in all_features
            if self._matches(feature.status, FeatureStatus.PASSING)
        }
        not_started = [
            feature
            for feature in all_features
            if self._matches(feature.status, FeatureStatus.NOT_STARTED)
        ]
        for feature in not_started:
            deps = feature.depends_on or []
            if all(dep_id in passing_ids for dep_id in deps):
                return feature

        failing = [
            feature
            for feature in all_features
            if self._matches(feature.status, FeatureStatus.FAILING)
        ]
        if failing:
            return min(failing, key=lambda feature: feature.attempts or 0)

        return None

    def update_feature_status(
        self,
        feature_id: int,
        status: FeatureStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update feature status.

        Args:
            feature_id: Feature ID
            status: New status
            error: Optional error message (for failing status)
        """
        feature = self.get_feature(feature_id)
        if feature is None:
            return

        old_status = feature.status
        updates: Dict[str, Any] = {"status": status}
        if self._matches(status, FeatureStatus.FAILING):
            updates["attempts"] = (feature.attempts or 0) + 1
            updates["last_error"] = error
        elif self._matches(status, FeatureStatus.PASSING):
            updates["last_error"] = None

        if not update_workspace_record("ProjectFeature", feature_id, updates):
            return

        project = self.get_project(feature.project_id)
        if project is not None:
            passing_features = project.passing_features or 0
            if (
                not self._matches(old_status, FeatureStatus.PASSING)
                and self._matches(status, FeatureStatus.PASSING)
            ):
                passing_features += 1
            elif (
                self._matches(old_status, FeatureStatus.PASSING)
                and not self._matches(status, FeatureStatus.PASSING)
            ):
                passing_features = max(0, passing_features - 1)

            project_updates: Dict[str, Any] = {
                "passing_features": passing_features,
            }
            if (
                passing_features == project.total_features
                and (project.total_features or 0) > 0
            ):
                project_updates["status"] = ProjectStatus.COMPLETED
                self._logger.info(
                    f"Project {project.id} completed! All features passing."
                )
            update_workspace_record(
                "ProjectState",
                project.id,
                project_updates,
            )

        self._logger.info(f"Feature {feature_id} status: {status.value}")

    # =========================================================================
    # Session Operations
    # =========================================================================

    def start_session(
        self,
        project_id: int,
        feature_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """Start a new working session.

        Args:
            project_id: Project ID
            feature_id: Feature to work on (or None to auto-select)
            context_snapshot: Optional context to save

        Returns:
            Created SessionState
        """
        if feature_id is None:
            feature = self.get_next_feature_to_work_on(project_id)
            feature_id = feature.id if feature else None

        if feature_id is not None:
            update_workspace_record(
                "ProjectFeature",
                feature_id,
                {"status": FeatureStatus.IN_PROGRESS},
            )

        session = create_workspace_record(
            "SessionState",
            {
                "project_id": project_id,
                "feature_id": feature_id,
                "context_snapshot": context_snapshot or {},
            },
        )

        project = self.get_project(project_id)
        if project is not None:
            update_workspace_record(
                "ProjectState",
                project_id,
                {"current_feature_id": feature_id},
            )

        self._logger.info(
            f"Started session {session.id} for project {project_id}, "
            f"feature {feature_id}"
        )
        return session

    def end_session(
        self,
        session_id: int,
        working_memory: Optional[Dict[str, Any]] = None,
        next_action: Optional[str] = None,
        error: Optional[str] = None,
        tokens_consumed: int = 0,
    ) -> None:
        """End a working session.

        Args:
            session_id: Session ID
            working_memory: Working memory to preserve
            next_action: Recommended next action for next session
            error: Error that caused session to end
            tokens_consumed: Total tokens used
        """
        session = get_workspace_record("SessionState", session_id)
        if session is None:
            return

        update_workspace_record(
            "SessionState",
            session_id,
            {
                "ended_at": datetime.utcnow().isoformat(),
                "working_memory": working_memory or {},
                "next_recommended_action": next_action,
                "error_state": error,
                "tokens_consumed": tokens_consumed,
            },
        )
        self._logger.info(f"Ended session {session_id}")

    def get_last_session(self, project_id: int) -> Optional[SessionState]:
        """Get the most recent session for a project.

        Args:
            project_id: Project ID

        Returns:
            Most recent SessionState or None
        """
        sessions = query_workspace_records(
            "SessionState",
            filters={"project_id": project_id},
        )
        if not sessions:
            return None
        return max(
            sessions,
            key=lambda session: self._timestamp_key(
                getattr(session, "started_at", None)
            ),
        )

    # =========================================================================
    # Progress Logging
    # =========================================================================

    def log_progress(
        self,
        project_id: int,
        action: str,
        outcome: str,
        session_id: Optional[int] = None,
        feature_id: Optional[int] = None,
        files_changed: Optional[List[str]] = None,
        git_commit: bool = False,
        tokens_used: int = 0,
    ) -> ProgressEntry:
        """Log progress on a project.

        Args:
            project_id: Project ID
            action: What was done
            outcome: What happened
            session_id: Optional session ID
            feature_id: Optional feature ID
            files_changed: List of files modified
            git_commit: Whether to create git commit
            tokens_used: Tokens consumed for this work

        Returns:
            Created ProgressEntry
        """
        commit_hash = None
        if git_commit:
            project = self.get_project(project_id)
            if project and project.git_repo_path:
                commit_hash = self._git_commit(
                    project.git_repo_path,
                    f"{action}\n\n{outcome}",
                    files_changed or [],
                )

        entry = create_workspace_record(
            "ProgressEntry",
            {
                "project_id": project_id,
                "session_id": session_id,
                "feature_id": feature_id,
                "action": action,
                "outcome": outcome,
                "files_changed": files_changed or [],
                "git_commit_hash": commit_hash,
                "tokens_used": tokens_used,
            },
        )

        self._logger.info(f"Logged progress: {action}")
        return entry

    def get_progress_log(
        self, project_id: int, limit: int = 20
    ) -> List[ProgressEntry]:
        """Get recent progress entries for a project.

        Args:
            project_id: Project ID
            limit: Maximum entries to return

        Returns:
            List of ProgressEntry instances
        """
        entries = query_workspace_records(
            "ProgressEntry",
            filters={"project_id": project_id},
        )
        entries = sorted(
            entries,
            key=lambda entry: self._timestamp_key(
                getattr(entry, "timestamp", None)
            ),
            reverse=True,
        )
        return entries[:limit]

    def get_progress_as_text(self, project_id: int, limit: int = 20) -> str:
        """Get progress log as human-readable text.

        Args:
            project_id: Project ID
            limit: Maximum entries

        Returns:
            Formatted progress log string
        """
        entries = self.get_progress_log(project_id, limit)
        if not entries:
            return "No progress recorded yet."

        lines = ["# Progress Log", ""]
        for entry in reversed(entries):  # Chronological order
            lines.append(entry.to_log_string())
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # Decision Memory
    # =========================================================================

    def record_decision(
        self,
        project_id: int,
        context: str,
        decision: str,
        reasoning: str,
        feature_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> DecisionMemory:
        """Record a decision for future reference.

        Args:
            project_id: Project ID
            context: What situation prompted the decision
            decision: What was decided
            reasoning: Why this decision was made
            feature_id: Optional related feature
            tags: Tags for retrieval

        Returns:
            Created DecisionMemory
        """
        memory = create_workspace_record(
            "DecisionMemory",
            {
                "project_id": project_id,
                "feature_id": feature_id,
                "decision_context": context,
                "decision_made": decision,
                "reasoning": reasoning,
                "tags": tags or [],
            },
        )

        self._logger.info(
            "Recorded decision (%s)",
            summarize_text(decision, label="decision"),
        )
        return memory

    def update_decision_outcome(
        self,
        decision_id: int,
        outcome: DecisionOutcome,
        score: float,
        lesson: Optional[str] = None,
    ) -> None:
        """Update a decision with its outcome.

        Args:
            decision_id: Decision ID
            outcome: What happened
            score: -1.0 to 1.0 success score
            lesson: What was learned
        """
        if get_workspace_record("DecisionMemory", decision_id) is None:
            return
        update_workspace_record(
            "DecisionMemory",
            decision_id,
            {
                "outcome": outcome,
                "outcome_score": max(-1.0, min(1.0, score)),
                "lesson_learned": lesson,
            },
        )

    def get_relevant_decisions(
        self,
        project_id: int,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[DecisionMemory]:
        """Get relevant past decisions.

        Args:
            project_id: Project ID
            tags: Tags to filter by
            limit: Maximum results

        Returns:
            List of relevant decisions
        """
        decisions = query_workspace_records(
            "DecisionMemory",
            filters={"project_id": project_id},
        )
        if tags:
            tag_set = set(tags)
            decisions = [
                decision
                for decision in decisions
                if tag_set.intersection(set(decision.tags or []))
            ]

        decisions = sorted(
            decisions,
            key=lambda decision: self._timestamp_key(
                getattr(decision, "timestamp", None)
            ),
            reverse=True,
        )
        return decisions[:limit]

    # =========================================================================
    # Git Operations
    # =========================================================================

    def _init_git_repo(self, path: Path) -> Optional[str]:
        """Initialize git repository.

        Args:
            path: Directory path

        Returns:
            Git repo path or None if failed
        """
        try:
            git_dir = path / ".git"
            if not git_dir.exists():
                subprocess.run(
                    ["git", "init"],
                    cwd=str(path),
                    check=True,
                    capture_output=True,
                )
                self._logger.info(f"Initialized git repo at {path}")
            return str(path)
        except Exception as e:
            self._logger.error(f"Failed to init git: {e}")
            return None

    def _git_commit(
        self, repo_path: str, message: str, files: List[str]
    ) -> Optional[str]:
        """Create a git commit.

        Args:
            repo_path: Repository path
            message: Commit message
            files: Files to commit (empty for all changes)

        Returns:
            Commit hash or None if failed
        """
        try:
            # Stage files
            if files:
                subprocess.run(
                    ["git", "add"] + files,
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Get hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()

        except Exception as e:
            self._logger.error(f"Git commit failed: {e}")
            return None

    def git_revert_to_commit(
        self, project_id: int, commit_hash: str
    ) -> bool:
        """Revert project to a specific commit.

        Args:
            project_id: Project ID
            commit_hash: Commit to revert to

        Returns:
            True if successful
        """
        project = self.get_project(project_id)
        if not project or not project.git_repo_path:
            return False

        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                cwd=project.git_repo_path,
                check=True,
                capture_output=True,
            )
            self._logger.info(f"Reverted to commit {commit_hash[:7]}")
            return True
        except Exception as e:
            self._logger.error(f"Git revert failed: {e}")
            return False

    def get_git_log(
        self, project_id: int, limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent git commits.

        Args:
            project_id: Project ID
            limit: Maximum commits

        Returns:
            List of commit dicts with hash, message, date
        """
        project = self.get_project(project_id)
        if not project or not project.git_repo_path:
            return []

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-{limit}",
                    "--pretty=format:%H|%s|%ai",
                ],
                cwd=project.git_repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) == 3:
                        commits.append(
                            {
                                "hash": parts[0],
                                "message": parts[1],
                                "date": parts[2],
                            }
                        )
            return commits

        except Exception as e:
            self._logger.error(f"Git log failed: {e}")
            return []
