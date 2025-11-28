"""Long-Running Agent Harness - Main orchestrator.

The LongRunningHarness is the primary interface for running multi-session
projects. It manages the lifecycle of projects from initialization through
completion.

Key responsibilities:
1. Project lifecycle management
2. Session orchestration
3. Sub-agent coordination
4. State recovery and resumption
5. Progress monitoring

This builds on Anthropic's approach with several enhancements:
- Decision memory for learning from outcomes
- Specialized sub-agents for different task types
- Sophisticated state recovery
- Resource-aware execution
"""

from typing import Any, Optional, List, Dict, Callable
from pathlib import Path
import json

from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    ProjectFeature,
    ProjectStatus,
    FeatureStatus,
    FeatureCategory,
    DecisionOutcome,
)
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.components.llm.long_running.initializer_agent import (
    InitializerAgent,
)
from airunner.components.llm.long_running.session_agent import SessionAgent
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LongRunningHarness:
    """Main orchestrator for long-running agent projects.

    The harness manages multi-session projects following Anthropic's
    two-phase approach (initializer + session agents) with extensions
    for decision memory, sub-agent delegation, and state recovery.

    Example:
        ```python
        harness = LongRunningHarness(
            chat_model=my_llm,
            tools=my_tools,
        )

        # Start a new project
        project_id = harness.create_project(
            name="My Chat App",
            description="Build a real-time chat application with rooms and DMs",
            working_directory="/home/user/projects/chat-app"
        )

        # Run sessions until complete (or hit max)
        result = harness.run_until_complete(
            project_id,
            max_sessions=50
        )

        # Or run one session at a time
        session_result = harness.run_session(project_id)
        ```

    Attributes:
        chat_model: LangChain chat model for agents
        tools: List of tools available to agents
        project_manager: Manages project persistence
        initializer: InitializerAgent instance
        session_agent: SessionAgent instance
        sub_agents: Dict of specialized sub-agents by category
    """

    def __init__(
        self,
        chat_model: Any,
        tools: Optional[List[Any]] = None,
        project_manager: Optional[ProjectManager] = None,
        sub_agents: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ):
        """Initialize the harness.

        Args:
            chat_model: LangChain chat model
            tools: List of tools for agents
            project_manager: Optional custom ProjectManager
            sub_agents: Optional dict of specialized sub-agents
            on_progress: Optional callback for progress updates
        """
        self._chat_model = chat_model
        self._tools = tools or []
        self._project_manager = project_manager or ProjectManager()
        self._sub_agents = sub_agents or {}
        self._on_progress = on_progress

        # Create agents
        self._initializer = InitializerAgent(
            chat_model=self._chat_model,
            project_manager=self._project_manager,
        )
        self._session_agent = SessionAgent(
            chat_model=self._chat_model,
            tools=self._tools,
            project_manager=self._project_manager,
            sub_agents=self._sub_agents,
        )

        logger.info("LongRunningHarness initialized")

    def register_sub_agent(
        self,
        category: str,
        agent: Any,
    ) -> None:
        """Register a specialized sub-agent for a feature category.

        Sub-agents handle specific types of work:
        - "code": Code writing, debugging, testing
        - "research": Information gathering, synthesis
        - "documentation": Writing docs, comments
        - "testing": Test creation, validation

        Args:
            category: Feature category this agent handles
            agent: Agent instance with invoke() method
        """
        self._sub_agents[category] = agent
        # Update session agent with new sub-agents
        self._session_agent = SessionAgent(
            chat_model=self._chat_model,
            tools=self._tools,
            project_manager=self._project_manager,
            sub_agents=self._sub_agents,
        )
        logger.info(f"Registered sub-agent for category: {category}")

    def create_project(
        self,
        name: str,
        description: str,
        working_directory: Optional[str] = None,
    ) -> int:
        """Create and initialize a new project.

        Uses the InitializerAgent to:
        1. Analyze requirements
        2. Generate comprehensive feature list
        3. Set up project directory
        4. Initialize git repository
        5. Create initial progress log

        Args:
            name: Project name
            description: Detailed requirements/description
            working_directory: Optional directory for project files

        Returns:
            Project ID

        Raises:
            ValueError: If initialization fails
        """
        logger.info(f"Creating project: {name}")

        result = self._initializer.initialize_project(
            name=name,
            description=description,
            working_directory=working_directory,
        )

        if result.get("error"):
            raise ValueError(f"Project initialization failed: {result['error']}")

        project_id = result["project_id"]
        feature_count = result["feature_count"]

        logger.info(
            f"Project {project_id} created with {feature_count} features"
        )

        if self._on_progress:
            self._on_progress(
                {
                    "event": "project_created",
                    "project_id": project_id,
                    "feature_count": feature_count,
                }
            )

        return project_id

    def run_session(
        self,
        project_id: int,
        feature_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a single working session on a project.

        Each session:
        1. Reviews current state
        2. Selects ONE feature to work on
        3. Implements/fixes the feature
        4. Tests and verifies
        5. Commits and logs progress

        Args:
            project_id: Project to work on
            feature_id: Optional specific feature to work on

        Returns:
            Session result dict with:
            - session_id: ID of the session
            - feature_id: Feature that was worked on
            - verification_result: "passed" or "failed"
            - files_changed: List of modified files
            - error: Any error that occurred
        """
        logger.info(f"Running session for project {project_id}")

        # Check project status
        project = self._project_manager.get_project(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        if project.status == ProjectStatus.COMPLETED:
            return {
                "message": "Project already completed",
                "status": "completed",
            }

        if project.status == ProjectStatus.ABANDONED:
            return {
                "error": "Project has been abandoned",
                "status": "abandoned",
            }

        # Run the session
        result = self._session_agent.run_session(project_id)

        if self._on_progress:
            self._on_progress(
                {
                    "event": "session_complete",
                    "project_id": project_id,
                    **result,
                }
            )

        return result

    def run_until_complete(
        self,
        project_id: int,
        max_sessions: int = 100,
        pause_between_sessions: bool = False,
    ) -> Dict[str, Any]:
        """Run sessions until project is complete or limit reached.

        This is the "autonomous mode" - the harness will continue
        running sessions until all features pass or the session
        limit is reached.

        Args:
            project_id: Project to work on
            max_sessions: Maximum sessions to run (safety limit)
            pause_between_sessions: If True, require confirmation
                between sessions

        Returns:
            Final result dict with:
            - status: "completed", "incomplete", or "error"
            - sessions_run: Number of sessions executed
            - features_passing: Number of passing features
            - total_features: Total feature count
            - error: Any final error
        """
        logger.info(
            f"Running until complete: project {project_id}, max {max_sessions}"
        )

        sessions_run = 0
        errors = []

        for i in range(max_sessions):
            # Check if project is complete
            project = self._project_manager.get_project(project_id)
            if not project:
                return {
                    "status": "error",
                    "error": "Project not found",
                    "sessions_run": sessions_run,
                }

            if project.status == ProjectStatus.COMPLETED:
                logger.info(
                    f"Project completed after {sessions_run} sessions"
                )
                return {
                    "status": "completed",
                    "sessions_run": sessions_run,
                    "features_passing": project.passing_features,
                    "total_features": project.total_features,
                }

            # Run session
            sessions_run += 1
            logger.info(f"Starting session {sessions_run}/{max_sessions}")

            if self._on_progress:
                self._on_progress(
                    {
                        "event": "session_starting",
                        "session_number": sessions_run,
                        "max_sessions": max_sessions,
                        "project_id": project_id,
                    }
                )

            result = self.run_session(project_id)

            if result.get("error"):
                errors.append(result["error"])
                logger.warning(f"Session error: {result['error']}")

            # Check for repeated failures
            if len(errors) >= 5:
                consecutive_errors = errors[-5:]
                if len(set(consecutive_errors)) == 1:
                    logger.error("Same error 5 times in a row, stopping")
                    return {
                        "status": "error",
                        "error": f"Repeated error: {errors[-1]}",
                        "sessions_run": sessions_run,
                        "features_passing": project.passing_features,
                        "total_features": project.total_features,
                    }

            if pause_between_sessions:
                # In a real implementation, this would wait for user input
                logger.info("Session complete. Waiting for next session...")

        # Hit max sessions
        project = self._project_manager.get_project(project_id)
        return {
            "status": "incomplete",
            "message": f"Reached max sessions ({max_sessions})",
            "sessions_run": sessions_run,
            "features_passing": project.passing_features if project else 0,
            "total_features": project.total_features if project else 0,
        }

    def resume_project(self, project_id: int) -> Dict[str, Any]:
        """Resume work on a paused or interrupted project.

        Recovers state from the last session and continues work.

        Args:
            project_id: Project to resume

        Returns:
            Dict with recovery info and first session result
        """
        logger.info(f"Resuming project {project_id}")

        project = self._project_manager.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        # Get last session for context
        last_session = self._project_manager.get_last_session(project_id)
        recovery_info = None
        if last_session:
            recovery_info = last_session.get_context_for_next_session()
            logger.info(f"Recovered context from session {last_session.id}")

        # Update status if paused
        if project.status == ProjectStatus.PAUSED:
            self._project_manager.update_project_status(
                project_id, ProjectStatus.ACTIVE
            )

        # Run a session
        result = self.run_session(project_id)
        result["recovery_info"] = recovery_info

        return result

    def get_project_status(self, project_id: int) -> Dict[str, Any]:
        """Get current project status and progress.

        Args:
            project_id: Project ID

        Returns:
            Dict with status, progress, and feature breakdown
        """
        project = self._project_manager.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        features = self._project_manager.get_project_features(project_id)

        # Count by status
        status_counts = {}
        for feature in features:
            status = feature.status.value if feature.status else "not_started"
            status_counts[status] = status_counts.get(status, 0) + 1

        # Recent progress
        progress_log = self._project_manager.get_progress_log(project_id, 5)

        return {
            "project_id": project_id,
            "name": project.name,
            "status": project.status.value if project.status else "unknown",
            "total_features": project.total_features,
            "passing_features": project.passing_features,
            "progress_percent": (
                (project.passing_features / project.total_features * 100)
                if project.total_features
                else 0
            ),
            "feature_breakdown": status_counts,
            "recent_progress": [
                {
                    "timestamp": str(entry.timestamp),
                    "action": entry.action,
                    "outcome": entry.outcome,
                }
                for entry in progress_log
            ],
        }

    def pause_project(self, project_id: int) -> bool:
        """Pause a project.

        Args:
            project_id: Project to pause

        Returns:
            True if paused successfully
        """
        self._project_manager.update_project_status(
            project_id, ProjectStatus.PAUSED
        )
        logger.info(f"Paused project {project_id}")
        return True

    def abandon_project(self, project_id: int, reason: str = "") -> bool:
        """Abandon a project.

        Args:
            project_id: Project to abandon
            reason: Optional reason for abandonment

        Returns:
            True if abandoned successfully
        """
        self._project_manager.update_project_status(
            project_id, ProjectStatus.ABANDONED
        )
        self._project_manager.log_progress(
            project_id=project_id,
            action="Project abandoned",
            outcome=reason or "User requested abandonment",
        )
        logger.info(f"Abandoned project {project_id}: {reason}")
        return True

    def revert_to_checkpoint(
        self, project_id: int, commit_hash: str
    ) -> bool:
        """Revert project to a specific git commit.

        Useful for recovering from bad changes or failed experiments.

        Args:
            project_id: Project ID
            commit_hash: Git commit to revert to

        Returns:
            True if successful
        """
        success = self._project_manager.git_revert_to_commit(
            project_id, commit_hash
        )
        if success:
            self._project_manager.log_progress(
                project_id=project_id,
                action=f"Reverted to commit {commit_hash[:7]}",
                outcome="Recovered previous state",
            )
        return success

    def get_decision_history(
        self, project_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get decision history for learning insights.

        Args:
            project_id: Project ID
            limit: Maximum decisions to return

        Returns:
            List of decision dicts with outcomes
        """
        decisions = self._project_manager.get_relevant_decisions(
            project_id, limit=limit
        )
        return [
            {
                "id": d.id,
                "timestamp": str(d.timestamp),
                "context": d.decision_context,
                "decision": d.decision_made,
                "reasoning": d.reasoning,
                "outcome": d.outcome.value if d.outcome else None,
                "score": d.outcome_score,
                "lesson": d.lesson_learned,
            }
            for d in decisions
        ]

    def add_decision_feedback(
        self,
        decision_id: int,
        outcome: str,
        score: float,
        lesson: Optional[str] = None,
    ) -> None:
        """Add feedback for a past decision.

        This allows humans to provide feedback on agent decisions,
        helping improve future performance.

        Args:
            decision_id: Decision ID
            outcome: "success", "partial", "failure", or "reverted"
            score: -1.0 to 1.0 success score
            lesson: What can be learned
        """
        outcome_enum = DecisionOutcome(outcome)
        self._project_manager.update_decision_outcome(
            decision_id=decision_id,
            outcome=outcome_enum,
            score=score,
            lesson=lesson,
        )
        logger.info(f"Added feedback for decision {decision_id}: {outcome}")

    def export_project_report(self, project_id: int) -> str:
        """Export a comprehensive project report.

        Args:
            project_id: Project ID

        Returns:
            Markdown-formatted report
        """
        project = self._project_manager.get_project(project_id)
        if not project:
            return "# Error: Project not found"

        features = self._project_manager.get_project_features(project_id)
        progress_log = self._project_manager.get_progress_log(project_id, 50)
        git_log = self._project_manager.get_git_log(project_id, 20)
        decisions = self._project_manager.get_relevant_decisions(
            project_id, limit=20
        )

        lines = [
            f"# Project Report: {project.name}",
            "",
            f"**Status:** {project.status.value if project.status else 'unknown'}",
            f"**Created:** {project.created_at}",
            f"**Last Updated:** {project.updated_at}",
            "",
            "## Description",
            project.description or "No description",
            "",
            f"## Progress: {project.get_progress_summary()}",
            "",
            "### Feature Status",
        ]

        # Features by status
        for status in FeatureStatus:
            status_features = [
                f for f in features if f.status == status
            ]
            if status_features:
                lines.append(f"\n#### {status.value.upper()}")
                for f in status_features:
                    lines.append(f"- {f.name}")

        lines.extend(
            [
                "",
                "## Progress Log",
                "",
            ]
        )
        for entry in progress_log:
            lines.append(entry.to_log_string())

        lines.extend(
            [
                "",
                "## Git History",
                "",
            ]
        )
        for commit in git_log:
            lines.append(
                f"- [{commit['hash'][:7]}] {commit['message']}"
            )

        lines.extend(
            [
                "",
                "## Decision History",
                "",
            ]
        )
        for d in decisions:
            outcome = d.outcome.value if d.outcome else "pending"
            lines.append(
                f"- **{d.decision_made}** ({outcome})\n"
                f"  Context: {d.decision_context[:100]}...\n"
                f"  Lesson: {d.lesson_learned or 'None'}"
            )

        return "\n".join(lines)
