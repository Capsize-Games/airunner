"""Session Agent for incremental progress on long-running projects.

The Session Agent handles a single working session:
1. Reads project state, progress log, and git history
2. Selects ONE feature to work on
3. Implements/fixes the feature
4. Tests and verifies the feature
5. Commits changes and updates progress log
6. Leaves clean state for next session

Key improvements over Anthropic's approach:
- Decision memory: Recalls and learns from past outcomes
- Sub-agent delegation: Routes to specialized agents (code, research, test)
- Automatic state recovery: Handles interrupted sessions
- Resource-aware: Respects hardware constraints
"""

from typing import Any, Optional, List, Dict, Annotated, Callable
from typing_extensions import TypedDict
from enum import Enum
import json

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph, add_messages

from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    ProjectFeature,
    FeatureStatus,
    FeatureCategory,
    DecisionOutcome,
)
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class SessionPhase(str, Enum):
    """Current phase of the session."""

    ORIENTATION = "orientation"  # Reading state, logs, history
    PLANNING = "planning"  # Choosing what to work on
    IMPLEMENTATION = "implementation"  # Actually doing the work
    VERIFICATION = "verification"  # Testing the work
    CLEANUP = "cleanup"  # Committing, logging, handoff


# System prompt for the session agent
SESSION_SYSTEM_PROMPT = """You are an expert software engineer working on a long-running project. Your job is to make INCREMENTAL, FOCUSED progress.

CRITICAL RULES:
1. Work on EXACTLY ONE feature per session
2. NEVER declare the whole project complete - only individual features
3. ALWAYS test your work before marking a feature as passing
4. ALWAYS leave the codebase in a clean, working state
5. ALWAYS commit your changes with descriptive messages
6. If you encounter blockers, document them clearly for the next session
7. Learn from past decisions and their outcomes

SESSION WORKFLOW:
1. ORIENTATION
   - Review progress log
   - Check git history
   - Understand current state

2. PLANNING
   - Select ONE feature to work on (highest priority, dependencies met)
   - Review any past decisions related to this feature
   - Create implementation plan

3. IMPLEMENTATION
   - Make code changes
   - Use appropriate tools (file operations, code execution, etc.)
   - Keep changes focused and atomic

4. VERIFICATION
   - Run tests
   - Verify feature works end-to-end
   - Check for regressions

5. CLEANUP
   - Commit changes
   - Update progress log
   - Note recommendations for next session

AVAILABLE CONTEXT:
- Project progress log (what was done before)
- Feature list with status
- Git history
- Past decisions and their outcomes
- Working directory contents

OUTPUT FORMAT:
When responding, always include:
- PHASE: current phase
- ACTION: what you're doing
- OUTCOME: what happened
- NEXT: recommended next step

Example:
PHASE: implementation
ACTION: Created user authentication module
OUTCOME: Login/logout endpoints functional, tests passing
NEXT: Implement password reset feature"""


class SessionState(TypedDict):
    """State schema for Session Agent.

    Attributes:
        messages: Conversation messages
        project_id: Project being worked on
        session_id: Current session ID
        feature_id: Feature being worked on
        phase: Current session phase
        progress_context: Progress log content
        git_context: Git history content
        feature_context: Feature details
        decision_context: Relevant past decisions
        tools_output: Results from tool calls
        verification_result: Result of testing
        files_changed: Files modified this session
        error: Any error message
        should_continue: Whether to continue the loop
    """

    messages: Annotated[list[BaseMessage], add_messages]
    project_id: int
    session_id: Optional[int]
    feature_id: Optional[int]
    phase: SessionPhase
    progress_context: str
    git_context: str
    feature_context: str
    decision_context: str
    tools_output: Optional[str]
    verification_result: Optional[str]
    files_changed: List[str]
    error: Optional[str]
    should_continue: bool


class SessionAgent:
    """Agent that handles a single working session on a project.

    Makes incremental progress toward project completion by:
    1. Understanding current state
    2. Selecting appropriate work
    3. Implementing changes
    4. Verifying quality
    5. Committing and documenting

    Example:
        ```python
        agent = SessionAgent(chat_model, tools=[...])
        result = agent.run_session(
            project_id=1,
            max_iterations=10
        )
        print(f"Session result: {result['outcome']}")
        ```
    """

    def __init__(
        self,
        chat_model: Any,
        tools: Optional[List[Any]] = None,
        project_manager: Optional[ProjectManager] = None,
        sub_agents: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Session Agent.

        Args:
            chat_model: LangChain chat model
            tools: List of tools for the agent to use
            project_manager: ProjectManager instance
            sub_agents: Dict mapping category names to specialized agents
        """
        self._chat_model = chat_model
        self._tools = tools or []
        self._project_manager = project_manager or ProjectManager()
        self._sub_agents = sub_agents or {}

        # Bind tools to model if available
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info(f"Session agent bound {len(self._tools)} tools")

        self._graph = self._build_graph()
        logger.info("SessionAgent initialized")

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow for session execution."""
        workflow = StateGraph(SessionState)

        # Add nodes
        workflow.add_node("orientation", self._orientation_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("implementation", self._implementation_node)
        workflow.add_node("verification", self._verification_node)
        workflow.add_node("cleanup", self._cleanup_node)

        # Add edges with conditional routing
        workflow.add_edge(START, "orientation")
        workflow.add_edge("orientation", "planning")
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "implement": "implementation",
                "end": "cleanup",
            },
        )
        workflow.add_conditional_edges(
            "implementation",
            self._route_after_implementation,
            {
                "verify": "verification",
                "continue": "implementation",
                "end": "cleanup",
            },
        )
        workflow.add_conditional_edges(
            "verification",
            self._route_after_verification,
            {
                "fix": "implementation",
                "done": "cleanup",
            },
        )
        workflow.add_edge("cleanup", END)

        return workflow.compile()

    def _orientation_node(self, state: SessionState) -> dict:
        """Orient the agent to current project state.

        Reads progress log, git history, and feature list to understand
        what has been done and what needs to be done.

        Args:
            state: Current state

        Returns:
            Updated state with context
        """
        logger.info(f"Orientation phase for project {state['project_id']}")

        project_id = state["project_id"]

        # Get progress log
        progress_context = self._project_manager.get_progress_as_text(
            project_id, limit=10
        )

        # Get git history
        git_commits = self._project_manager.get_git_log(project_id, limit=10)
        git_context = "\n".join(
            f"- [{c['hash'][:7]}] {c['message']} ({c['date']})"
            for c in git_commits
        ) or "No git history yet"

        # Get feature list
        project = self._project_manager.get_project(project_id)
        features = self._project_manager.get_project_features(project_id)
        feature_context = self._format_feature_list(features)

        # Get relevant past decisions
        decisions = self._project_manager.get_relevant_decisions(
            project_id, limit=5
        )
        decision_context = "\n\n".join(
            d.to_context_string() for d in decisions
        ) or "No past decisions recorded"

        # Create orientation message
        orientation_msg = f"""# Project Orientation

## Project: {project.name if project else 'Unknown'}
{project.description if project else ''}

## Recent Progress:
{progress_context}

## Git History:
{git_context}

## Feature Status:
{feature_context}

## Past Decisions:
{decision_context}

---
Analyze this context and prepare to select the next feature to work on."""

        return {
            "phase": SessionPhase.PLANNING,
            "progress_context": progress_context,
            "git_context": git_context,
            "feature_context": feature_context,
            "decision_context": decision_context,
            "messages": [SystemMessage(content=SESSION_SYSTEM_PROMPT)],
        }

    def _planning_node(self, state: SessionState) -> dict:
        """Plan what feature to work on.

        Selects the highest-priority feature with met dependencies
        and creates an implementation plan.

        Args:
            state: Current state

        Returns:
            Updated state with feature selection
        """
        logger.info("Planning phase")

        # Get next feature to work on
        next_feature = self._project_manager.get_next_feature_to_work_on(
            state["project_id"]
        )

        if not next_feature:
            logger.info("No features left to work on - project may be complete")
            return {
                "phase": SessionPhase.CLEANUP,
                "feature_id": None,
                "should_continue": False,
                "messages": [
                    AIMessage(
                        content="PHASE: planning\nACTION: Checked feature list\n"
                        "OUTCOME: All features are passing!\n"
                        "NEXT: Project appears complete - verify and close"
                    )
                ],
            }

        # Start a session if not already started
        session_id = state.get("session_id")
        if not session_id:
            session = self._project_manager.start_session(
                project_id=state["project_id"],
                feature_id=next_feature.id,
            )
            session_id = session.id

        # Update feature status to in-progress
        self._project_manager.update_feature_status(
            next_feature.id, FeatureStatus.IN_PROGRESS
        )

        # Create planning prompt
        planning_prompt = f"""# Planning Phase

I will work on this feature:

**Feature:** {next_feature.name}
**Category:** {next_feature.category.value if next_feature.category else 'functional'}
**Priority:** {next_feature.priority}
**Description:** {next_feature.description}

**Verification Steps:**
{chr(10).join(f'- {step}' for step in (next_feature.verification_steps or []))}

**Previous Attempts:** {next_feature.attempts or 0}
{f"**Last Error:** {next_feature.last_error}" if next_feature.last_error else ""}

---

PHASE: planning
ACTION: Selected feature to work on
OUTCOME: Will implement "{next_feature.name}"
NEXT: Begin implementation"""

        return {
            "phase": SessionPhase.IMPLEMENTATION,
            "feature_id": next_feature.id,
            "session_id": session_id,
            "should_continue": True,
            "messages": [HumanMessage(content=planning_prompt)],
        }

    def _implementation_node(self, state: SessionState) -> dict:
        """Implement the selected feature.

        Uses tools to make code changes, create files, etc.
        May delegate to specialized sub-agents based on feature category.

        Args:
            state: Current state

        Returns:
            Updated state with implementation results
        """
        logger.info(f"Implementation phase for feature {state.get('feature_id')}")

        feature = self._project_manager.get_feature(state["feature_id"])
        if not feature:
            return {
                "error": f"Feature {state['feature_id']} not found",
                "should_continue": False,
            }

        # Check if we should delegate to a sub-agent
        if feature.category and feature.category.value in self._sub_agents:
            return self._delegate_to_sub_agent(state, feature)

        # Create implementation prompt
        impl_prompt = f"""# Implementation Phase

Working on: {feature.name}
Category: {feature.category.value if feature.category else 'functional'}

Description: {feature.description}

Use your tools to implement this feature. Focus on:
1. Writing clean, well-documented code
2. Following project conventions
3. Making atomic, focused changes
4. Testing as you go

Report your progress after each significant action."""

        # Get LLM response with tool use
        try:
            response = self._chat_model.invoke(
                state["messages"] + [HumanMessage(content=impl_prompt)]
            )

            # Track files changed (would come from tool outputs)
            files_changed = state.get("files_changed", [])

            # Check if implementation appears complete
            content = response.content.lower()
            implementation_complete = any(
                phrase in content
                for phrase in [
                    "implementation complete",
                    "feature implemented",
                    "ready for testing",
                    "ready to verify",
                ]
            )

            return {
                "messages": [response],
                "tools_output": response.content,
                "files_changed": files_changed,
                "phase": SessionPhase.VERIFICATION
                if implementation_complete
                else SessionPhase.IMPLEMENTATION,
                "should_continue": not implementation_complete,
            }

        except Exception as e:
            logger.error(f"Implementation error: {e}")
            return {"error": str(e), "should_continue": False}

    def _verification_node(self, state: SessionState) -> dict:
        """Verify the implemented feature.

        Runs tests and checks that the feature works as expected
        according to verification steps.

        Args:
            state: Current state

        Returns:
            Updated state with verification results
        """
        logger.info(f"Verification phase for feature {state.get('feature_id')}")

        feature = self._project_manager.get_feature(state["feature_id"])
        if not feature:
            return {"error": "Feature not found", "should_continue": False}

        # Create verification prompt
        verification_steps = feature.verification_steps or []
        steps_text = "\n".join(f"- [ ] {step}" for step in verification_steps)

        verify_prompt = f"""# Verification Phase

Feature: {feature.name}

Please verify this feature by completing these steps:
{steps_text}

For each step:
1. Execute the verification action
2. Check the result
3. Mark as passed or failed

If ALL steps pass, mark the feature as PASSING.
If ANY step fails, note what went wrong.

CRITICAL: Only mark as passing if you have ACTUALLY VERIFIED each step!"""

        try:
            response = self._chat_model.invoke(
                state["messages"] + [HumanMessage(content=verify_prompt)]
            )

            content = response.content.lower()

            # Determine if verification passed
            verification_passed = any(
                phrase in content
                for phrase in [
                    "all steps pass",
                    "verification passed",
                    "feature passing",
                    "all tests pass",
                ]
            )

            verification_failed = any(
                phrase in content
                for phrase in [
                    "verification failed",
                    "step failed",
                    "test failed",
                    "does not work",
                ]
            )

            return {
                "messages": [response],
                "verification_result": "passed" if verification_passed else "failed",
                "phase": SessionPhase.CLEANUP,
                "should_continue": not verification_passed and not verification_failed,
            }

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {"error": str(e), "should_continue": False}

    def _cleanup_node(self, state: SessionState) -> dict:
        """Clean up session and prepare for next.

        Commits changes, logs progress, updates feature status,
        and leaves recommendations for next session.

        Args:
            state: Current state

        Returns:
            Final state
        """
        logger.info("Cleanup phase")

        feature_id = state.get("feature_id")
        session_id = state.get("session_id")
        project_id = state["project_id"]
        verification_result = state.get("verification_result")
        files_changed = state.get("files_changed", [])

        # Update feature status
        if feature_id:
            if verification_result == "passed":
                self._project_manager.update_feature_status(
                    feature_id, FeatureStatus.PASSING
                )
                action = "Feature completed and verified"
                outcome = "All verification steps passed"
            else:
                self._project_manager.update_feature_status(
                    feature_id, FeatureStatus.FAILING
                )
                action = "Feature attempted but needs more work"
                outcome = state.get("verification_result", "Verification incomplete")

            # Log progress
            self._project_manager.log_progress(
                project_id=project_id,
                session_id=session_id,
                feature_id=feature_id,
                action=action,
                outcome=outcome,
                files_changed=files_changed,
                git_commit=True,
            )

        # End session
        if session_id:
            # Get recommendation for next session
            next_feature = self._project_manager.get_next_feature_to_work_on(
                project_id
            )
            next_action = (
                f"Work on: {next_feature.name}"
                if next_feature
                else "Project may be complete - review all features"
            )

            self._project_manager.end_session(
                session_id=session_id,
                working_memory={
                    "last_feature": feature_id,
                    "verification_result": verification_result,
                },
                next_action=next_action,
            )

        return {
            "phase": SessionPhase.CLEANUP,
            "should_continue": False,
        }

    def _delegate_to_sub_agent(
        self, state: SessionState, feature: ProjectFeature
    ) -> dict:
        """Delegate implementation to a specialized sub-agent.

        Args:
            state: Current state
            feature: Feature to implement

        Returns:
            Updated state from sub-agent
        """
        category = feature.category.value if feature.category else "functional"
        sub_agent = self._sub_agents.get(category)

        if not sub_agent:
            logger.warning(f"No sub-agent for category {category}, using main agent")
            return {}

        logger.info(f"Delegating to {category} sub-agent")

        # Create context for sub-agent
        sub_context = {
            "feature": feature.to_dict(),
            "project_context": state.get("progress_context", ""),
            "decision_context": state.get("decision_context", ""),
        }

        try:
            # Invoke sub-agent
            result = sub_agent.invoke(sub_context)

            # Record this delegation as a decision
            self._project_manager.record_decision(
                project_id=state["project_id"],
                context=f"Implementing feature: {feature.name}",
                decision=f"Delegated to {category} sub-agent",
                reasoning=f"Feature category is {category}",
                feature_id=feature.id,
                tags=["delegation", category],
            )

            return {
                "tools_output": str(result),
                "messages": [
                    AIMessage(
                        content=f"Sub-agent ({category}) result:\n{result}"
                    )
                ],
            }

        except Exception as e:
            logger.error(f"Sub-agent delegation failed: {e}")
            return {"error": f"Sub-agent failed: {e}"}

    def _route_after_planning(self, state: SessionState) -> str:
        """Route after planning phase.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        if not state.get("feature_id"):
            return "end"
        return "implement"

    def _route_after_implementation(self, state: SessionState) -> str:
        """Route after implementation phase.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        if state.get("error"):
            return "end"
        if state.get("should_continue"):
            return "continue"
        return "verify"

    def _route_after_verification(self, state: SessionState) -> str:
        """Route after verification phase.

        Args:
            state: Current state

        Returns:
            Next node name
        """
        if state.get("verification_result") == "passed":
            return "done"
        if state.get("should_continue"):
            return "fix"
        return "done"

    def _format_feature_list(self, features: List[ProjectFeature]) -> str:
        """Format feature list for context.

        Args:
            features: List of features

        Returns:
            Formatted string
        """
        if not features:
            return "No features defined yet"

        lines = []
        for f in features:
            status_emoji = {
                FeatureStatus.PASSING: "✅",
                FeatureStatus.FAILING: "❌",
                FeatureStatus.IN_PROGRESS: "🔄",
                FeatureStatus.NOT_STARTED: "⬜",
                FeatureStatus.BLOCKED: "🚫",
            }.get(f.status, "⬜")

            lines.append(
                f"{status_emoji} [{f.status.value if f.status else 'not_started'}] "
                f"{f.name} (priority: {f.priority})"
            )

        # Summary
        total = len(features)
        passing = sum(
            1 for f in features if f.status == FeatureStatus.PASSING
        )
        lines.insert(0, f"Total: {total} features, {passing} passing ({passing*100//total if total else 0}%)\n")

        return "\n".join(lines)

    def run_session(
        self,
        project_id: int,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Run a single working session on a project.

        Args:
            project_id: Project to work on
            max_iterations: Maximum LLM calls (safety limit)

        Returns:
            Dict with session results
        """
        logger.info(f"Starting session for project {project_id}")

        initial_state: SessionState = {
            "messages": [],
            "project_id": project_id,
            "session_id": None,
            "feature_id": None,
            "phase": SessionPhase.ORIENTATION,
            "progress_context": "",
            "git_context": "",
            "feature_context": "",
            "decision_context": "",
            "tools_output": None,
            "verification_result": None,
            "files_changed": [],
            "error": None,
            "should_continue": True,
        }

        # Run the graph
        result = self._graph.invoke(initial_state)

        # Get session summary
        session_id = result.get("session_id")
        feature_id = result.get("feature_id")

        return {
            "session_id": session_id,
            "feature_id": feature_id,
            "phase": result.get("phase", SessionPhase.CLEANUP).value,
            "verification_result": result.get("verification_result"),
            "files_changed": result.get("files_changed", []),
            "error": result.get("error"),
        }
