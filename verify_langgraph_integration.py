#!/usr/bin/env python
"""Verification script for LangGraph integration.

This script verifies that all LangGraph components are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from airunner.components.llm.langgraph.state import (
            BaseAgentState,
            RAGAgentState,
            ToolAgentState,
            StateFactory,
        )
        from airunner.components.llm.langgraph.graph_builder import (
            LangGraphBuilder,
        )
        from airunner.components.llm.langgraph.bridge import LlamaIndexBridge
        from airunner.components.llm.langgraph.code_generator import (
            LangGraphCodeGenerator,
        )
        from airunner.components.llm.langgraph.runtime_executor import (
            LangGraphRuntime,
        )

        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_state_classes():
    """Test state class creation."""
    print("\nTesting state classes...")
    try:
        from airunner.components.llm.langgraph.state import (
            BaseAgentState,
            RAGAgentState,
            ToolAgentState,
        )

        # Test BaseAgentState
        base_state = BaseAgentState(messages=[], next_action="test")
        assert base_state["messages"] == []
        assert base_state["next_action"] == "test"

        # Test RAGAgentState
        rag_state = RAGAgentState(
            messages=[],
            next_action="test",
            rag_context="",
            retrieved_docs=[],
        )
        assert "rag_context" in rag_state

        # Test ToolAgentState
        tool_state = ToolAgentState(
            messages=[], next_action="test", tool_calls=[], tool_results=[]
        )
        assert "tool_calls" in tool_state

        print("✅ State classes working correctly")
        return True
    except Exception as e:
        print(f"❌ State class test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_graph_builder():
    """Test graph builder."""
    print("\nTesting graph builder...")
    try:
        from airunner.components.llm.langgraph.state import BaseAgentState
        from airunner.components.llm.langgraph.graph_builder import (
            LangGraphBuilder,
        )

        def test_node(state: BaseAgentState) -> BaseAgentState:
            state["messages"].append("Test")
            return state

        builder = LangGraphBuilder(BaseAgentState)
        builder.add_node("test_node", test_node)
        builder.set_entry_point("test_node")
        builder.add_edge("test_node", "END")

        # Validate
        assert builder.validate(), "Validation failed"

        # Compile
        workflow = builder.compile()
        assert workflow is not None, "Compilation failed"

        # Execute
        result = workflow.invoke({"messages": [], "next_action": "start"})
        assert "Test" in result["messages"]

        print("✅ Graph builder working correctly")
        return True
    except Exception as e:
        print(f"❌ Graph builder test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_visual_nodes_exist():
    """Test that visual node files exist."""
    print("\nChecking visual node files...")
    try:
        from pathlib import Path

        node_dir = (
            Path(__file__).parent
            / "src"
            / "airunner"
            / "components"
            / "nodegraph"
            / "gui"
            / "widgets"
            / "nodes"
            / "langgraph"
        )

        expected_nodes = [
            "base_langgraph_node.py",
            "state_schema_node.py",
            "llm_call_node.py",
            "rag_search_node.py",
            "tool_call_node.py",
            "conditional_branch_node.py",
        ]

        missing = []
        for node_file in expected_nodes:
            if not (node_dir / node_file).exists():
                missing.append(node_file)

        if missing:
            print(f"❌ Missing node files: {missing}")
            return False

        print(f"✅ All {len(expected_nodes)} visual node files exist")
        return True
    except Exception as e:
        print(f"❌ Visual node check failed: {e}")
        return False


def test_examples_exist():
    """Test that example files exist."""
    print("\nChecking example files...")
    try:
        from pathlib import Path

        examples_dir = Path(__file__).parent / "examples"

        expected_examples = [
            "langgraph_simple_workflow.py",
            "langgraph_rag_workflow.py",
        ]

        missing = []
        for example_file in expected_examples:
            if not (examples_dir / example_file).exists():
                missing.append(example_file)

        if missing:
            print(f"❌ Missing example files: {missing}")
            return False

        print(f"✅ All {len(expected_examples)} example files exist")
        return True
    except Exception as e:
        print(f"❌ Example check failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("LangGraph Integration Verification")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("State Classes", test_state_classes()))
    results.append(("Graph Builder", test_graph_builder()))
    results.append(("Visual Nodes", test_visual_nodes_exist()))
    results.append(("Examples", test_examples_exist()))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:.<50} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All verification tests passed!")
        print("LangGraph integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
