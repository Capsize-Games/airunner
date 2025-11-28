"""Unit tests for ProjectManager.

Tests project, feature, session, and progress management without
requiring an LLM.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from airunner.components.llm.long_running.project_manager import ProjectManager
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


class TestProjectManager:
    """Test suite for ProjectManager."""

    @pytest.fixture
    def manager(self):
        """Create a ProjectManager instance."""
        return ProjectManager()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for project files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    # =========================================================================
    # Project Tests
    # =========================================================================

    def test_create_project_basic(self, manager, temp_dir):
        """Test creating a basic project."""
        project = manager.create_project(
            name="Test Project",
            description="A test project",
            working_directory=temp_dir,
            init_git=False,  # Skip git for tests
        )

        assert project is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.status == ProjectStatus.INITIALIZING
        assert project.total_features == 0
        assert project.passing_features == 0

    def test_create_project_duplicate_name(self, manager, temp_dir):
        """Test that duplicate project names raise error."""
        manager.create_project(
            name="Unique Project",
            description="First project",
            working_directory=temp_dir,
            init_git=False,
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.create_project(
                name="Unique Project",
                description="Second project",
                init_git=False,
            )

    def test_get_project(self, manager, temp_dir):
        """Test retrieving a project by ID."""
        created = manager.create_project(
            name="Retrievable Project",
            description="Test",
            init_git=False,
        )

        retrieved = manager.get_project(created.id)
        assert retrieved is not None
        assert retrieved.name == "Retrievable Project"

    def test_get_project_by_name(self, manager, temp_dir):
        """Test retrieving a project by name."""
        manager.create_project(
            name="Named Project",
            description="Test",
            init_git=False,
        )

        retrieved = manager.get_project_by_name("Named Project")
        assert retrieved is not None
        assert retrieved.name == "Named Project"

    def test_update_project_status(self, manager, temp_dir):
        """Test updating project status."""
        project = manager.create_project(
            name="Status Test",
            description="Test",
            init_git=False,
        )

        manager.update_project_status(project.id, ProjectStatus.ACTIVE)
        updated = manager.get_project(project.id)
        assert updated.status == ProjectStatus.ACTIVE

    def test_delete_project(self, manager, temp_dir):
        """Test deleting a project."""
        project = manager.create_project(
            name="Deletable",
            description="Test",
            init_git=False,
        )

        result = manager.delete_project(project.id)
        assert result is True

        retrieved = manager.get_project(project.id)
        assert retrieved is None

    # =========================================================================
    # Feature Tests
    # =========================================================================

    def test_add_feature(self, manager, temp_dir):
        """Test adding a feature to a project."""
        project = manager.create_project(
            name="Feature Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Login feature",
            description="User can log in with username and password",
            category=FeatureCategory.FUNCTIONAL,
            priority=8,
            verification_steps=["Open login page", "Enter credentials", "Click login"],
        )

        assert feature is not None
        assert feature.name == "Login feature"
        assert feature.status == FeatureStatus.NOT_STARTED
        assert feature.priority == 8
        assert len(feature.verification_steps) == 3

        # Check project was updated
        updated_project = manager.get_project(project.id)
        assert updated_project.total_features == 1

    def test_add_features_bulk(self, manager, temp_dir):
        """Test adding multiple features at once."""
        project = manager.create_project(
            name="Bulk Feature Test",
            description="Test",
            init_git=False,
        )

        features_data = [
            {"name": "Feature 1", "description": "First feature"},
            {"name": "Feature 2", "description": "Second feature", "priority": 7},
            {"name": "Feature 3", "description": "Third feature", "category": "ui"},
        ]

        features = manager.add_features_bulk(project.id, features_data)
        assert len(features) == 3

        updated_project = manager.get_project(project.id)
        assert updated_project.total_features == 3

    def test_get_project_features(self, manager, temp_dir):
        """Test retrieving project features."""
        project = manager.create_project(
            name="Get Features Test",
            description="Test",
            init_git=False,
        )

        manager.add_feature(
            project_id=project.id,
            name="Feature A",
            description="Test A",
        )
        manager.add_feature(
            project_id=project.id,
            name="Feature B",
            description="Test B",
            category=FeatureCategory.UI,
        )

        all_features = manager.get_project_features(project.id)
        assert len(all_features) == 2

        ui_features = manager.get_project_features(
            project.id, category=FeatureCategory.UI
        )
        assert len(ui_features) == 1
        assert ui_features[0].name == "Feature B"

    def test_update_feature_status(self, manager, temp_dir):
        """Test updating feature status."""
        project = manager.create_project(
            name="Status Update Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Updatable Feature",
            description="Test",
        )

        # Update to in-progress
        manager.update_feature_status(feature.id, FeatureStatus.IN_PROGRESS)
        updated = manager.get_feature(feature.id)
        assert updated.status == FeatureStatus.IN_PROGRESS

        # Update to passing
        manager.update_feature_status(feature.id, FeatureStatus.PASSING)
        updated = manager.get_feature(feature.id)
        assert updated.status == FeatureStatus.PASSING

        # Check project passing count
        updated_project = manager.get_project(project.id)
        assert updated_project.passing_features == 1

    def test_update_feature_status_failing(self, manager, temp_dir):
        """Test updating feature to failing status."""
        project = manager.create_project(
            name="Failing Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Failing Feature",
            description="Test",
        )

        manager.update_feature_status(
            feature.id,
            FeatureStatus.FAILING,
            error="Test failed: assertion error",
        )

        updated = manager.get_feature(feature.id)
        assert updated.status == FeatureStatus.FAILING
        assert updated.attempts == 1
        assert "assertion error" in updated.last_error

    def test_get_next_feature_to_work_on(self, manager, temp_dir):
        """Test getting the next feature to work on."""
        project = manager.create_project(
            name="Next Feature Test",
            description="Test",
            init_git=False,
        )

        # Add features with different priorities
        f1 = manager.add_feature(
            project_id=project.id,
            name="Low Priority",
            description="Test",
            priority=3,
        )
        f2 = manager.add_feature(
            project_id=project.id,
            name="High Priority",
            description="Test",
            priority=9,
        )

        next_feature = manager.get_next_feature_to_work_on(project.id)
        assert next_feature is not None
        assert next_feature.name == "High Priority"

    def test_get_next_feature_with_dependencies(self, manager, temp_dir):
        """Test that features with unmet dependencies are skipped."""
        project = manager.create_project(
            name="Dependency Test",
            description="Test",
            init_git=False,
        )

        # Create base feature
        base = manager.add_feature(
            project_id=project.id,
            name="Base Feature",
            description="Foundation",
            priority=5,
        )

        # Create dependent feature with higher priority
        dependent = manager.add_feature(
            project_id=project.id,
            name="Dependent Feature",
            description="Depends on base",
            priority=10,
            depends_on=[base.id],
        )

        # Should get base feature (dependency not met for dependent)
        next_feature = manager.get_next_feature_to_work_on(project.id)
        assert next_feature.name == "Base Feature"

        # Mark base as passing
        manager.update_feature_status(base.id, FeatureStatus.PASSING)

        # Now should get dependent feature
        next_feature = manager.get_next_feature_to_work_on(project.id)
        assert next_feature.name == "Dependent Feature"

    # =========================================================================
    # Session Tests
    # =========================================================================

    def test_start_session(self, manager, temp_dir):
        """Test starting a session."""
        project = manager.create_project(
            name="Session Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Session Feature",
            description="Test",
        )

        session = manager.start_session(project.id, feature.id)
        assert session is not None
        assert session.project_id == project.id
        assert session.feature_id == feature.id
        assert session.started_at is not None

    def test_start_session_auto_select_feature(self, manager, temp_dir):
        """Test starting a session with automatic feature selection."""
        project = manager.create_project(
            name="Auto Select Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Auto Feature",
            description="Test",
        )

        session = manager.start_session(project.id)
        assert session is not None
        assert session.feature_id == feature.id

    def test_end_session(self, manager, temp_dir):
        """Test ending a session."""
        project = manager.create_project(
            name="End Session Test",
            description="Test",
            init_git=False,
        )

        session = manager.start_session(project.id)

        manager.end_session(
            session_id=session.id,
            working_memory={"last_action": "wrote code"},
            next_action="Run tests",
            tokens_consumed=1000,
        )

        # Note: Would need to query session again to verify
        # This test mainly ensures no exceptions

    def test_get_last_session(self, manager, temp_dir):
        """Test getting the most recent session."""
        project = manager.create_project(
            name="Last Session Test",
            description="Test",
            init_git=False,
        )

        session1 = manager.start_session(project.id)
        manager.end_session(session1.id)

        session2 = manager.start_session(project.id)

        last = manager.get_last_session(project.id)
        assert last is not None
        assert last.id == session2.id

    # =========================================================================
    # Progress Tests
    # =========================================================================

    def test_log_progress(self, manager, temp_dir):
        """Test logging progress."""
        project = manager.create_project(
            name="Progress Test",
            description="Test",
            init_git=False,
        )

        entry = manager.log_progress(
            project_id=project.id,
            action="Implemented login",
            outcome="Login works but needs password reset",
            files_changed=["auth.py", "login.html"],
            git_commit=False,
        )

        assert entry is not None
        assert entry.action == "Implemented login"
        assert "auth.py" in entry.files_changed

    def test_get_progress_log(self, manager, temp_dir):
        """Test retrieving progress log."""
        project = manager.create_project(
            name="Get Progress Test",
            description="Test",
            init_git=False,
        )

        for i in range(5):
            manager.log_progress(
                project_id=project.id,
                action=f"Action {i}",
                outcome=f"Outcome {i}",
            )

        entries = manager.get_progress_log(project.id, limit=3)
        assert len(entries) == 3

    def test_get_progress_as_text(self, manager, temp_dir):
        """Test getting progress as formatted text."""
        project = manager.create_project(
            name="Text Progress Test",
            description="Test",
            init_git=False,
        )

        manager.log_progress(
            project_id=project.id,
            action="Did something",
            outcome="It worked",
        )

        text = manager.get_progress_as_text(project.id)
        assert "Progress Log" in text
        assert "Did something" in text

    # =========================================================================
    # Decision Memory Tests
    # =========================================================================

    def test_record_decision(self, manager, temp_dir):
        """Test recording a decision."""
        project = manager.create_project(
            name="Decision Test",
            description="Test",
            init_git=False,
        )

        decision = manager.record_decision(
            project_id=project.id,
            context="Needed to choose a database",
            decision="Selected SQLite",
            reasoning="Simple, embedded, no server needed",
            tags=["architecture", "database"],
        )

        assert decision is not None
        assert decision.decision_made == "Selected SQLite"
        assert "architecture" in decision.tags

    def test_update_decision_outcome(self, manager, temp_dir):
        """Test updating decision outcome."""
        project = manager.create_project(
            name="Decision Outcome Test",
            description="Test",
            init_git=False,
        )

        decision = manager.record_decision(
            project_id=project.id,
            context="Test context",
            decision="Test decision",
            reasoning="Test reasoning",
        )

        manager.update_decision_outcome(
            decision_id=decision.id,
            outcome=DecisionOutcome.SUCCESS,
            score=0.9,
            lesson="SQLite works well for small projects",
        )

        # Would need to retrieve to verify

    def test_get_relevant_decisions(self, manager, temp_dir):
        """Test getting relevant decisions."""
        project = manager.create_project(
            name="Relevant Decisions Test",
            description="Test",
            init_git=False,
        )

        for i in range(5):
            manager.record_decision(
                project_id=project.id,
                context=f"Context {i}",
                decision=f"Decision {i}",
                reasoning=f"Reasoning {i}",
            )

        decisions = manager.get_relevant_decisions(project.id, limit=3)
        assert len(decisions) == 3


class TestProjectCompletion:
    """Test project completion scenarios."""

    @pytest.fixture
    def manager(self):
        """Create a ProjectManager instance."""
        return ProjectManager()

    def test_project_completes_when_all_features_pass(self, manager):
        """Test that project status updates to completed when all features pass."""
        project = manager.create_project(
            name="Completion Test",
            description="Test",
            init_git=False,
        )

        # Add a single feature
        feature = manager.add_feature(
            project_id=project.id,
            name="Only Feature",
            description="Test",
        )

        # Mark as passing
        manager.update_feature_status(feature.id, FeatureStatus.PASSING)

        # Check project status
        updated = manager.get_project(project.id)
        assert updated.status == ProjectStatus.COMPLETED

    def test_no_features_returns_none_for_next(self, manager):
        """Test that project with all passing features returns None for next."""
        project = manager.create_project(
            name="No Next Test",
            description="Test",
            init_git=False,
        )

        feature = manager.add_feature(
            project_id=project.id,
            name="Done Feature",
            description="Test",
        )

        manager.update_feature_status(feature.id, FeatureStatus.PASSING)

        next_feature = manager.get_next_feature_to_work_on(project.id)
        assert next_feature is None
