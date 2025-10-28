# Workflow Template Patterns

This document describes the common workflow patterns available in AI Runner's template system.

## Available Templates

### 1. RAG Workflow (`rag_workflow.json`)

**Category:** knowledge  
**Tags:** rag, search, knowledge, retrieval

**Description:**  
Retrieval-Augmented Generation workflow that searches a knowledge base and generates responses based on retrieved context.

**Variables:**
- `collection_name`: Name of the knowledge collection to search (default: "default")
- `top_k`: Number of top documents to retrieve (default: 5)
- `temperature`: LLM temperature for generation (default: 0.7)

**Flow:**
1. User Input → User's question or query
2. RAG Search → Search knowledge base for relevant documents
3. Prompt Template → Format retrieved context with question
4. LLM Generation → Generate answer based on context
5. Output → Final generated answer

**Use Cases:**
- Question answering over documents
- Knowledge base chat
- Document-grounded responses

---

### 2. Agent Loop Workflow (`agent_loop_workflow.json`)

**Category:** agent  
**Tags:** agent, reasoning, tools, loop, autonomous

**Description:**  
Autonomous agent workflow with reasoning, action selection, tool execution, and observation feedback loop.

**Variables:**
- `max_iterations`: Maximum number of agent loop iterations (default: 5)
- `temperature`: LLM temperature for reasoning (default: 0.7)
- `agent_name`: Name of the expert agent to use (default: "research_expert")

**Flow:**
1. Task Input → Task for agent to accomplish
2. Agent Reasoning → Analyze task and plan next action
3. Action Selection → Select best tool/action for current step
4. Tool Execution → Execute selected tool with parameters
5. Observation → Observe tool execution result
6. Loop Condition → Check if task complete or max iterations reached
   - If not complete → Return to Agent Reasoning with observation
   - If complete → Proceed to Final Result
7. Output → Final agent result

**Use Cases:**
- Multi-step task completion
- Research and analysis tasks
- Tool-based problem solving

---

### 3. Sequential Tool Chain (`tool_chain_workflow.json`)

**Category:** tools  
**Tags:** tools, chain, sequence, pipeline

**Description:**  
Chain multiple tools together in sequence, passing outputs as inputs to next tool.

**Variables:**
- `temperature`: LLM temperature if tools involve generation (default: 0.5)

**Flow:**
1. Initial Input → Input for tool chain
2. Tool 1 → First tool (e.g., search_web)
3. Tool 2 → Second tool (e.g., extract_text)
4. Tool 3 → Third tool (e.g., summarize)
5. Output → Final output from tool chain

**Use Cases:**
- Data processing pipelines
- Multi-stage transformations
- Sequential analysis workflows

---

## Using Templates

### From LLM Tools

Templates can be used via the workflow tools created in Issue #1873:

```python
# List available templates
from airunner.components.nodegraph.template_manager import get_template_manager

manager = get_template_manager()
templates = manager.list_templates()

# Create workflow from template
workflow_data = manager.create_from_template(
    template_name="RAG Workflow",
    workflow_name="my_rag_workflow",
    variables={"top_k": 10, "temperature": 0.5}
)

# Use with create_workflow tool
create_workflow(**workflow_data)
```

### From Python API

```python
from airunner.components.nodegraph.template_manager import get_template_manager

# Get template manager
manager = get_template_manager()

# Search for templates
rag_templates = manager.search_templates("rag")

# Get specific template
template = manager.get_template("RAG Workflow")

# Create workflow with custom variables
workflow = manager.create_from_template(
    "RAG Workflow",
    "my_custom_rag",
    variables={"collection_name": "my_docs", "top_k": 20}
)
```

## Creating Custom Templates

Templates are JSON files with the following structure:

```json
{
  "name": "Template Name",
  "description": "Template description",
  "category": "category_name",
  "tags": ["tag1", "tag2"],
  "author": "Author Name",
  "version": "1.0",
  "variables": {
    "var_name": "default_value"
  },
  "nodes": [
    {
      "node_identifier": "ai_runner.nodes.NodeClass",
      "name": "node_name",
      "pos_x": 100,
      "pos_y": 200,
      "properties": {
        "property_name": "{{var_name}}"
      }
    }
  ],
  "connections": [
    {
      "output_node_name": "source_node",
      "output_port": "output",
      "input_node_name": "target_node",
      "input_port": "input"
    }
  ]
}
```

### Variable Substitution

Variables use `{{variable_name}}` syntax and are replaced when creating workflows from templates:

```json
{
  "variables": {
    "collection": "default",
    "k": 5
  },
  "nodes": [
    {
      "properties": {
        "collection_name": "{{collection}}",
        "top_k": "{{k}}"
      }
    }
  ]
}
```

## Template Categories

Templates are organized by category:

- **knowledge**: RAG, search, retrieval workflows
- **agent**: Autonomous agent workflows
- **tools**: Tool chain and integration workflows
- **general**: General-purpose workflows

## Best Practices

1. **Clear Naming**: Use descriptive template names
2. **Documentation**: Provide detailed descriptions
3. **Defaults**: Set sensible default variable values
4. **Tags**: Add relevant tags for discoverability
5. **Positioning**: Use consistent node positioning (multiples of 100)
6. **Modularity**: Design templates to be composable
7. **Variables**: Parameterize values that users will want to customize

## Template Browser UI

The template browser (to be implemented in GUI) will provide:

- Browse templates by category
- Search templates by name, description, or tags
- Preview template structure
- Create workflows from templates with custom variables
- Import/export custom templates
