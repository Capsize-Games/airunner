

# LangGraph Visual Workflow Builder - User Guide

**AI Runner LangGraph Integration**  
Visual agent workflow builder with code generation

---

## 🎯 Overview

AI Runner now includes a powerful visual workflow builder for creating LangGraph agentic workflows through a drag-and-drop interface. This integration allows you to:

- **Visually build** complex agent workflows
- **Export to Python** code for standalone execution
- **Integrate with LlamaIndex** RAG and existing tools
- **Execute at runtime** without saving files

---

## 🚀 Quick Start

### 1. Open the NodeGraph

In AI Runner, navigate to the **NodeGraph** tab.

### 2. Add LangGraph Nodes

Look for the **LangGraph** category in the node palette:

- **State Schema** - Define workflow state structure
- **LLM Call** - Call language models
- **RAG Search** - Search knowledge base with LlamaIndex
- **Tool Call** - Execute registered tools
- **Conditional Branch** - Add if/else logic

### 3. Connect Nodes

Drag connections between execution ports (triangles) to define workflow.

### 4. Configure Properties

Double-click nodes to set parameters like model, temperature, prompts, etc.

### 5. Export to Code

Use the export function to generate executable Python code from your visual graph.

---

## 📦 Available Nodes

### State Schema Node

**Purpose:** Define the data structure passed between workflow nodes.

**Properties:**
- `state_name`: Name of the state class (default: "AgentState")
- `state_type`: Predefined type (base, rag, tool, custom)
- `custom_fields`: JSON dict of additional fields

**State Types:**
- **base**: Basic message passing (`messages`, `next_action`, `error`, `metadata`)
- **rag**: RAG workflows (adds `rag_context`, `retrieved_docs`, `query`)
- **tool**: Tool execution (adds `tool_calls`, `tool_results`, `current_tool`)
- **custom**: Define your own fields as JSON

**Example Custom Fields:**
```json
{
  "user_name": "str",
  "session_id": "str",
  "counter": "int"
}
```

---

### LLM Call Node

**Purpose:** Call a language model within the workflow.

**Properties:**
- `model`: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
- `temperature`: Sampling temperature (0.0-2.0)
- `max_tokens`: Maximum response length
- `system_prompt`: System instructions for the LLM
- `message_key`: State field to read messages from
- `response_key`: State field to write response to

**Input Ports:**
- `prompt`: Optional prompt override
- `system_prompt`: Optional system prompt override

**Output Ports:**
- `response`: LLM response

**Code Generation:**
Generates a function that:
1. Gets messages from state
2. Calls LLM with configured parameters
3. Stores response in state

---

### RAG Search Node

**Purpose:** Retrieve relevant documents using LlamaIndex RAG.

**Properties:**
- `top_k`: Number of documents to retrieve (1-20)
- `query_key`: State field containing query
- `context_key`: Where to store retrieved context
- `docs_key`: Where to store document metadata

**Input Ports:**
- `query`: Search query

**Output Ports:**
- `context`: Retrieved text context
- `documents`: Document metadata list

**Usage with LlamaIndex:**
The RAG node integrates with your existing LlamaIndex vector store:

```python
from airunner.components.llm.langgraph.bridge import LlamaIndexBridge

# Create RAG node from index
rag_node = LlamaIndexBridge.create_rag_node(
    rag_index=my_vector_index,
    top_k=5
)
```

---

### Tool Call Node

**Purpose:** Execute a registered tool from the ToolRegistry.

**Properties:**
- `tool_name`: Name of tool to execute
- `input_key`: State field containing tool input
- `output_key`: Where to store tool result

**Input Ports:**
- `tool_input`: Input for the tool

**Output Ports:**
- `tool_output`: Tool execution result

**Available Tools:**
Tools registered with the `@tool` decorator are automatically available:

```python
from airunner.components.llm.core.tool_registry import tool, ToolCategory

@tool(
    name="search_docs",
    category=ToolCategory.SEARCH,
    description="Search documentation"
)
def search_docs(query: str) -> str:
    # Implementation
    return results
```

---

### Conditional Branch Node

**Purpose:** Add if/else logic to workflows.

**Properties:**
- `condition_code`: Python expression to evaluate
- `true_route`: Node name if condition is true
- `false_route`: Node name if condition is false

**Special Features:**
- Has two execution output ports: **True** (green) and **False** (red)
- Evaluates Python expressions with access to state
- Can route to END to terminate workflow

**Example Conditions:**
```python
# Simple field check
return state.get("next_action") == "continue"

# Numeric comparison
return len(state["messages"]) > 5

# Complex logic
return state.get("error") is None and state["query"]
```

---

## 🔧 Programmatic Usage

You can use the LangGraph integration programmatically without the visual interface.

### Basic Workflow

```python
from airunner.components.llm.langgraph.state import BaseAgentState
from airunner.components.llm.langgraph.graph_builder import LangGraphBuilder

# Define node functions
def process(state: BaseAgentState) -> BaseAgentState:
    state["messages"].append("Processed")
    return state

# Build workflow
builder = LangGraphBuilder(BaseAgentState)
builder.add_node("process", process)
builder.set_entry_point("process")
builder.add_edge("process", "END")

# Compile and execute
app = builder.compile()
result = app.invoke({
    "messages": [],
    "next_action": "",
    "error": None,
    "metadata": {}
})
```

### RAG Workflow

```python
from airunner.components.llm.langgraph.state import RAGAgentState
from airunner.components.llm.langgraph.bridge import LlamaIndexBridge

# Create RAG node from existing index
rag_node = LlamaIndexBridge.create_rag_node(
    rag_index=my_index,
    top_k=5
)

# Add to workflow
builder = LangGraphBuilder(RAGAgentState)
builder.add_node("search", rag_node)
# ... add more nodes
```

### Code Generation

```python
from airunner.components.llm.langgraph.code_generator import LangGraphCodeGenerator
from pathlib import Path

generator = LangGraphCodeGenerator("my_agent", "AgentState")

code = generator.generate(
    nodes=node_configs,
    edges=edge_list,
    conditional_edges=conditional_list,
    state_fields={"messages": "List[str]"},
    entry_point="start"
)

# Save to file
generator.save(code, Path("generated_agent.py"))
```

### Runtime Execution

```python
from airunner.components.llm.langgraph.runtime_executor import LangGraphRuntime

runtime = LangGraphRuntime()

# Compile code
module = runtime.compile_and_load(code, "my_agent")

# Execute
result = runtime.execute_workflow(
    module,
    initial_state={"messages": []}
)
```

---

## 🎨 Visual Graph Export

### Exporting from NodeGraph

```python
from airunner.components.llm.langgraph.exporter import LangGraphExporter
from pathlib import Path

exporter = LangGraphExporter()

# Export visual graph to code
code = exporter.export(
    graph=node_graph_instance,
    output_path=Path("my_workflow.py"),
    workflow_name="my_agent"
)
```

### Generated Code Structure

The exported code is clean, standalone Python:

```python
"""LangGraph workflow: my_agent.

Auto-generated by AI Runner LangGraph integration.
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import logging

# State definition
class AgentState(TypedDict):
    messages: List[str]
    next_action: str
    # ...

# Node functions
def node_1(state: AgentState) -> AgentState:
    # Node logic
    return state

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("node_1", node_1)
# ...
app = workflow.compile()

# Execution function
def run_my_agent(initial_state):
    return app.invoke(initial_state)

if __name__ == "__main__":
    # Example usage
    result = run_my_agent({"messages": []})
```

---

## 🔌 Integration Points

### With LlamaIndex RAG

AI Runner's existing LlamaIndex RAG system integrates seamlessly:

```python
# In your agent code
from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

# Access RAG index
rag_index = agent.rag_system.get_index()

# Create LangGraph RAG node
rag_node = LlamaIndexBridge.create_rag_node(rag_index)
```

### With Tool Registry

Tools registered with `@tool` decorator are automatically available:

```python
from airunner.components.llm.core.tool_registry import tool, ToolCategory

@tool(
    name="analyze_sentiment",
    category=ToolCategory.ANALYSIS,
    description="Analyze text sentiment"
)
def analyze_sentiment(text: str) -> dict:
    # Your implementation
    return {"sentiment": "positive", "confidence": 0.95}

# Use in workflow via ToolCallNode
# Tool will be available by name "analyze_sentiment"
```

### With Existing LLM System

Your existing LLM configurations work with LangGraph nodes:

```python
# LLM settings from AI Runner
llm_settings = agent.llm_settings

# Use in LangGraph LLM node
# Model, temperature, etc. from settings
```

---

## 📝 Example Workflows

### 1. Simple Chat Agent

**Visual Workflow:**
```
[Start] → [LLM Call] → [END]
```

**Purpose:** Basic chat interaction

**Nodes:**
1. **LLM Call**: Model=gpt-4, responds to user message

### 2. RAG-Enhanced Chat

**Visual Workflow:**
```
[Start] → [RAG Search] → [LLM Call] → [END]
```

**Purpose:** Answer questions using knowledge base

**Nodes:**
1. **RAG Search**: Retrieve relevant docs, top_k=5
2. **LLM Call**: Generate answer with context

### 3. Tool-Using Agent

**Visual Workflow:**
```
[Start] → [LLM Call] → [Conditional] 
                           ├─(needs tool)→ [Tool Call] → [LLM Call]
                           └─(done)→ [END]
```

**Purpose:** Agent that decides when to use tools

**Nodes:**
1. **LLM Call**: Analyze request
2. **Conditional Branch**: Check if tool needed
3. **Tool Call**: Execute tool
4. **LLM Call**: Format final response

### 4. Research Agent (Loop)

**Visual Workflow:**
```
[Start] → [RAG Search] → [LLM Call] → [Conditional]
                                          ├─(continue)→ [RAG Search] (loop)
                                          └─(done)→ [END]
```

**Purpose:** Iterative research with multiple searches

**Nodes:**
1. **RAG Search**: Find relevant info
2. **LLM Call**: Analyze and decide next query
3. **Conditional Branch**: Continue or finish

---

## 🐛 Debugging

### Visual Debugging

- **Step through nodes**: Execute one node at a time
- **Inspect state**: View state after each node
- **Breakpoints**: Pause execution at specific nodes

### Code Debugging

Generated code includes logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Each node logs its execution:
```
INFO:__main__:Executing node: rag_search
INFO:__main__:Retrieved 5 documents
INFO:__main__:Executing node: llm_call
INFO:__main__:LLM call completed
```

### Common Issues

**Issue:** "Tool not found"
- **Solution:** Ensure tool is registered with `@tool` decorator

**Issue:** "RAG index missing"
- **Solution:** Pass RAG index via state metadata or config

**Issue:** "Syntax error in generated code"
- **Solution:** Check node properties for invalid Python expressions

---

## 🔐 Best Practices

### 1. State Design

- Keep state simple and flat
- Use descriptive field names
- Document custom state fields

### 2. Node Naming

- Use clear, descriptive node names
- Follow snake_case convention
- Avoid special characters

### 3. Error Handling

- Always check for `error` in state
- Set `error` field when problems occur
- Add conditional branches for error paths

### 4. Performance

- Limit RAG top_k to necessary documents
- Use streaming for long-running workflows
- Cache expensive operations

### 5. Testing

- Test workflows with example data
- Validate generated code before deployment
- Use unit tests for node functions

---

## 📚 API Reference

### LangGraphBuilder

```python
class LangGraphBuilder:
    def __init__(self, state_class: type)
    def add_node(self, name: str, func: Callable) -> LangGraphBuilder
    def add_edge(self, source: str, target: str) -> LangGraphBuilder
    def add_conditional_edge(self, source: str, condition: Callable, mapping: dict)
    def set_entry_point(self, node_name: str) -> LangGraphBuilder
    def compile(self, checkpointer=None) -> CompiledGraph
    def validate(self) -> bool
```

### LlamaIndexBridge

```python
class LlamaIndexBridge:
    @staticmethod
    def create_rag_node(rag_index, state_query_key, state_context_key, top_k)
    
    @staticmethod
    def create_chat_engine_node(chat_engine, state_message_key)
    
    @staticmethod
    def create_tool_node(tool_name, state_input_key, state_output_key)
```

### LangGraphCodeGenerator

```python
class LangGraphCodeGenerator:
    def __init__(self, workflow_name: str, state_class_name: str)
    def generate(self, nodes, edges, conditional_edges, state_fields, entry_point) -> str
    def save(self, code: str, output_path: Path)
    def format_code(self, code: str) -> str
```

### LangGraphRuntime

```python
class LangGraphRuntime:
    def compile_and_load(self, code: str, module_name: str) -> ModuleType
    def execute_workflow(self, module, initial_state, config) -> dict
    def validate_code(self, code: str) -> tuple[bool, str]
    def clear_cache()
```

---

## 🤝 Contributing

Want to add new node types? See the developer guide:

1. Create new node class extending `BaseLangGraphNode`
2. Implement `to_langgraph_code()` method
3. Add properties and ports
4. Register in `node_graph_widget.py`

---

## 📄 License

MIT License - Same as AI Runner

---

## 🆘 Support

- **Documentation**: `/docs/LANGGRAPH_NODEGRAPH_INTEGRATION.md`
- **Examples**: `/examples/langgraph_*.py`
- **Tests**: `/tests/components/llm/langgraph/`
- **Issues**: https://github.com/Capsize-Games/airunner/issues

---

**Happy Agent Building! 🚀**
