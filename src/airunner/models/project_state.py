"""Service-owned long-running project state models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from airunner.base import BaseModel


class ProjectStatus(str, Enum):
    """Status of a long-running project."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class FeatureStatus(str, Enum):
    """Status of a project feature."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FAILING = "failing"
    PASSING = "passing"
    BLOCKED = "blocked"


class FeatureCategory(str, Enum):
    """Category of feature for routing to specialized agents."""

    FUNCTIONAL = "functional"
    UI = "ui"
    INTEGRATION = "integration"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"


class DecisionOutcome(str, Enum):
    """Outcome of a past decision."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    REVERTED = "reverted"


class ProjectState(BaseModel):
    """Persistent state for a long-running agent project."""

    __tablename__ = "project_states"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    working_directory = Column(String(512))
    git_repo_path = Column(String(512))
    status = Column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.INITIALIZING,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    total_features = Column(Integer, default=0)
    passing_features = Column(Integer, default=0)
    current_feature_id = Column(Integer)
    system_prompt = Column(Text)
    project_metadata = Column(
        JSON,
        default=dict,
    )

    features = relationship(
        "ProjectFeature",
        back_populates="project",
        foreign_keys="ProjectFeature.project_id",
        cascade="all, delete-orphan",
    )
    progress_entries = relationship(
        "ProgressEntry",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "SessionState",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    decisions = relationship(
        "DecisionMemory",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def get_progress_summary(self) -> str:
        """Get a human-readable progress summary."""
        if self.total_features == 0:
            return "Project not yet initialized"
        pct = (self.passing_features / self.total_features) * 100
        return (
            f"{self.passing_features}/{self.total_features} features passing "
            f"({pct:.1f}%)"
        )

    def to_context_dict(self) -> dict:
        """Export key project info for agent context."""
        return {
            "project_name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "progress": self.get_progress_summary(),
            "working_directory": self.working_directory,
        }


class ProjectFeature(BaseModel):
    """A single feature in a long-running project."""

    __tablename__ = "project_features"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("project_states.id"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    verification_steps = Column(JSON, default=list)
    category = Column(
        SQLEnum(FeatureCategory),
        default=FeatureCategory.FUNCTIONAL,
    )
    status = Column(
        SQLEnum(FeatureStatus),
        default=FeatureStatus.NOT_STARTED,
    )
    priority = Column(Integer, default=5)
    depends_on = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    attempts = Column(Integer, default=0)
    last_error = Column(Text)

    project = relationship(
        "ProjectState",
        back_populates="features",
        foreign_keys=[project_id],
    )

    def can_work_on(self, project: "ProjectState") -> bool:
        """Check whether the feature's dependencies are satisfied."""
        if not self.depends_on:
            return True

        for dep_id in self.depends_on:
            for feature in project.features:
                if (
                    feature.id == dep_id
                    and feature.status != FeatureStatus.PASSING
                ):
                    return False
        return True

    def to_dict(self) -> dict:
        """Export the feature for agent context."""
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
    """Log entry for work done on a project."""

    __tablename__ = "progress_entries"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("project_states.id"),
        nullable=False,
        index=True,
    )
    session_id = Column(Integer, ForeignKey("session_states.id"), index=True)
    feature_id = Column(Integer, ForeignKey("project_features.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(Text, nullable=False)
    outcome = Column(Text)
    files_changed = Column(JSON, default=list)
    git_commit_hash = Column(String(64))
    tokens_used = Column(Integer, default=0)

    project = relationship("ProjectState", back_populates="progress_entries")
    session = relationship("SessionState", back_populates="progress_entries")

    def to_log_string(self) -> str:
        """Format the entry for human-readable logs."""
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        commit = (
            f" [{self.git_commit_hash[:7]}]"
            if self.git_commit_hash
            else ""
        )
        files = (
            f"\n  Files: {', '.join(self.files_changed)}"
            if self.files_changed
            else ""
        )
        return (
            f"[{timestamp}]{commit} {self.action}\n"
            f"  Outcome: {self.outcome}{files}"
        )


class SessionState(BaseModel):
    """State for a single agent session."""

    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("project_states.id"),
        nullable=False,
        index=True,
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

    project = relationship("ProjectState", back_populates="sessions")
    progress_entries = relationship(
        "ProgressEntry",
        back_populates="session",
    )

    def get_context_for_next_session(self) -> dict:
        """Get context to seed the next session."""
        return {
            "previous_session_id": self.id,
            "last_action": self.last_action,
            "recommended_next": self.next_recommended_action,
            "working_memory": self.working_memory or {},
            "error_to_fix": self.error_state,
        }


class DecisionMemory(BaseModel):
    """Memory of past decisions and their outcomes."""

    __tablename__ = "decision_memories"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("project_states.id"),
        nullable=False,
        index=True,
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

    project = relationship("ProjectState", back_populates="decisions")

    def to_context_string(self) -> str:
        """Format the decision for agent context."""
        outcome_str = self.outcome.value if self.outcome else "pending"
        return (
            f"Decision: {self.decision_made}\n"
            f"Context: {self.decision_context}\n"
            f"Outcome: {outcome_str} (score: {self.outcome_score:.2f})\n"
            f"Lesson: {self.lesson_learned or 'None recorded'}"
        )


__all__ = [
    "DecisionMemory",
    "DecisionOutcome",
    "FeatureCategory",
    "FeatureStatus",
    "ProgressEntry",
    "ProjectFeature",
    "ProjectState",
    "ProjectStatus",
    "SessionState",
]