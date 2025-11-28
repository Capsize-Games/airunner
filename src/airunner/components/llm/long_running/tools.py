"""LangChain tools for long-running project management.

These tools allow the LLM to interact with long-running projects
directly through the conversation interface.
"""

from typing import Optional, List

from airunner.components.llm.core.tool_registry import tool, ToolCategory


@tool(
    name="create_long_running_project",
    category=ToolCategory.PROJECT,
    description=(
        "Create a new long-running project with automatic feature decomposition. "
        "The system will analyze requirements and create a comprehensive feature list."
    ),
    requires_api=False,
)
def create_long_running_project(
    name: str,
    description: str,
    working_directory: Optional[str] = None,
) -> str:
    """Create a new long-running project.

    Args:
        name: Project name
        description: Detailed requirements/description
        working_directory: Optional directory for project files

    Returns:
        Success message with project ID and feature count
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )

    try:
        manager = ProjectManager()

        # Check if project exists
        existing = manager.get_project_by_name(name)
        if existing:
            return f"Project '{name}' already exists (ID: {existing.id})"

        project = manager.create_project(
            name=name,
            description=description,
            working_directory=working_directory,
        )

        return (
            f"Created project '{name}' (ID: {project.id})\n"
            f"Working directory: {working_directory or 'Not set'}\n"
            f"Status: Initializing\n\n"
            f"Use 'initialize_project_features' to generate the feature list."
        )

    except Exception as e:
        return f"Error creating project: {str(e)}"


@tool(
    name="initialize_project_features",
    category=ToolCategory.PROJECT,
    description=(
        "Initialize a project with a comprehensive feature list. "
        "Uses AI to analyze requirements and create atomic, testable features."
    ),
    requires_api=True,
)
def initialize_project_features(project_id: int) -> str:
    """Generate and add features to a project.

    Args:
        project_id: Project ID

    Returns:
        Success message with feature count
    """
    # Note: This would need to be called with the chat_model context
    # For now, return instructions
    return (
        f"To initialize features for project {project_id}, use the "
        "LongRunningHarness.create_project() method which handles "
        "both project creation and feature initialization.\n\n"
        "Example:\n"
        "```python\n"
        "harness = LongRunningHarness(chat_model)\n"
        "project_id = harness.create_project(\n"
        "    name='My Project',\n"
        "    description='Build a...',\n"
        ")\n"
        "```"
    )


@tool(
    name="get_project_status",
    category=ToolCategory.PROJECT,
    description=(
        "Get the current status and progress of a long-running project."
    ),
    requires_api=False,
)
def get_project_status(project_id: int) -> str:
    """Get project status and progress.

    Args:
        project_id: Project ID

    Returns:
        Project status summary
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureStatus,
    )

    try:
        manager = ProjectManager()
        project = manager.get_project(project_id)

        if not project:
            return f"Project {project_id} not found"

        features = manager.get_project_features(project_id)

        # Count by status
        status_counts = {}
        for feature in features:
            status = feature.status.value if feature.status else "not_started"
            status_counts[status] = status_counts.get(status, 0) + 1

        progress = manager.get_progress_as_text(project_id, limit=5)

        return (
            f"# Project: {project.name}\n"
            f"**Status:** {project.status.value if project.status else 'unknown'}\n"
            f"**Progress:** {project.get_progress_summary()}\n\n"
            f"## Feature Breakdown:\n"
            + "\n".join(f"- {k}: {v}" for k, v in status_counts.items())
            + f"\n\n## Recent Progress:\n{progress}"
        )

    except Exception as e:
        return f"Error getting status: {str(e)}"


@tool(
    name="list_project_features",
    category=ToolCategory.PROJECT,
    description=(
        "List all features in a project with their status."
    ),
    requires_api=False,
)
def list_project_features(
    project_id: int,
    status_filter: Optional[str] = None,
) -> str:
    """List features in a project.

    Args:
        project_id: Project ID
        status_filter: Optional filter (passing, failing, in_progress, not_started)

    Returns:
        Feature list
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureStatus,
    )

    try:
        manager = ProjectManager()

        status = None
        if status_filter:
            try:
                status = FeatureStatus(status_filter)
            except ValueError:
                pass

        features = manager.get_project_features(project_id, status=status)

        if not features:
            return "No features found"

        status_emoji = {
            "passing": "✅",
            "failing": "❌",
            "in_progress": "🔄",
            "not_started": "⬜",
            "blocked": "🚫",
        }

        lines = [f"# Features ({len(features)} total)\n"]
        for f in features:
            status_val = f.status.value if f.status else "not_started"
            emoji = status_emoji.get(status_val, "⬜")
            lines.append(
                f"{emoji} **{f.name}** [{status_val}]\n"
                f"   Priority: {f.priority} | Category: "
                f"{f.category.value if f.category else 'functional'}\n"
                f"   {f.description[:100]}{'...' if len(f.description or '') > 100 else ''}"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing features: {str(e)}"


@tool(
    name="get_project_progress_log",
    category=ToolCategory.PROJECT,
    description=(
        "Get the progress log for a project showing what has been done."
    ),
    requires_api=False,
)
def get_project_progress_log(
    project_id: int,
    limit: int = 20,
) -> str:
    """Get project progress log.

    Args:
        project_id: Project ID
        limit: Maximum entries to return

    Returns:
        Progress log text
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )

    try:
        manager = ProjectManager()
        return manager.get_progress_as_text(project_id, limit=limit)

    except Exception as e:
        return f"Error getting progress: {str(e)}"


@tool(
    name="list_long_running_projects",
    category=ToolCategory.PROJECT,
    description=(
        "List all long-running projects."
    ),
    requires_api=False,
)
def list_long_running_projects(
    status_filter: Optional[str] = None,
) -> str:
    """List all projects.

    Args:
        status_filter: Optional filter (active, completed, paused, abandoned)

    Returns:
        List of projects
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )
    from airunner.components.llm.long_running.data.project_state import (
        ProjectStatus,
    )

    try:
        manager = ProjectManager()

        status = None
        if status_filter:
            try:
                status = ProjectStatus(status_filter)
            except ValueError:
                pass

        projects = manager.list_projects(status=status)

        if not projects:
            return "No projects found"

        lines = ["# Long-Running Projects\n"]
        for p in projects:
            lines.append(
                f"**{p.name}** (ID: {p.id})\n"
                f"   Status: {p.status.value if p.status else 'unknown'}\n"
                f"   Progress: {p.get_progress_summary()}\n"
                f"   Updated: {p.updated_at}\n"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing projects: {str(e)}"


@tool(
    name="add_project_feature",
    category=ToolCategory.PROJECT,
    description=(
        "Manually add a feature to a project."
    ),
    requires_api=False,
)
def add_project_feature(
    project_id: int,
    name: str,
    description: str,
    category: str = "functional",
    priority: int = 5,
    verification_steps: Optional[List[str]] = None,
) -> str:
    """Add a feature to a project.

    Args:
        project_id: Project ID
        name: Feature name
        description: Feature description
        category: functional, ui, integration, testing, documentation, performance, security
        priority: 1-10 (higher = more important)
        verification_steps: List of steps to verify feature

    Returns:
        Success message
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureCategory,
    )

    try:
        manager = ProjectManager()

        # Validate category
        try:
            cat = FeatureCategory(category)
        except ValueError:
            cat = FeatureCategory.FUNCTIONAL

        feature = manager.add_feature(
            project_id=project_id,
            name=name,
            description=description,
            category=cat,
            priority=priority,
            verification_steps=verification_steps or [],
        )

        return (
            f"Added feature '{name}' (ID: {feature.id})\n"
            f"Category: {cat.value}\n"
            f"Priority: {priority}\n"
            f"Verification steps: {len(verification_steps or [])}"
        )

    except Exception as e:
        return f"Error adding feature: {str(e)}"


@tool(
    name="update_feature_status",
    category=ToolCategory.PROJECT,
    description=(
        "Update the status of a project feature. "
        "IMPORTANT: Only mark as 'passing' after actual verification!"
    ),
    requires_api=False,
)
def update_feature_status(
    feature_id: int,
    status: str,
    error: Optional[str] = None,
) -> str:
    """Update feature status.

    Args:
        feature_id: Feature ID
        status: passing, failing, in_progress, not_started, blocked
        error: Optional error message (for failing status)

    Returns:
        Confirmation message
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureStatus,
    )

    try:
        manager = ProjectManager()

        # Validate status
        try:
            feat_status = FeatureStatus(status)
        except ValueError:
            return f"Invalid status: {status}. Use: passing, failing, in_progress, not_started, blocked"

        manager.update_feature_status(feature_id, feat_status, error)

        return f"Feature {feature_id} status updated to: {status}"

    except Exception as e:
        return f"Error updating status: {str(e)}"


@tool(
    name="log_project_progress",
    category=ToolCategory.PROJECT,
    description=(
        "Log progress on a project. Creates a record of work done."
    ),
    requires_api=False,
)
def log_project_progress(
    project_id: int,
    action: str,
    outcome: str,
    files_changed: Optional[List[str]] = None,
    git_commit: bool = False,
) -> str:
    """Log progress on a project.

    Args:
        project_id: Project ID
        action: What was done
        outcome: What happened
        files_changed: List of files modified
        git_commit: Whether to create a git commit

    Returns:
        Confirmation message
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )

    try:
        manager = ProjectManager()

        entry = manager.log_progress(
            project_id=project_id,
            action=action,
            outcome=outcome,
            files_changed=files_changed or [],
            git_commit=git_commit,
        )

        commit_msg = ""
        if entry.git_commit_hash:
            commit_msg = f"\nGit commit: {entry.git_commit_hash[:7]}"

        return f"Progress logged at {entry.timestamp}{commit_msg}"

    except Exception as e:
        return f"Error logging progress: {str(e)}"


@tool(
    name="get_next_feature_to_work_on",
    category=ToolCategory.PROJECT,
    description=(
        "Get the next feature that should be worked on in a project. "
        "Returns the highest priority feature with met dependencies."
    ),
    requires_api=False,
)
def get_next_feature_to_work_on(project_id: int) -> str:
    """Get next feature to work on.

    Args:
        project_id: Project ID

    Returns:
        Feature details or message if none available
    """
    from airunner.components.llm.long_running.project_manager import (
        ProjectManager,
    )

    try:
        manager = ProjectManager()
        feature = manager.get_next_feature_to_work_on(project_id)

        if not feature:
            return "No features to work on - project may be complete!"

        steps = "\n".join(
            f"- {step}" for step in (feature.verification_steps or [])
        )

        return (
            f"# Next Feature: {feature.name}\n\n"
            f"**ID:** {feature.id}\n"
            f"**Priority:** {feature.priority}\n"
            f"**Category:** {feature.category.value if feature.category else 'functional'}\n"
            f"**Attempts:** {feature.attempts or 0}\n\n"
            f"## Description\n{feature.description}\n\n"
            f"## Verification Steps\n{steps or 'None specified'}\n\n"
            + (f"## Last Error\n{feature.last_error}" if feature.last_error else "")
        )

    except Exception as e:
        return f"Error: {str(e)}"


# Export list of tools
LONG_RUNNING_TOOLS = [
    create_long_running_project,
    initialize_project_features,
    get_project_status,
    list_project_features,
    get_project_progress_log,
    list_long_running_projects,
    add_project_feature,
    update_feature_status,
    log_project_progress,
    get_next_feature_to_work_on,
]
