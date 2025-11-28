"""Unit tests for the LongRunningHarness.

Tests the harness orchestration without requiring a real LLM.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, Any

from airunner.components.llm.long_running.harness import LongRunningHarness
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.components.llm.long_running.data.project_state import (
    ProjectStatus,
    FeatureStatus,
)


class MockChatModel:
    """Mock LLM for testing."""

    def __init__(self, responses: list = None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    def invoke(self, messages):
        """Return next response or default."""
        response = MagicMock()
        if self.call_count < len(self.responses):
            response.content = self.responses[self.call_count]
        else:
            response.content = "Default response"
        self.call_count += 1
        return response

    def bind_tools(self, tools):
        """Return self (tools bound)."""
        return self


class TestLongRunningHarness:
    """Test suite for LongRunningHarness."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock chat model."""
        return MockChatModel()

    @pytest.fixture
    def manager(self):
        """Create a real project manager for state verification."""
        return ProjectManager()

    @pytest.fixture
    def harness(self, mock_model, manager):
        """Create a harness with mock model."""
        return LongRunningHarness(
            chat_model=mock_model,
            project_manager=manager,
        )

    def test_harness_initialization(self, harness):
        """Test harness initializes correctly."""
        assert harness is not None
        assert harness._chat_model is not None
        assert harness._project_manager is not None
        assert harness._initializer is not None
        assert harness._session_agent is not None

    def test_register_sub_agent(self, harness):
        """Test registering a sub-agent."""
        mock_sub_agent = MagicMock()
        harness.register_sub_agent("code", mock_sub_agent)
        assert "code" in harness._sub_agents

    def test_get_project_status_not_found(self, harness):
        """Test getting status of non-existent project."""
        result = harness.get_project_status(99999)
        assert "error" in result

    def test_get_project_status(self, harness, manager):
        """Test getting project status."""
        # Create a project directly
        project = manager.create_project(
            name="Status Test Project",
            description="Test",
            init_git=False,
        )
        manager.add_feature(
            project_id=project.id,
            name="Test Feature",
            description="Test",
        )
        manager.update_project_status(project.id, ProjectStatus.ACTIVE)

        result = harness.get_project_status(project.id)
        assert result["name"] == "Status Test Project"
        assert result["total_features"] == 1
        assert "feature_breakdown" in result

    def test_pause_project(self, harness, manager):
        """Test pausing a project."""
        project = manager.create_project(
            name="Pause Test",
            description="Test",
            init_git=False,
        )

        result = harness.pause_project(project.id)
        assert result is True

        updated = manager.get_project(project.id)
        assert updated.status == ProjectStatus.PAUSED

    def test_abandon_project(self, harness, manager):
        """Test abandoning a project."""
        project = manager.create_project(
            name="Abandon Test",
            description="Test",
            init_git=False,
        )

        result = harness.abandon_project(project.id, "Testing abandonment")
        assert result is True

        updated = manager.get_project(project.id)
        assert updated.status == ProjectStatus.ABANDONED

    def test_get_decision_history(self, harness, manager):
        """Test getting decision history."""
        project = manager.create_project(
            name="Decision History Test",
            description="Test",
            init_git=False,
        )

        manager.record_decision(
            project_id=project.id,
            context="Test context",
            decision="Test decision",
            reasoning="Test reasoning",
        )

        decisions = harness.get_decision_history(project.id)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "Test decision"

    def test_export_project_report(self, harness, manager):
        """Test exporting project report."""
        project = manager.create_project(
            name="Report Test",
            description="A test project for reports",
            init_git=False,
        )

        manager.add_feature(
            project_id=project.id,
            name="Report Feature",
            description="Test",
        )

        report = harness.export_project_report(project.id)
        assert "Report Test" in report
        assert "Report Feature" in report

    def test_export_project_report_not_found(self, harness):
        """Test export for non-existent project."""
        report = harness.export_project_report(99999)
        assert "Error" in report

    def test_run_session_completed_project(self, harness, manager):
        """Test that running session on completed project returns message."""
        project = manager.create_project(
            name="Completed Session Test",
            description="Test",
            init_git=False,
        )
        manager.update_project_status(project.id, ProjectStatus.COMPLETED)

        result = harness.run_session(project.id)
        assert "completed" in str(result).lower()

    def test_run_session_abandoned_project(self, harness, manager):
        """Test that running session on abandoned project returns error."""
        project = manager.create_project(
            name="Abandoned Session Test",
            description="Test",
            init_git=False,
        )
        manager.update_project_status(project.id, ProjectStatus.ABANDONED)

        result = harness.run_session(project.id)
        assert "abandoned" in str(result).lower()

    def test_run_session_not_found(self, harness):
        """Test that running session on non-existent project returns error."""
        result = harness.run_session(99999)
        assert "error" in result


class TestProgressCallback:
    """Test progress callback functionality."""

    def test_on_progress_callback(self):
        """Test that progress callback is called."""
        mock_model = MockChatModel()
        manager = ProjectManager()
        progress_events = []

        def on_progress(event: Dict[str, Any]):
            progress_events.append(event)

        harness = LongRunningHarness(
            chat_model=mock_model,
            project_manager=manager,
            on_progress=on_progress,
        )

        # Create a project manually and verify callback would be called
        project = manager.create_project(
            name="Callback Test",
            description="Test",
            init_git=False,
        )

        # The harness.create_project would trigger callbacks
        # but we're testing the infrastructure exists


class TestSubAgentIntegration:
    """Test sub-agent integration with harness."""

    def test_sub_agents_passed_to_session_agent(self):
        """Test that sub-agents are passed to session agent."""
        mock_model = MockChatModel()
        mock_code_agent = MagicMock()

        harness = LongRunningHarness(
            chat_model=mock_model,
            sub_agents={"code": mock_code_agent},
        )

        assert "code" in harness._sub_agents


class TestResumeProject:
    """Test project resumption scenarios."""

    @pytest.fixture
    def harness_with_model(self):
        """Create harness with mock model."""
        mock_model = MockChatModel()
        manager = ProjectManager()
        return LongRunningHarness(
            chat_model=mock_model,
            project_manager=manager,
        )

    def test_resume_paused_project(self, harness_with_model):
        """Test resuming a paused project."""
        manager = harness_with_model._project_manager

        project = manager.create_project(
            name="Resume Test",
            description="Test",
            init_git=False,
        )
        manager.update_project_status(project.id, ProjectStatus.PAUSED)

        # Start a session to have something to resume from
        session = manager.start_session(project.id)
        manager.end_session(
            session.id,
            next_action="Continue from here",
        )

        result = harness_with_model.resume_project(project.id)

        # Project should be active again
        updated = manager.get_project(project.id)
        assert updated.status == ProjectStatus.ACTIVE

    def test_resume_with_recovery_info(self, harness_with_model):
        """Test that resume includes recovery info from last session."""
        manager = harness_with_model._project_manager

        project = manager.create_project(
            name="Recovery Info Test",
            description="Test",
            init_git=False,
        )

        # Create a session with working memory
        session = manager.start_session(project.id)
        manager.end_session(
            session.id,
            working_memory={"important_data": "test_value"},
            next_action="Next thing to do",
        )

        result = harness_with_model.resume_project(project.id)
        # Recovery info should be present
        assert "recovery_info" in result


class TestRunUntilComplete:
    """Test the autonomous run_until_complete functionality."""

    def test_max_sessions_limit(self):
        """Test that max_sessions limit is respected."""
        mock_model = MockChatModel()
        manager = ProjectManager()

        harness = LongRunningHarness(
            chat_model=mock_model,
            project_manager=manager,
        )

        project = manager.create_project(
            name="Max Sessions Test",
            description="Test",
            init_git=False,
        )
        manager.add_feature(
            project_id=project.id,
            name="Never Passing Feature",
            description="This feature never passes",
        )
        manager.update_project_status(project.id, ProjectStatus.ACTIVE)

        # Mock the session agent to avoid LLM invocation
        # Return a result that doesn't complete the feature
        harness._session_agent.run_session = MagicMock(
            return_value={
                "verification_result": "failed",
                "files_changed": [],
                "error": None,
            }
        )

        # Run with very low max_sessions
        result = harness.run_until_complete(project.id, max_sessions=2)

        assert result["status"] == "incomplete"
        assert result["sessions_run"] == 2

    def test_stops_when_completed(self):
        """Test that execution stops when project is completed."""
        mock_model = MockChatModel()
        manager = ProjectManager()

        harness = LongRunningHarness(
            chat_model=mock_model,
            project_manager=manager,
        )

        project = manager.create_project(
            name="Complete Test",
            description="Test",
            init_git=False,
        )
        # Project with no features is considered complete
        manager.update_project_status(project.id, ProjectStatus.COMPLETED)

        result = harness.run_until_complete(project.id, max_sessions=100)

        assert result["status"] == "completed"
        assert result["sessions_run"] == 0
