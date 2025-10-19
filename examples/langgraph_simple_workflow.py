"""Example: Simple LangGraph workflow using the builder API.

This example demonstrates how to use the LangGraph integration
programmatically without the visual interface.
"""

import logging
from airunner.components.llm.langgraph.state import BaseAgentState
from airunner.components.llm.langgraph.graph_builder import LangGraphBuilder
from airunner.components.llm.langgraph.code_generator import (
    LangGraphCodeGenerator,
)
from airunner.components.llm.langgraph.runtime_executor import LangGraphRuntime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define workflow nodes
def perceive(state: BaseAgentState) -> BaseAgentState:
    """Read input and prepare for processing."""
    logger.info("Perceiving input")
    state["messages"].append("Input received")
    state["next_action"] = "think"
    return state


def think(state: BaseAgentState) -> BaseAgentState:
    """Process input and decide action."""
    logger.info("Thinking")
    state["messages"].append("Decided on response")
    state["next_action"] = "act"
    return state


def act(state: BaseAgentState) -> BaseAgentState:
    """Execute action."""
    logger.info("Acting")
    state["messages"].append("Action executed")
    state["next_action"] = "end"
    return state


def main():
    """Run the example workflow."""
    print("=" * 60)
    print("LangGraph Integration Example: Simple Workflow")
    print("=" * 60)

    # Build workflow
    print("\n1. Building workflow...")
    builder = LangGraphBuilder(BaseAgentState)
    builder.add_node("perceive", perceive)
    builder.add_node("think", think)
    builder.add_node("act", act)
    builder.add_edge("perceive", "think")
    builder.add_edge("think", "act")
    builder.add_edge("act", "END")
    builder.set_entry_point("perceive")

    # Validate
    print("\n2. Validating workflow...")
    if not builder.validate():
        print("❌ Validation failed")
        return

    print("✅ Workflow valid")
    print(f"   Nodes: {len(builder.nodes)}")
    print(f"   Edges: {len(builder.edges)}")

    # Compile workflow
    print("\n3. Compiling workflow...")
    app = builder.compile()
    print("✅ Workflow compiled")

    # Execute workflow
    print("\n4. Executing workflow...")
    initial_state = {
        "messages": [],
        "next_action": "",
        "error": None,
        "metadata": {},
    }

    result = app.invoke(initial_state)

    print("\n5. Results:")
    print(f"   Messages: {result['messages']}")
    print(f"   Final action: {result['next_action']}")

    # Generate code
    print("\n6. Generating Python code...")
    generator = LangGraphCodeGenerator("simple_workflow", "SimpleState")

    node_configs = {
        "perceive": {
            "type": "custom",
            "description": "Perceive input",
            "code": "state['messages'].append('Input received')\n    state['next_action'] = 'think'",
        },
        "think": {
            "type": "custom",
            "description": "Think and decide",
            "code": "state['messages'].append('Decided on response')\n    state['next_action'] = 'act'",
        },
        "act": {
            "type": "custom",
            "description": "Execute action",
            "code": "state['messages'].append('Action executed')\n    state['next_action'] = 'end'",
        },
    }

    code = generator.generate(
        nodes=node_configs,
        edges=[("perceive", "think"), ("think", "act"), ("act", "END")],
        conditional_edges=[],
        state_fields={
            "messages": "List[str]",
            "next_action": "str",
            "error": "Optional[str]",
            "metadata": "Dict[str, Any]",
        },
        entry_point="perceive",
    )

    print("\nGenerated code preview (first 500 chars):")
    print("-" * 60)
    print(code[:500] + "...")
    print("-" * 60)

    # Runtime compilation test
    print("\n7. Testing runtime compilation...")
    runtime = LangGraphRuntime()

    try:
        module = runtime.compile_and_load(code, "simple_workflow_module")
        print("✅ Code compiled successfully")

        # Inspect module
        info = runtime.inspect_module(module)
        print(f"   Functions: {info['functions']}")
        print(f"   Has app: {info['has_app']}")

    except Exception as e:
        print(f"❌ Compilation failed: {e}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
