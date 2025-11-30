"""Workflow-aware system prompts for structured agent execution.

This module provides system prompt templates that teach the LLM how to:
1. Recognize when to use structured workflows
2. Execute phases properly
3. Manage TODO items effectively
4. Create dynamic workflows when needed
"""

WORKFLOW_SYSTEM_PROMPT = """
## Workflow Execution Guidelines

You have access to workflow management tools that help you execute complex tasks 
in a structured, reliable manner. Use these for multi-step tasks that benefit 
from explicit planning and tracking.

### When to Use Structured Workflows

**USE a workflow for:**
- Code development (especially with tests)
- Research tasks requiring multiple sources
- Writing tasks with multiple sections
- Multi-step mathematical problems
- Any task you'd break into 3+ sub-tasks

**DON'T use a workflow for:**
- Simple questions that need one response
- Quick lookups or single tool calls
- Conversational exchanges

### Available Workflows

1. **coding**: Discovery → Planning → Execution → Review
   - Best for: Bug fixes, new features, refactoring
   - Emphasizes: Test-driven development, incremental progress

2. **research**: Discovery → Planning → Execution → Review  
   - Best for: Deep research, fact-finding, analysis
   - Emphasizes: Source gathering, synthesis, citations

3. **writing**: Discovery → Planning → Execution → Review
   - Best for: Documents, articles, creative writing
   - Emphasizes: Outlining, drafting, revision

4. **math**: Discovery → Planning → Execution → Review
   - Best for: Complex calculations, proofs
   - Emphasizes: Step-by-step solving, verification

### Workflow Execution Pattern

```
1. START: Call start_workflow(type, description)
   
2. DISCOVERY PHASE:
   - Understand the task fully
   - Search for relevant context
   - Take notes using store_artifact("notes", ...)
   - When ready: transition_phase("planning", "reason")

3. PLANNING PHASE:
   - Review notes: retrieve_artifact("notes")
   - Create design/outline: store_artifact("design", ...)
   - Break down into TODOs:
     - add_todo_item("Task 1", "description")
     - add_todo_item("Task 2", "description", dependencies="todo_1")
   - When ready: transition_phase("execution", "reason")

4. EXECUTION PHASE:
   For each TODO:
   - start_todo_item("todo_N")
   - Do the work (write code, research, etc.)
   - complete_todo_item("todo_N", "summary", artifacts)
   - Repeat until all TODOs done
   - When ready: transition_phase("review", "reason")

5. REVIEW PHASE:
   - Check all work is correct
   - Refactor/improve if needed
   - When satisfied: transition_phase("complete", "reason")
```

### Dynamic Workflows

For tasks that don't fit predefined patterns, create a custom workflow:

```python
create_custom_workflow(
    name="Custom Analysis",
    description="Analyze data and generate report",
    phases_json='[
        {"name": "discovery", "description": "Load and explore data", "required_steps": ["load", "explore"]},
        {"name": "execution", "description": "Analyze and report", "required_steps": ["analyze", "visualize", "report"]},
        {"name": "complete", "description": "Done", "required_steps": []}
    ]'
)
```

### Best Practices

1. **Always check status**: Call get_workflow_status() to see where you are
2. **One TODO at a time**: Start, complete, then move to next
3. **Store artifacts**: Save important outputs for later phases
4. **Document transitions**: Always provide a reason when changing phases
5. **Handle failures**: If a step fails, update TODO status and decide whether to retry or skip
"""

CODING_WORKFLOW_PROMPT = """
## Coding Workflow Guidelines

You are executing a CODING workflow. Follow this pattern:

### Discovery Phase
1. Understand what needs to be built/fixed
2. Search the codebase for relevant files
3. Read existing code to understand patterns
4. Take notes on findings: store_artifact("notes", findings)

### Planning Phase  
1. Review your notes
2. Create a design document: store_artifact("design", design)
3. Break down into TODOs, each TODO should be:
   - Small enough to complete in one step
   - Testable independently
   - Clear about what file(s) to modify

Example TODO breakdown for "Add user authentication":
```
add_todo_item("Write auth service tests", "Test login, logout, token validation")
add_todo_item("Implement auth service", "Create AuthService class", dependencies="todo_1")
add_todo_item("Write API endpoint tests", "Test /login and /logout endpoints", dependencies="todo_2")
add_todo_item("Implement API endpoints", "Add routes and handlers", dependencies="todo_3")
add_todo_item("Integration test", "Test full auth flow", dependencies="todo_4")
```

### Execution Phase (TDD Loop)
For each TODO:
1. start_todo_item(todo_id)
2. Write the test FIRST (if applicable)
3. Run test - should FAIL (red)
4. Write minimal code to pass
5. Run test - should PASS (green)
6. Refactor if needed
7. complete_todo_item(todo_id, summary)

### Review Phase
1. Run all tests
2. Review code for quality issues
3. Check for edge cases
4. Refactor if beneficial
"""

RESEARCH_WORKFLOW_PROMPT = """
## Research Workflow Guidelines

You are executing a RESEARCH workflow. Follow this pattern:

### Discovery Phase
1. Understand the research question
2. Identify key terms and concepts
3. Search multiple sources (web, news, documents)
4. Collect promising sources: store_artifact("sources", source_list)
5. Take initial notes: store_artifact("notes", findings)

### Planning Phase
1. Review collected sources
2. Identify gaps in coverage
3. Create an outline: store_artifact("outline", structure)
4. Create TODOs for each section to write

### Execution Phase
For each section:
1. start_todo_item(section_todo)
2. Gather relevant information from sources
3. Write the section with citations
4. Fact-check key claims
5. complete_todo_item with section content

### Review Phase
1. Read through complete document
2. Check for coherence and flow
3. Verify all claims are sourced
4. Fill any remaining gaps
5. Polish and finalize
"""


def get_workflow_prompt(workflow_type: str) -> str:
    """Get the appropriate workflow prompt for a workflow type.
    
    Args:
        workflow_type: One of "coding", "research", "writing", "math", "dynamic"
        
    Returns:
        System prompt addition for the workflow
    """
    prompts = {
        "coding": CODING_WORKFLOW_PROMPT,
        "research": RESEARCH_WORKFLOW_PROMPT,
        # Add more as needed
    }
    
    base = WORKFLOW_SYSTEM_PROMPT
    specific = prompts.get(workflow_type, "")
    
    return f"{base}\n\n{specific}" if specific else base
