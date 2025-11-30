"""Workflow state machine for structured agent execution.

This module provides a state machine that enables:
1. Predefined workflows (coding, research, writing, math)
2. Dynamic workflows created by the LLM at runtime
3. Phase-based execution with explicit transitions
4. TODO list management integrated into the workflow

The state machine is designed to work within a single LangGraph workflow,
avoiding the complexity of multiple separate graphs while maintaining
structured execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class WorkflowType(Enum):
    """Types of workflows the agent can execute."""
    
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    MATH = "math"
    DYNAMIC = "dynamic"  # LLM-defined workflow
    SIMPLE = "simple"  # Single-turn, no workflow needed


class Phase(Enum):
    """Standard phases that workflows can use."""
    
    DISCOVERY = "discovery"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    COMPLETE = "complete"


class TodoStatus(Enum):
    """Status of a TODO item."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class TodoItem:
    """A single TODO item in the workflow."""
    
    id: str
    title: str
    description: str
    status: TodoStatus = TodoStatus.NOT_STARTED
    phase: Optional[Phase] = None
    parent_id: Optional[str] = None  # For sub-tasks
    dependencies: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)  # Output from this task
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


@dataclass
class PhaseDefinition:
    """Definition of a workflow phase."""
    
    name: Phase
    description: str
    required_steps: List[str]  # Step names that must be completed
    optional_steps: List[str] = field(default_factory=list)
    entry_conditions: List[str] = field(default_factory=list)  # Conditions to enter phase
    exit_conditions: List[str] = field(default_factory=list)  # Conditions to exit phase
    allowed_tools: List[str] = field(default_factory=list)  # Tools available in this phase


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow.
    
    Can be predefined (CODING, RESEARCH) or dynamically created by the LLM.
    """
    
    workflow_type: WorkflowType
    name: str
    description: str
    phases: List[PhaseDefinition]
    initial_phase: Phase = Phase.DISCOVERY
    
    def get_phase(self, phase: Phase) -> Optional[PhaseDefinition]:
        """Get phase definition by phase enum."""
        for p in self.phases:
            if p.name == phase:
                return p
        return None
    
    def get_next_phase(self, current: Phase) -> Optional[Phase]:
        """Get the next phase after current."""
        phase_order = [p.name for p in self.phases]
        try:
            idx = phase_order.index(current)
            if idx + 1 < len(phase_order):
                return phase_order[idx + 1]
        except ValueError:
            pass
        return None


@dataclass 
class WorkflowState:
    """Current state of workflow execution.
    
    This is the core state object that gets passed through the LangGraph
    workflow and enables structured multi-phase execution.
    """
    
    # Workflow identification
    workflow_type: WorkflowType = WorkflowType.SIMPLE
    workflow_definition: Optional[WorkflowDefinition] = None
    
    # Phase tracking
    current_phase: Phase = Phase.DISCOVERY
    phase_step: int = 0
    phase_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # TODO list for structured execution
    todo_list: List[TodoItem] = field(default_factory=list)
    current_todo_id: Optional[str] = None
    
    # Artifacts collected during workflow
    artifacts: Dict[str, Any] = field(default_factory=dict)
    # Example artifacts:
    # - "notes": str - Discovery notes
    # - "design_doc": str - Planning document  
    # - "todo_plan": List[str] - Planned tasks
    # - "code_files": Dict[str, str] - Written code
    # - "test_results": List[Dict] - Test execution results
    # - "research_sources": List[str] - URLs/documents found
    
    # Execution tracking
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 0
    max_iterations: int = 50
    
    # Error handling
    last_error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for LangGraph."""
        return {
            "workflow_type": self.workflow_type.value,
            "current_phase": self.current_phase.value,
            "phase_step": self.phase_step,
            "todo_list": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "phase": t.phase.value if t.phase else None,
                }
                for t in self.todo_list
            ],
            "current_todo_id": self.current_todo_id,
            "artifacts": self.artifacts,
            "iterations": self.iterations,
        }
    
    def get_current_todo(self) -> Optional[TodoItem]:
        """Get the currently active TODO item."""
        if not self.current_todo_id:
            return None
        for todo in self.todo_list:
            if todo.id == self.current_todo_id:
                return todo
        return None
    
    def get_next_todo(self) -> Optional[TodoItem]:
        """Get the next TODO item to work on."""
        for todo in self.todo_list:
            if todo.status == TodoStatus.NOT_STARTED:
                # Check dependencies
                deps_met = all(
                    any(t.id == dep and t.status == TodoStatus.COMPLETED 
                        for t in self.todo_list)
                    for dep in todo.dependencies
                )
                if deps_met:
                    return todo
        return None
    
    def mark_todo_complete(self, todo_id: str, artifacts: Optional[Dict] = None) -> bool:
        """Mark a TODO item as complete."""
        for todo in self.todo_list:
            if todo.id == todo_id:
                todo.status = TodoStatus.COMPLETED
                todo.completed_at = datetime.utcnow().isoformat()
                if artifacts:
                    todo.artifacts.update(artifacts)
                if self.current_todo_id == todo_id:
                    self.current_todo_id = None
                return True
        return False
    
    def add_todo(self, title: str, description: str, phase: Optional[Phase] = None,
                 dependencies: Optional[List[str]] = None) -> TodoItem:
        """Add a new TODO item."""
        todo_id = f"todo_{len(self.todo_list) + 1}"
        todo = TodoItem(
            id=todo_id,
            title=title,
            description=description,
            phase=phase or self.current_phase,
            dependencies=dependencies or [],
        )
        self.todo_list.append(todo)
        return todo
    
    def transition_phase(self, new_phase: Phase) -> bool:
        """Transition to a new phase."""
        self.phase_history.append({
            "from_phase": self.current_phase.value,
            "to_phase": new_phase.value,
            "step": self.phase_step,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.current_phase = new_phase
        self.phase_step = 0
        return True
    
    def can_transition(self) -> bool:
        """Check if we can transition to next phase."""
        if not self.workflow_definition:
            return True
        
        phase_def = self.workflow_definition.get_phase(self.current_phase)
        if not phase_def:
            return True
            
        # Check if required steps are done
        # This is simplified - real implementation would check artifacts
        return True
    
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        if self.current_phase == Phase.COMPLETE:
            return True
        
        # All TODOs complete
        if self.todo_list and all(
            t.status in (TodoStatus.COMPLETED, TodoStatus.SKIPPED)
            for t in self.todo_list
        ):
            return True
            
        return False


# =============================================================================
# Predefined Workflow Definitions
# =============================================================================

CODING_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.CODING,
    name="Coding Workflow",
    description="Structured workflow for code development with TDD",
    phases=[
        PhaseDefinition(
            name=Phase.DISCOVERY,
            description="Understand the task and gather context",
            required_steps=["understand_task", "search_codebase", "take_notes"],
            allowed_tools=["semantic_search", "read_file", "grep_search", "record_knowledge"],
        ),
        PhaseDefinition(
            name=Phase.PLANNING,
            description="Review notes, create design doc, and TODO list",
            required_steps=["review_notes", "create_design", "create_todos"],
            allowed_tools=["recall_knowledge", "create_document", "manage_todos"],
        ),
        PhaseDefinition(
            name=Phase.EXECUTION,
            description="Execute TODO items: write tests, write code, validate, verify",
            required_steps=["write_test", "write_code", "validate_code", "run_test", "verify"],
            allowed_tools=[
                "write_file", "edit_file", "run_tests", "run_command",
                "read_file", "manage_todos", "validate_code", "lint_code",
                "create_code_file", "edit_code_file"
            ],
            exit_conditions=["all_todos_complete", "all_tests_pass"],
        ),
        PhaseDefinition(
            name=Phase.REVIEW,
            description="Review changes and refactor if needed",
            required_steps=["review_changes", "refactor_if_needed"],
            allowed_tools=["read_file", "edit_file", "run_tests"],
        ),
        PhaseDefinition(
            name=Phase.COMPLETE,
            description="Workflow complete",
            required_steps=[],
        ),
    ],
)


RESEARCH_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.RESEARCH,
    name="Deep Research Workflow", 
    description="Structured workflow for comprehensive research",
    phases=[
        PhaseDefinition(
            name=Phase.DISCOVERY,
            description="Understand topic and gather initial sources",
            required_steps=["understand_topic", "initial_search", "collect_sources"],
            allowed_tools=["search_web", "search_news", "scrape_website", "record_knowledge"],
        ),
        PhaseDefinition(
            name=Phase.PLANNING,
            description="Review findings, create outline",
            required_steps=["review_sources", "identify_gaps", "create_outline"],
            allowed_tools=["recall_knowledge", "search_web", "create_document"],
        ),
        PhaseDefinition(
            name=Phase.EXECUTION,
            description="Write research document section by section",
            required_steps=["write_sections", "cite_sources", "fact_check"],
            allowed_tools=[
                "recall_knowledge", "search_web", "scrape_website",
                "create_document", "edit_document"
            ],
        ),
        PhaseDefinition(
            name=Phase.REVIEW,
            description="Review document, fill gaps, finalize",
            required_steps=["review_document", "fill_gaps", "finalize"],
            allowed_tools=["read_document", "edit_document", "search_web"],
        ),
        PhaseDefinition(
            name=Phase.COMPLETE,
            description="Research complete",
            required_steps=[],
        ),
    ],
)


WRITING_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.WRITING,
    name="Writing Workflow",
    description="Structured workflow for creative/technical writing",
    phases=[
        PhaseDefinition(
            name=Phase.DISCOVERY,
            description="Understand requirements and gather inspiration",
            required_steps=["understand_requirements", "gather_references"],
            allowed_tools=["search_web", "rag_search", "record_knowledge"],
        ),
        PhaseDefinition(
            name=Phase.PLANNING,
            description="Create outline and structure",
            required_steps=["create_outline", "plan_sections"],
            allowed_tools=["create_document", "recall_knowledge"],
        ),
        PhaseDefinition(
            name=Phase.EXECUTION,
            description="Write content",
            required_steps=["write_draft", "revise"],
            allowed_tools=["create_document", "edit_document"],
        ),
        PhaseDefinition(
            name=Phase.REVIEW,
            description="Review and polish",
            required_steps=["proofread", "finalize"],
            allowed_tools=["read_document", "edit_document"],
        ),
        PhaseDefinition(
            name=Phase.COMPLETE,
            description="Writing complete",
            required_steps=[],
        ),
    ],
)


MATH_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.MATH,
    name="Math Problem Solving Workflow",
    description="Structured workflow for mathematical problem solving",
    phases=[
        PhaseDefinition(
            name=Phase.DISCOVERY,
            description="Understand problem and identify approach",
            required_steps=["parse_problem", "identify_concepts", "plan_approach"],
            allowed_tools=["search_web", "calculator", "record_knowledge"],
        ),
        PhaseDefinition(
            name=Phase.PLANNING,
            description="Break down into steps",
            required_steps=["decompose_problem", "identify_formulas"],
            allowed_tools=["calculator", "create_document"],
        ),
        PhaseDefinition(
            name=Phase.EXECUTION,
            description="Solve step by step",
            required_steps=["solve_steps", "verify_intermediate"],
            allowed_tools=["calculator", "python_executor", "wolfram_alpha"],
        ),
        PhaseDefinition(
            name=Phase.REVIEW,
            description="Verify solution",
            required_steps=["check_answer", "verify_logic"],
            allowed_tools=["calculator", "python_executor"],
        ),
        PhaseDefinition(
            name=Phase.COMPLETE,
            description="Problem solved",
            required_steps=[],
        ),
    ],
)


# Registry of predefined workflows
WORKFLOW_REGISTRY: Dict[WorkflowType, WorkflowDefinition] = {
    WorkflowType.CODING: CODING_WORKFLOW,
    WorkflowType.RESEARCH: RESEARCH_WORKFLOW,
    WorkflowType.WRITING: WRITING_WORKFLOW,
    WorkflowType.MATH: MATH_WORKFLOW,
}


def get_workflow(workflow_type: WorkflowType) -> Optional[WorkflowDefinition]:
    """Get a predefined workflow by type."""
    return WORKFLOW_REGISTRY.get(workflow_type)


def create_dynamic_workflow(
    name: str,
    description: str,
    phases: List[Dict[str, Any]],
) -> WorkflowDefinition:
    """Create a dynamic workflow from LLM-generated specification.
    
    This allows the LLM to define its own workflow at runtime.
    
    Args:
        name: Workflow name
        description: What this workflow does
        phases: List of phase definitions as dicts
        
    Returns:
        WorkflowDefinition that can be executed
    """
    phase_defs = []
    for phase_dict in phases:
        phase_defs.append(PhaseDefinition(
            name=Phase(phase_dict.get("name", "execution")),
            description=phase_dict.get("description", ""),
            required_steps=phase_dict.get("required_steps", []),
            optional_steps=phase_dict.get("optional_steps", []),
            allowed_tools=phase_dict.get("allowed_tools", []),
        ))
    
    return WorkflowDefinition(
        workflow_type=WorkflowType.DYNAMIC,
        name=name,
        description=description,
        phases=phase_defs,
    )
