"""Data models for long-running agent projects.

This module defines SQLAlchemy models for persisting:
- Project state and configuration
- Feature lists with pass/fail status
- Progress entries (log of work done)
- Session state for continuity
- Decision memory for learning from outcomes

Design inspired by Anthropic's harness but extended with:
- Decision memory: Track past decisions and outcomes
- Sub-task delegation: Support for specialized sub-agents
- Richer metadata: Context for recovery
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
import json

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Float,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from airunner.components.data.models.base import BaseModel


class ProjectStatus(str, Enum):
    """Status of a long-running project."""

    INITIALIZING = "initializing"  # Being set up by initializer agent
    ACTIVE = "active"  # Ready for work
    PAUSED = "paused"  # User paused
    COMPLETED = "completed"  # All features passing
    ABANDONED = "abandoned"  # User cancelled


class FeatureStatus(str, Enum):
    """Status of a project feature."""

    NOT_STARTED = "not_started"  # Not yet attempted
    IN_PROGRESS = "in_progress"  # Currently being worked on
    FAILING = "failing"  # Attempted but not passing
    PASSING = "passing"  # Tests/verification passed
    BLOCKED = "blocked"  # Depends on failing feature


class FeatureCategory(str, Enum):
    """Category of feature for routing to specialized agents."""

    FUNCTIONAL = "functional"  # Core functionality
    UI = "ui"  # User interface
    INTEGRATION = "integration"  # External integrations
    TESTING = "testing"  # Test coverage
    DOCUMENTATION = "documentation"  # Docs
    PERFORMANCE = "performance"  # Optimization
    SECURITY = "security"  # Security features


class DecisionOutcome(str, Enum):
    """Outcome of a past decision."""

    SUCCESS = "success"  # Decision led to good outcome
    PARTIAL = "partial"  # Mixed results
    FAILURE = "failure"  # Decision led to problems
    REVERTED = "reverted"  # Had to undo the decision


class ProjectState(BaseModel):
    """Persistent state for a long-running agent project.

    This is the main entry point for tracking multi-session projects.
    It holds configuration, current status, and references to related data.

    Attributes:
        id: Primary key
        name: Human-readable project name
        description: What the project aims to achieve
        working_directory: Filesystem path for project files
        git_repo_path: Path to git repository (for versioning)
        status: Current project status
        created_at: When project was created
        updated_at: Last modification time
        total_features: Total number of features
        passing_features: Number of passing features
        current_feature_id: Feature currently being worked on
        system_prompt: Base system prompt for agents
        metadata: JSON field for extensible metadata
    """

    __tablename__ = "project_states"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    working_directory = Column(String(512))
    git_repo_path = Column(String(512))
    status = Column(
        SQLEnum(ProjectStatus), default=ProjectStatus.INITIALIZING
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    total_features = Column(Integer, default=0)
    passing_features = Column(Integer, default=0)
    current_feature_id = Column(Integer)  # No FK to avoid circular dependency
    system_prompt = Column(Text)
    project_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' (reserved by SQLAlchemy)

    # Relationships
    features = relationship(
        "ProjectFeature",
        back_populates="project",
        foreign_keys="ProjectFeature.project_id",
        cascade="all, delete-orphan",
    )
    progress_entries = relationship(
        "ProgressEntry", back_populates="project", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "SessionState", back_populates="project", cascade="all, delete-orphan"
    )
    decisions = relationship(
        "DecisionMemory", back_populates="project", cascade="all, delete-orphan"
    )

    def get_progress_summary(self) -> str:
        """Get human-readable progress summary."""
        if self.total_features == 0:
            return "Project not yet initialized"
        pct = (self.passing_features / self.total_features) * 100
        return (
            f"{self.passing_features}/{self.total_features} features passing "
            f"({pct:.1f}%)"
        )

    def to_context_dict(self) -> dict:
        """Export key info for agent context."""
        return {
            "project_name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "progress": self.get_progress_summary(),
            "working_directory": self.working_directory,
        }


class ProjectFeature(BaseModel):
    """A single feature in a long-running project.

    Features are the atomic units of work. Each session should work on
    exactly one feature to maintain focus and clean commits.

    Attributes:
        id: Primary key
        project_id: Parent project
        name: Short feature name
        description: Detailed description
        verification_steps: JSON list of steps to verify feature works
        category: Feature category for agent routing
        status: Current feature status
        priority: 1-10 priority (higher = more important)
        depends_on: JSON list of feature IDs this depends on
        created_at: When feature was added
        updated_at: Last modification
        attempts: Number of attempts to implement
        last_error: Last error encountered
    """

    __tablename__ = "project_features"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project_states.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    verification_steps = Column(JSON, default=list)
    category = Column(SQLEnum(FeatureCategory), default=FeatureCategory.FUNCTIONAL)
    status = Column(SQLEnum(FeatureStatus), default=FeatureStatus.NOT_STARTED)
    priority = Column(Integer, default=5)
    depends_on = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    attempts = Column(Integer, default=0)
    last_error = Column(Text)

    # Relationships
    project = relationship(
        "ProjectState", back_populates="features", foreign_keys=[project_id]
    )

    def can_work_on(self, project: "ProjectState") -> bool:
        """Check if this feature can be worked on (dependencies met)."""
        if not self.depends_on:
            return True

        for dep_id in self.depends_on:
            dep_feature = (
                project.features
                if hasattr(project, "_features_cache")
                else None
            )
            # Check if dependency is passing
            for f in project.features:
                if f.id == dep_id and f.status != FeatureStatus.PASSING:
                    return False
        return True

    def to_dict(self) -> dict:
        """Export feature for agent context."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "status": self.status.value if self.status else None,
            "priority": self.priority,
            "verification_steps": self.verification_steps or [],
            "attempts": self.attempts,
            "last_error": self.last_error,
        }


class ProgressEntry(BaseModel):
    """Log entry for work done on a project.

    This is the "claude-progress.txt" equivalent - a human-readable
    record of all agent sessions and their outcomes.

    Attributes:
        id: Primary key
        project_id: Parent project
        session_id: Which session made this entry
        feature_id: Which feature was worked on
        timestamp: When entry was made
        action: What was done
        outcome: What happened
        files_changed: JSON list of files modified
        git_commit_hash: Commit hash if committed
        tokens_used: Token consumption for this work
    """

    __tablename__ = "progress_entries"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project_states.id"), nullable=False, index=True
    )
    session_id = Column(Integer, ForeignKey("session_states.id"), index=True)
    feature_id = Column(Integer, ForeignKey("project_features.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(Text, nullable=False)
    outcome = Column(Text)
    files_changed = Column(JSON, default=list)
    git_commit_hash = Column(String(64))
    tokens_used = Column(Integer, default=0)

    # Relationships
    project = relationship("ProjectState", back_populates="progress_entries")
    session = relationship("SessionState", back_populates="progress_entries")

    def to_log_string(self) -> str:
        """Format entry for human-readable log."""
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        commit = f" [{self.git_commit_hash[:7]}]" if self.git_commit_hash else ""
        files = (
            f"\n  Files: {', '.join(self.files_changed)}"
            if self.files_changed
            else ""
        )
        return f"[{ts}]{commit} {self.action}\n  Outcome: {self.outcome}{files}"


class SessionState(BaseModel):
    """State for a single agent session.

    Tracks everything about one working session so the next session
    can pick up exactly where this one left off.

    Attributes:
        id: Primary key
        project_id: Parent project
        started_at: When session began
        ended_at: When session ended
        feature_id: Feature being worked on
        context_snapshot: JSON snapshot of relevant context
        working_memory: JSON of short-term working memory
        last_action: Last action taken
        next_recommended_action: What the agent recommends doing next
        error_state: Any error that caused session to end
        tokens_consumed: Total tokens used in session
    """

    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project_states.id"), nullable=False, index=True
    )
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    feature_id = Column(Integer, ForeignKey("project_features.id"))
    context_snapshot = Column(JSON, default=dict)
    working_memory = Column(JSON, default=dict)
    last_action = Column(Text)
    next_recommended_action = Column(Text)
    error_state = Column(Text)
    tokens_consumed = Column(Integer, default=0)

    # Relationships
    project = relationship("ProjectState", back_populates="sessions")
    progress_entries = relationship(
        "ProgressEntry", back_populates="session"
    )

    def get_context_for_next_session(self) -> dict:
        """Get context dict for initializing next session."""
        return {
            "previous_session_id": self.id,
            "last_action": self.last_action,
            "recommended_next": self.next_recommended_action,
            "working_memory": self.working_memory or {},
            "error_to_fix": self.error_state,
        }


class DecisionMemory(BaseModel):
    """Memory of past decisions and their outcomes.

    This extends Anthropic's approach by tracking what worked
    and what didn't, allowing the agent to learn from experience.

    Attributes:
        id: Primary key
        project_id: Parent project
        feature_id: Related feature (if any)
        timestamp: When decision was made
        decision_context: What situation prompted the decision
        decision_made: What was decided
        reasoning: Why this decision was made
        outcome: What happened
        outcome_score: -1.0 to 1.0 success score
        lesson_learned: What can be learned from this
        tags: JSON list of tags for retrieval
    """

    __tablename__ = "decision_memories"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project_states.id"), nullable=False, index=True
    )
    feature_id = Column(Integer, ForeignKey("project_features.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    decision_context = Column(Text, nullable=False)
    decision_made = Column(Text, nullable=False)
    reasoning = Column(Text)
    outcome = Column(SQLEnum(DecisionOutcome))
    outcome_score = Column(Float, default=0.0)
    lesson_learned = Column(Text)
    tags = Column(JSON, default=list)

    # Relationships
    project = relationship("ProjectState", back_populates="decisions")

    def to_context_string(self) -> str:
        """Format for agent context."""
        outcome_str = self.outcome.value if self.outcome else "pending"
        return (
            f"Decision: {self.decision_made}\n"
            f"Context: {self.decision_context}\n"
            f"Outcome: {outcome_str} (score: {self.outcome_score:.2f})\n"
            f"Lesson: {self.lesson_learned or 'None recorded'}"
        )
