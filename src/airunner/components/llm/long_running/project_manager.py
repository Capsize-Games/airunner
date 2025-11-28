"""Project manager for long-running agent projects.

Handles CRUD operations for projects, features, progress entries,
and session state. Acts as the persistence layer for the harness.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import subprocess

from sqlalchemy.orm import Session, make_transient

from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    ProjectFeature,
    ProgressEntry,
    SessionState,
    DecisionMemory,
    ProjectStatus,
    FeatureStatus,
    FeatureCategory,
    DecisionOutcome,
)
from airunner.components.data.session_manager import session_scope
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

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

    def _detach(self, db: Session, obj):
        """Detach an object from the session so it can be used outside.
        
        Args:
            db: The database session
            obj: The ORM object to detach
            
        Returns:
            The detached object
        """
        if obj is not None:
            db.expunge(obj)
            make_transient(obj)
        return obj
    
    def _detach_all(self, db: Session, objects: List):
        """Detach a list of objects from the session.
        
        Args:
            db: The database session
            objects: List of ORM objects to detach
            
        Returns:
            List of detached objects
        """
        for obj in objects:
            self._detach(db, obj)
        return objects

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
        with session_scope() as db:
            # Check for existing project
            existing = (
                db.query(ProjectState)
                .filter(ProjectState.name == name)
                .first()
            )
            if existing:
                raise ValueError(f"Project '{name}' already exists")

            # Create working directory if specified
            if working_directory:
                work_dir = Path(working_directory)
                work_dir.mkdir(parents=True, exist_ok=True)

                # Initialize git if requested
                git_path = None
                if init_git:
                    git_path = self._init_git_repo(work_dir)

            project = ProjectState(
                name=name,
                description=description,
                working_directory=working_directory,
                git_repo_path=git_path if working_directory and init_git else None,
                status=ProjectStatus.INITIALIZING,
                system_prompt=system_prompt,
                project_metadata=metadata or {},
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            
            self._logger.info(f"Created project '{name}' (ID: {project.id})")
            return self._detach(db, project)

    def get_project(self, project_id: int) -> Optional[ProjectState]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            ProjectState or None if not found
        """
        with session_scope() as db:
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            return self._detach(db, project)

    def get_project_by_name(self, name: str) -> Optional[ProjectState]:
        """Get project by name.

        Args:
            name: Project name

        Returns:
            ProjectState or None if not found
        """
        with session_scope() as db:
            project = (
                db.query(ProjectState)
                .filter(ProjectState.name == name)
                .first()
            )
            return self._detach(db, project)

    def list_projects(
        self, status: Optional[ProjectStatus] = None
    ) -> List[ProjectState]:
        """List all projects, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of ProjectState instances
        """
        with session_scope() as db:
            query = db.query(ProjectState)
            if status:
                query = query.filter(ProjectState.status == status)
            projects = query.order_by(ProjectState.updated_at.desc()).all()
            return self._detach_all(db, projects)

    def update_project_status(
        self, project_id: int, status: ProjectStatus
    ) -> None:
        """Update project status.

        Args:
            project_id: Project ID
            status: New status
        """
        with session_scope() as db:
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            if project:
                project.status = status
                project.updated_at = datetime.utcnow()
                db.commit()
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
        with session_scope() as db:
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            if not project:
                return False
            db.delete(project)
            db.commit()
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
        with session_scope() as db:
            feature = ProjectFeature(
                project_id=project_id,
                name=name,
                description=description,
                category=category,
                verification_steps=verification_steps or [],
                priority=priority,
                depends_on=depends_on or [],
                status=FeatureStatus.NOT_STARTED,
            )
            db.add(feature)

            # Update project feature count
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            if project:
                project.total_features = (project.total_features or 0) + 1

            db.commit()
            db.refresh(feature)

            self._logger.info(f"Added feature '{name}' to project {project_id}")
            return self._detach(db, feature)

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
        with session_scope() as db:
            for f in features:
                feature = ProjectFeature(
                    project_id=project_id,
                    name=f["name"],
                    description=f.get("description", ""),
                    category=FeatureCategory(f.get("category", "functional")),
                    verification_steps=f.get("verification_steps", []),
                    priority=f.get("priority", 5),
                    depends_on=f.get("depends_on", []),
                    status=FeatureStatus.NOT_STARTED,
                )
                db.add(feature)
                created.append(feature)

            # Update project feature count
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            if project:
                project.total_features = (project.total_features or 0) + len(features)

            db.commit()
            for f in created:
                db.refresh(f)

            self._logger.info(f"Added {len(created)} features to project {project_id}")
            return self._detach_all(db, created)

    def get_feature(self, feature_id: int) -> Optional[ProjectFeature]:
        """Get feature by ID.

        Args:
            feature_id: Feature ID

        Returns:
            ProjectFeature or None
        """
        with session_scope() as db:
            feature = (
                db.query(ProjectFeature)
                .filter(ProjectFeature.id == feature_id)
                .first()
            )
            return self._detach(db, feature)

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
        with session_scope() as db:
            query = db.query(ProjectFeature).filter(
                ProjectFeature.project_id == project_id
            )
            if status:
                query = query.filter(ProjectFeature.status == status)
            if category:
                query = query.filter(ProjectFeature.category == category)
            features = query.order_by(ProjectFeature.priority.desc()).all()
            return self._detach_all(db, features)

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
        with session_scope() as db:
            # First check for in-progress features
            in_progress = (
                db.query(ProjectFeature)
                .filter(
                    ProjectFeature.project_id == project_id,
                    ProjectFeature.status == FeatureStatus.IN_PROGRESS,
                )
                .first()
            )
            if in_progress:
                return self._detach(db, in_progress)

            # Get all features for dependency checking
            all_features = (
                db.query(ProjectFeature)
                .filter(ProjectFeature.project_id == project_id)
                .all()
            )
            passing_ids = {
                f.id for f in all_features if f.status == FeatureStatus.PASSING
            }

            # Find not-started features with met dependencies
            not_started = [
                f
                for f in all_features
                if f.status == FeatureStatus.NOT_STARTED
            ]
            for feature in sorted(
                not_started, key=lambda x: x.priority, reverse=True
            ):
                # Check dependencies
                deps = feature.depends_on or []
                if all(dep_id in passing_ids for dep_id in deps):
                    return self._detach(db, feature)

            # Fall back to failing features (retry)
            failing = [
                f
                for f in all_features
                if f.status == FeatureStatus.FAILING
            ]
            if failing:
                # Return the one with fewest attempts
                feature = min(failing, key=lambda x: x.attempts or 0)
                return self._detach(db, feature)

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
        with session_scope() as db:
            feature = (
                db.query(ProjectFeature)
                .filter(ProjectFeature.id == feature_id)
                .first()
            )
            if not feature:
                return

            old_status = feature.status
            feature.status = status
            feature.updated_at = datetime.utcnow()

            if status == FeatureStatus.FAILING:
                feature.attempts = (feature.attempts or 0) + 1
                feature.last_error = error
            elif status == FeatureStatus.PASSING:
                feature.last_error = None

            # Update project passing count
            project = (
                db.query(ProjectState)
                .filter(ProjectState.id == feature.project_id)
                .first()
            )
            if project:
                if (
                    old_status != FeatureStatus.PASSING
                    and status == FeatureStatus.PASSING
                ):
                    project.passing_features = (project.passing_features or 0) + 1
                elif (
                    old_status == FeatureStatus.PASSING
                    and status != FeatureStatus.PASSING
                ):
                    project.passing_features = max(
                        0, (project.passing_features or 0) - 1
                    )

                # Check if all features passing
                if (
                    project.passing_features == project.total_features
                    and project.total_features > 0
                ):
                    project.status = ProjectStatus.COMPLETED
                    self._logger.info(
                        f"Project {project.id} completed! All features passing."
                    )

            db.commit()
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
        with session_scope() as db:
            # Auto-select feature if not specified
            if feature_id is None:
                feature = self.get_next_feature_to_work_on(project_id)
                feature_id = feature.id if feature else None

            # Mark feature as in-progress
            if feature_id:
                feat = (
                    db.query(ProjectFeature)
                    .filter(ProjectFeature.id == feature_id)
                    .first()
                )
                if feat:
                    feat.status = FeatureStatus.IN_PROGRESS

            session = SessionState(
                project_id=project_id,
                feature_id=feature_id,
                context_snapshot=context_snapshot or {},
                started_at=datetime.utcnow(),
            )
            db.add(session)

            # Update project current feature
            project = db.query(ProjectState).filter(ProjectState.id == project_id).first()
            if project:
                project.current_feature_id = feature_id

            db.commit()
            db.refresh(session)

            self._logger.info(
                f"Started session {session.id} for project {project_id}, "
                f"feature {feature_id}"
            )
            return self._detach(db, session)

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
        with session_scope() as db:
            session = (
                db.query(SessionState)
                .filter(SessionState.id == session_id)
                .first()
            )
            if not session:
                return

            session.ended_at = datetime.utcnow()
            session.working_memory = working_memory or {}
            session.next_recommended_action = next_action
            session.error_state = error
            session.tokens_consumed = tokens_consumed

            db.commit()
            self._logger.info(f"Ended session {session_id}")

    def get_last_session(self, project_id: int) -> Optional[SessionState]:
        """Get the most recent session for a project.

        Args:
            project_id: Project ID

        Returns:
            Most recent SessionState or None
        """
        with session_scope() as db:
            session = (
                db.query(SessionState)
                .filter(SessionState.project_id == project_id)
                .order_by(SessionState.started_at.desc())
                .first()
            )
            return self._detach(db, session)

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
        with session_scope() as db:
            # Get git commit hash if committing
            commit_hash = None
            if git_commit:
                project = (
                    db.query(ProjectState)
                    .filter(ProjectState.id == project_id)
                    .first()
                )
                if project and project.git_repo_path:
                    commit_hash = self._git_commit(
                        project.git_repo_path,
                        f"{action}\n\n{outcome}",
                        files_changed or [],
                    )

            entry = ProgressEntry(
                project_id=project_id,
                session_id=session_id,
                feature_id=feature_id,
                action=action,
                outcome=outcome,
                files_changed=files_changed or [],
                git_commit_hash=commit_hash,
                tokens_used=tokens_used,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)

            self._logger.info(f"Logged progress: {action}")
            return self._detach(db, entry)

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
        with session_scope() as db:
            entries = (
                db.query(ProgressEntry)
                .filter(ProgressEntry.project_id == project_id)
                .order_by(ProgressEntry.timestamp.desc())
                .limit(limit)
                .all()
            )
            return self._detach_all(db, entries)

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
        with session_scope() as db:
            memory = DecisionMemory(
                project_id=project_id,
                feature_id=feature_id,
                decision_context=context,
                decision_made=decision,
                reasoning=reasoning,
                tags=tags or [],
            )
            db.add(memory)
            db.commit()
            db.refresh(memory)

            self._logger.info(f"Recorded decision: {decision[:50]}...")
            return self._detach(db, memory)

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
        with session_scope() as db:
            memory = (
                db.query(DecisionMemory)
                .filter(DecisionMemory.id == decision_id)
                .first()
            )
            if memory:
                memory.outcome = outcome
                memory.outcome_score = max(-1.0, min(1.0, score))
                memory.lesson_learned = lesson
                db.commit()

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
        with session_scope() as db:
            query = db.query(DecisionMemory).filter(
                DecisionMemory.project_id == project_id
            )

            # Note: Full-text tag search would require more complex query
            # For now, return recent decisions
            decisions = (
                query.order_by(DecisionMemory.timestamp.desc())
                .limit(limit)
                .all()
            )
            return self._detach_all(db, decisions)

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
