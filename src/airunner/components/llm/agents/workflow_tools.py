"""Workflow management tools for structured agent execution.

These tools allow the LLM to:
1. Select and initialize predefined workflows
2. Create dynamic workflows at runtime
3. Manage phase transitions
4. Track and update TODO items
5. Store and retrieve artifacts

The tools integrate with WorkflowState to provide the LLM with
explicit control over its execution flow.
"""

import json
from typing import Any, Dict, List, Optional

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.agents.workflow_state import (
    Phase,
    TodoStatus,
    WorkflowState,
    WorkflowType,
    create_dynamic_workflow,
    get_workflow,
)


# Global workflow state - in practice, this would be passed through LangGraph state
_current_workflow_state: Optional[WorkflowState] = None


def get_current_state() -> WorkflowState:
    """Get or create the current workflow state."""
    global _current_workflow_state
    if _current_workflow_state is None:
        _current_workflow_state = WorkflowState()
    return _current_workflow_state


def set_current_state(state: WorkflowState) -> None:
    """Set the current workflow state."""
    global _current_workflow_state
    _current_workflow_state = state


def reset_workflow_state() -> None:
    """Reset the workflow state."""
    global _current_workflow_state
    _current_workflow_state = None


def is_workflow_active() -> bool:
    """Check if a coding workflow is currently active.
        """
    global _current_workflow_state
    if _current_workflow_state is None:
        return False
    return _current_workflow_state.workflow_type in (
        WorkflowType.CODING,
        WorkflowType.RESEARCH,
        WorkflowType.WRITING,
        WorkflowType.DYNAMIC,
    )


def require_workflow(tool_name: str) -> str:
    """Placeholder for backward compatibility.
    
    Previously this checked if a workflow was active before allowing tools.
    Now it allows all tools to proceed - the model is guided by instructions
    but not blocked from using tools.
    
    Args:
        tool_name: Name of the tool being called
    
    Returns:
        Empty string (always allows the tool to proceed)
    """
    return ""  # No longer enforce workflow requirements


def require_execution_phase(tool_name: str) -> str:
    """Check if we're in a valid state for code creation.
    
    Previously this was strict about requiring EXECUTION phase with an active TODO.
    Now it's relaxed to allow the model more freedom - the workflow instructions
    guide behavior but don't block tool usage.
    
    Args:
        tool_name: Name of the tool being called
    
    Returns:
        Empty string (always allows the tool to proceed)
    """
    # No longer enforce strict workflow requirements
    # The model is guided by instructions but not blocked
    return ""


@tool(
    name="start_workflow",
    category=ToolCategory.WORKFLOW,
    description=(
        "Start a predefined workflow for complex multi-step tasks. "
        "Use 'coding' for TDD development, 'research' for comprehensive research, "
        "'writing' for documents, 'math' for problem solving, 'simple' for no workflow."
    ),
    keywords=["workflow", "start", "begin", "coding", "research", "writing", "math"],
    input_examples=[
        {"workflow_type": "coding", "task_description": "Write a Python hello world function"},
        {"workflow_type": "research", "task_description": "Research best practices for API design"},
    ],
)
def start_workflow(
    workflow_type: str,
    task_description: str,
) -> str:
    """Start a predefined workflow for a complex task.
    
    Use this at the beginning of complex tasks that benefit from
    structured execution. Available workflow types:
    - "coding": For code development with TDD (discovery → planning → execution → review)
    - "research": For comprehensive research (gather → analyze → synthesize → write)
    - "writing": For creative/technical writing
    - "math": For mathematical problem solving
    - "simple": For tasks that don't need structured workflow
    
    Args:
        workflow_type: One of "coding", "research", "writing", "math", "simple"
        task_description: Brief description of what you're trying to accomplish
            """
    state = get_current_state()
    
    # CRITICAL: Check if a workflow is already active
    # If so, return instructions to continue rather than restart
    if state.workflow_type is not None and state.workflow_type != WorkflowType.SIMPLE:
        current_phase = state.current_phase.value if state.current_phase else "unknown"
        return f"""⚠️ WORKFLOW ALREADY ACTIVE - DO NOT RESTART!

You already started a {state.workflow_type.value} workflow.
Current phase: {current_phase}

DO NOT call start_workflow again! Instead, continue with the next step:

If in DISCOVERY phase → call: transition_phase('planning', 'Moving to planning')
If in PLANNING phase  → call: add_todo_item('title', 'description')
If in EXECUTION phase → call: start_todo_item('todo_id') then use code tools
If in REVIEW phase    → call: transition_phase('complete', 'All done')

Original task: {state.artifacts.get('task_description', task_description)}

YOUR NEXT ACTION: Continue the workflow from the {current_phase} phase."""
    
    try:
        wf_type = WorkflowType(workflow_type)
    except ValueError:
        return f"Unknown workflow type '{workflow_type}'. Use: coding, research, writing, math, or simple"
    
    if wf_type == WorkflowType.SIMPLE:
        state.workflow_type = WorkflowType.SIMPLE
        return "Simple mode - no structured workflow. Proceed with the task directly."
    
    workflow_def = get_workflow(wf_type)
    if not workflow_def:
        return f"Workflow '{workflow_type}' not found in registry."
    
    state.workflow_type = wf_type
    state.workflow_definition = workflow_def
    state.current_phase = workflow_def.initial_phase
    state.phase_step = 0
    state.artifacts["task_description"] = task_description
    
    # Return detailed workflow instructions based on type
    if wf_type == WorkflowType.CODING:
        return f"""✓ CODING WORKFLOW STARTED
Task: {task_description}

════════════════════════════════════════════════════════════════════════════════
YOU ARE NOW IN: DISCOVERY PHASE
════════════════════════════════════════════════════════════════════════════════

**IMMEDIATE NEXT ACTION (do this NOW):**
Since this is a simple task, you can skip discovery and go straight to planning.

Call this tool NOW:
  transition_phase('planning', 'Task is simple, moving to planning')

════════════════════════════════════════════════════════════════════════════════
WORKFLOW OVERVIEW (for reference)
════════════════════════════════════════════════════════════════════════════════

Phase 1: DISCOVERY → transition_phase('planning', 'reason')
Phase 2: PLANNING  → add_todo_item() then transition_phase('execution', 'reason')  
Phase 3: EXECUTION → start_todo_item() → create_code_file() → validate_code() → complete_todo_item()
Phase 4: REVIEW    → transition_phase('complete', 'All done')

**RULES:**
- You CANNOT call create_code_file until you are in EXECUTION phase
- You CANNOT be in EXECUTION phase until you have TODO items
- You CANNOT work on a TODO until you call start_todo_item()
- ALWAYS call validate_code after create_code_file to check for syntax errors
- If validate_code shows errors, fix them with edit_code_file before completing

════════════════════════════════════════════════════════════════════════════════
YOUR NEXT TOOL CALL: transition_phase('planning', 'Task is simple')
════════════════════════════════════════════════════════════════════════════════"""
    
    # Default workflow info for other types
    phase_def = workflow_def.get_phase(state.current_phase)
    phase_info = ""
    if phase_def:
        phase_info = f"""
Current Phase: {phase_def.name.value.upper()}
Description: {phase_def.description}
Required Steps: {', '.join(phase_def.required_steps)}
Available Tools: {', '.join(phase_def.allowed_tools) if phase_def.allowed_tools else 'all tools'}
"""
    
    return f"""Workflow '{workflow_def.name}' started.
{phase_info}
Task: {task_description}

Begin with the {state.current_phase.value} phase. Use 'get_workflow_status' to check progress."""


@tool(
    name="create_custom_workflow",
    category=ToolCategory.WORKFLOW,
    description=(
        "Create a custom workflow when predefined ones don't fit. "
        "Define phases with required steps and allowed tools."
    ),
    defer_loading=True,  # Rarely needed, discoverable via search_tools
    keywords=["workflow", "custom", "create", "dynamic", "phases"],
)
def create_custom_workflow(
    name: str,
    description: str,
    phases_json: str,
) -> str:
    """Create a custom workflow for tasks that don't fit predefined patterns.
    
    Use this when you need a specialized workflow. Define phases with their
    required steps and allowed tools.
    
    Args:
        name: Name for this workflow
        description: What this workflow accomplishes
        phases_json: JSON array of phase definitions with keys phase_name,
            phase_description, required_steps (list), and allowed_tools (list).
    """
    state = get_current_state()
    
    try:
        phases = json.loads(phases_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON for phases: {e}"
    
    try:
        workflow_def = create_dynamic_workflow(name, description, phases)
        state.workflow_type = WorkflowType.DYNAMIC
        state.workflow_definition = workflow_def
        state.current_phase = workflow_def.initial_phase
        state.phase_step = 0
        
        return f"""Custom workflow '{name}' created and started.
Phases: {' → '.join(p.name.value for p in workflow_def.phases)}
Current Phase: {state.current_phase.value}

Begin with the first phase."""
    except Exception as e:
        return f"Failed to create workflow: {e}"


@tool(
    name="get_workflow_status",
    category=ToolCategory.WORKFLOW,
    description="Get current workflow status including phase, TODOs, and progress.",
    keywords=["workflow", "status", "progress", "phase", "todo"],
)
def get_workflow_status() -> str:
    """Get the current workflow status including phase, TODOs, and progress.
    
    Call this to understand where you are in the workflow and what to do next.
        """
    state = get_current_state()
    
    if state.workflow_type == WorkflowType.SIMPLE:
        return "No structured workflow active. Working in simple mode."
    
    # Phase info
    phase_info = f"Phase: {state.current_phase.value.upper()}"
    if state.workflow_definition:
        phase_def = state.workflow_definition.get_phase(state.current_phase)
        if phase_def:
            phase_info += f"\nDescription: {phase_def.description}"
            phase_info += f"\nRequired Steps: {', '.join(phase_def.required_steps)}"
    
    # TODO summary
    total = len(state.todo_list)
    completed = sum(1 for t in state.todo_list if t.status == TodoStatus.COMPLETED)
    in_progress = sum(1 for t in state.todo_list if t.status == TodoStatus.IN_PROGRESS)
    
    todo_summary = f"\nTODOs: {completed}/{total} complete"
    if in_progress:
        todo_summary += f", {in_progress} in progress"
    
    # Current TODO
    current_todo = state.get_current_todo()
    if current_todo:
        todo_summary += f"\nCurrently working on: [{current_todo.id}] {current_todo.title}"
    
    # Next TODO
    next_todo = state.get_next_todo()
    if next_todo and next_todo.id != (current_todo.id if current_todo else None):
        todo_summary += f"\nNext up: [{next_todo.id}] {next_todo.title}"
    
    # Artifacts
    artifact_summary = ""
    if state.artifacts:
        artifact_keys = list(state.artifacts.keys())
        artifact_summary = f"\nArtifacts collected: {', '.join(artifact_keys)}"
    
    # Iterations
    iteration_info = f"\nIterations: {state.iterations}/{state.max_iterations}"
    
    return f"""{phase_info}
{todo_summary}
{artifact_summary}
{iteration_info}"""


@tool(
    name="transition_phase",
    category=ToolCategory.WORKFLOW,
    description=(
        "Transition to a new workflow phase. "
        "Valid phases: discovery, planning, execution, review, complete."
    ),
    keywords=["workflow", "phase", "transition", "next", "move"],
    input_examples=[
        {"phase": "planning", "reason": "Task is simple, moving to planning"},
        {"phase": "execution", "reason": "TODO items created, ready to implement"},
        {"phase": "review", "reason": "All TODOs complete, ready to review"},
        {"phase": "complete", "reason": "Review done, task complete"},
    ],
)
def transition_phase(
    phase: str,
    reason: str,
) -> str:
    """Transition to a new workflow phase.
    
    Use this when you've completed the current phase and are ready to move on.
    Valid phases: discovery, planning, execution, review, complete
    
    Args:
        phase: The phase to transition to
        reason: Why you're making this transition
    """
    state = get_current_state()
    
    try:
        new_phase = Phase(phase)
    except ValueError:
        return f"Invalid phase '{phase}'. Use: discovery, planning, execution, review, complete"
    
    old_phase = state.current_phase
    state.transition_phase(new_phase)
    state.artifacts[f"phase_transition_{len(state.phase_history)}"] = {
        "from": old_phase.value,
        "to": new_phase.value,
        "reason": reason,
    }
    
    # Get new phase info and next action
    phase_info = ""
    next_action = ""
    if state.workflow_definition:
        phase_def = state.workflow_definition.get_phase(new_phase)
        if phase_def:
            phase_info = f"""
New Phase: {phase_def.name.value.upper()}
Description: {phase_def.description}
Required Steps: {', '.join(phase_def.required_steps)}
"""
    
    # Provide explicit next action guidance
    if new_phase.value == "planning":
        next_action = """
NEXT ACTION: Call add_todo_item(title='...', description='...') to create your task list.
Example: add_todo_item(title='Create hello_world function', description='Write a Python function that prints Hello World')"""
    elif new_phase.value == "execution":
        # List available todos
        todo_list = ", ".join([f"{t.id}" for t in state.todo_list if t.status != TodoStatus.COMPLETED])
        next_action = f"""
NEXT ACTION: Call start_todo_item(todo_id='todo_1') to begin working on a task.
Available TODO IDs: {todo_list if todo_list else 'none'}"""
    
    return f"""Phase transition: {old_phase.value} → {new_phase.value}
Reason: {reason}
{phase_info}{next_action}"""


@tool(
    name="add_todo_item",
    category=ToolCategory.WORKFLOW,
    description="Add a TODO item to the workflow task list with optional dependencies.",
    keywords=["todo", "task", "add", "create", "plan"],
    input_examples=[
        {"title": "Write unit test", "description": "Create test_hello.py with test for hello_world function"},
        {"title": "Implement function", "description": "Create hello.py with hello_world() function", "dependencies": "todo_1"},
    ],
)
def add_todo_item(
    title: str,
    description: str,
    dependencies: Any = "",
) -> str:
    """Add a TODO item to the workflow task list.
    
    Use this during the planning phase to break down work into manageable tasks.
    TODOs can have dependencies on other TODOs.
    
    Args:
        title: Short title for the TODO (3-7 words)
        description: Detailed description of what needs to be done
        dependencies: Comma-separated TODO IDs that must complete first,
            e.g. "todo_1" or "todo_1,todo_2". Leave empty string "" if no dependencies.
    """
    state = get_current_state()
    
    # Handle case where model passes list instead of string
    if isinstance(dependencies, list):
        dependencies = ",".join(str(d) for d in dependencies if d)
    
    dep_list = []
    if dependencies:
        dep_list = [d.strip() for d in dependencies.split(",") if d.strip()]
    
    todo = state.add_todo(title, description, dependencies=dep_list)
    
    return f"""TODO added: [{todo.id}] {title}
Phase: {todo.phase.value if todo.phase else 'none'}
Dependencies: {', '.join(dep_list) if dep_list else 'none'}

NEXT STEP: Before you can use create_code_file, you must:
1. Call: transition_phase('execution', 'Ready to implement')
2. Then call: start_todo_item(todo_id='{todo.id}')

Do NOT call create_code_file until you have done both steps above."""


@tool(
    name="start_todo_item",
    category=ToolCategory.WORKFLOW,
    description="Start working on a TODO item. Only one can be in progress at a time.",
    keywords=["todo", "start", "begin", "work"],
    input_examples=[
        {"todo_id": "todo_1"},
        {"todo_id": "todo_2"},
    ],
)
def start_todo_item(todo_id: str) -> str:
    """Start working on a TODO item.
    
    Call this before beginning work on a TODO. Only one TODO can be
    in progress at a time.
    
    Args:
        todo_id: The ID of the TODO to start (e.g., "todo_1")
            """
    state = get_current_state()
    
    # Find the TODO
    todo = None
    for t in state.todo_list:
        if t.id == todo_id:
            todo = t
            break
    
    if not todo:
        return f"TODO '{todo_id}' not found."
    
    if todo.status == TodoStatus.COMPLETED:
        return f"TODO '{todo_id}' is already completed."
    
    # Check dependencies
    unmet_deps = []
    for dep_id in todo.dependencies:
        for t in state.todo_list:
            if t.id == dep_id and t.status != TodoStatus.COMPLETED:
                unmet_deps.append(dep_id)
    
    if unmet_deps:
        return f"Cannot start '{todo_id}' - waiting on dependencies: {', '.join(unmet_deps)}"
    
    # Mark current TODO as no longer in progress if different
    if state.current_todo_id and state.current_todo_id != todo_id:
        for t in state.todo_list:
            if t.id == state.current_todo_id:
                t.status = TodoStatus.NOT_STARTED
                break
    
    todo.status = TodoStatus.IN_PROGRESS
    state.current_todo_id = todo_id
    
    return f"""Started: [{todo.id}] {todo.title}

Description: {todo.description}

Complete the work, then call 'complete_todo_item' with any artifacts."""


@tool(
    name="complete_todo_item",
    category=ToolCategory.WORKFLOW,
    description="Mark a TODO item as complete with summary and optional artifacts.",
    keywords=["todo", "complete", "done", "finish"],
    input_examples=[
        {"todo_id": "todo_1", "summary": "Created test_hello.py with unit test"},
        {"todo_id": "todo_2", "summary": "Implemented hello_world function", "artifacts_json": "{\"file\": \"hello.py\"}"},
    ],
)
def complete_todo_item(
    todo_id: str,
    summary: str,
    artifacts_json: Optional[str] = None,
) -> str:
    """Mark a TODO item as complete.
    
    Call this after finishing the work for a TODO. Include a summary
    and any artifacts (code written, files created, etc.).
    
    Args:
        todo_id: The ID of the TODO to complete
        summary: Brief summary of what was done
        artifacts_json: Optional JSON object with artifacts (e.g., {"file": "path/to/file.py", "tests_passed": true})
            """
    state = get_current_state()
    
    artifacts = {}
    if artifacts_json:
        try:
            artifacts = json.loads(artifacts_json)
        except json.JSONDecodeError:
            pass
    
    artifacts["summary"] = summary
    
    if not state.mark_todo_complete(todo_id, artifacts):
        return f"TODO '{todo_id}' not found."
    
    # Find next TODO
    next_todo = state.get_next_todo()
    next_info = ""
    if next_todo:
        next_info = f"\nNext TODO: [{next_todo.id}] {next_todo.title}"
    else:
        # Check if all done
        all_complete = all(
            t.status in (TodoStatus.COMPLETED, TodoStatus.SKIPPED)
            for t in state.todo_list
        )
        if all_complete:
            next_info = "\n🎉 All TODOs complete! Consider transitioning to the next phase."
    
    return f"""Completed: [{todo_id}]
Summary: {summary}
{next_info}"""


@tool(
    name="store_artifact",
    category=ToolCategory.WORKFLOW,
    description="Store an artifact (notes, code, documents) for use in later phases.",
    defer_loading=True,  # Optional feature, discoverable via search_tools
    keywords=["artifact", "store", "save", "notes", "document"],
)
def store_artifact(
    key: str,
    value: str,
    artifact_type: str = "text",
) -> str:
    """Store an artifact from the current workflow.
    
    Use this to save important outputs like notes, code, documents, etc.
    that may be needed in later phases.
    
    Args:
        key: Identifier for this artifact (e.g., "design_doc", "test_results")
        value: The artifact content (text, JSON, etc.)
        artifact_type: Type of artifact - "text", "json", "code", "path"
            """
    state = get_current_state()
    
    if artifact_type == "json":
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    
    state.artifacts[key] = {
        "type": artifact_type,
        "value": value,
        "phase": state.current_phase.value,
    }
    
    return f"Artifact '{key}' stored ({artifact_type})."


@tool(
    name="retrieve_artifact",
    category=ToolCategory.WORKFLOW,
    description="Retrieve a stored artifact from earlier in the workflow.",
    defer_loading=True,  # Optional feature, discoverable via search_tools
    keywords=["artifact", "retrieve", "get", "recall"],
)
def retrieve_artifact(key: str) -> str:
    """Retrieve a stored artifact from the workflow.
    
    Use this to access notes, documents, or other artifacts from earlier phases.
    
    Args:
        key: The artifact identifier
            """
    state = get_current_state()
    
    if key not in state.artifacts:
        available = list(state.artifacts.keys())
        return f"Artifact '{key}' not found. Available: {', '.join(available) if available else 'none'}"
    
    artifact = state.artifacts[key]
    if isinstance(artifact, dict) and "value" in artifact:
        return f"[{artifact.get('type', 'unknown')}] {artifact['value']}"
    return str(artifact)


@tool(
    name="list_todos",
    category=ToolCategory.WORKFLOW,
    description="List all TODO items in the current workflow with their status.",
    keywords=["todo", "list", "tasks", "status"],
)
def list_todos() -> str:
    """List all TODO items in the current workflow.
        """
    state = get_current_state()
    
    if not state.todo_list:
        return "No TODOs defined. Use 'add_todo_item' to create tasks."
    
    lines = ["TODOs:"]
    for todo in state.todo_list:
        status_icon = {
            TodoStatus.NOT_STARTED: "⬜",
            TodoStatus.IN_PROGRESS: "🔄",
            TodoStatus.COMPLETED: "✅",
            TodoStatus.BLOCKED: "🚫",
            TodoStatus.SKIPPED: "⏭️",
        }.get(todo.status, "❓")
        
        deps = f" (deps: {','.join(todo.dependencies)})" if todo.dependencies else ""
        lines.append(f"  {status_icon} [{todo.id}] {todo.title}{deps}")
    
    return "\n".join(lines)


# Export all workflow tools
WORKFLOW_TOOLS = [
    start_workflow,
    create_custom_workflow,
    get_workflow_status,
    transition_phase,
    add_todo_item,
    start_todo_item,
    complete_todo_item,
    store_artifact,
    retrieve_artifact,
    list_todos,
]
