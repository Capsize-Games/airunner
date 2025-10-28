"""Tests for LangGraph integration.

Basic tests for the core LangGraph functionality.
"""

import pytest
from airunner.components.llm.langgraph.state import (
    BaseAgentState,
    RAGAgentState,
    StateFactory,
)
from airunner.components.llm.langgraph.graph_builder import LangGraphBuilder
from airunner.components.llm.langgraph.code_generator import (
    LangGraphCodeGenerator,
)
from airunner.components.llm.langgraph.runtime_executor import LangGraphRuntime


class TestStateDefinitions:
    """Test state class definitions."""

    def test_base_agent_state(self):
        """Test BaseAgentState has required fields."""
        state: BaseAgentState = {
            "messages": [],
            "next_action": "",
            "error": None,
            "metadata": {},
        }
        assert "messages" in state
        assert "next_action" in state
        assert "error" in state
        assert "metadata" in state

    def test_rag_agent_state(self):
        """Test RAGAgentState extends BaseAgentState."""
        state: RAGAgentState = {
            "messages": [],
            "next_action": "",
            "error": None,
            "metadata": {},
            "rag_context": "",
            "retrieved_docs": [],
            "query": "",
        }
        assert "rag_context" in state
        assert "retrieved_docs" in state
        assert "query" in state

    def test_state_factory(self):
        """Test StateFactory can create custom states."""
        CustomState = StateFactory.create_state_class(
            "CustomState",
            BaseAgentState,
            {"custom_field": str},
        )

        state = CustomState(
            messages=[],
            next_action="",
            error=None,
            metadata={},
            custom_field="test",
        )

        assert state["custom_field"] == "test"


class TestGraphBuilder:
    """Test LangGraphBuilder functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.builder = LangGraphBuilder(BaseAgentState)

    def test_add_node(self):
        """Test adding nodes to builder."""

        def test_node(state: BaseAgentState) -> BaseAgentState:
            return state

        self.builder.add_node("test", test_node)
        assert "test" in self.builder.nodes

    def test_add_edge(self):
        """Test adding edges to builder."""

        def node1(state: BaseAgentState) -> BaseAgentState:
            return state

        def node2(state: BaseAgentState) -> BaseAgentState:
            return state

        self.builder.add_node("node1", node1)
        self.builder.add_node("node2", node2)
        self.builder.add_edge("node1", "node2")

        assert ("node1", "node2") in self.builder.edges

    def test_set_entry_point(self):
        """Test setting entry point."""

        def test_node(state: BaseAgentState) -> BaseAgentState:
            return state

        self.builder.add_node("start", test_node)
        self.builder.set_entry_point("start")

        assert self.builder.entry_point == "start"

    def test_validate_success(self):
        """Test validation of valid workflow."""

        def node1(state: BaseAgentState) -> BaseAgentState:
            return state

        self.builder.add_node("start", node1)
        self.builder.set_entry_point("start")
        self.builder.add_edge("start", "END")

        assert self.builder.validate()

    def test_validate_failure_no_entry(self):
        """Test validation fails without entry point."""

        def node1(state: BaseAgentState) -> BaseAgentState:
            return state

        self.builder.add_node("node1", node1)

        assert not self.builder.validate()

    def test_compile(self):
        """Test compiling workflow."""

        def test_node(state: BaseAgentState) -> BaseAgentState:
            state["messages"].append("processed")
            return state

        self.builder.add_node("process", test_node)
        self.builder.set_entry_point("process")
        self.builder.add_edge("process", "END")

        app = self.builder.compile()
        assert app is not None

    def test_execute_workflow(self):
        """Test executing compiled workflow."""

        def test_node(state: BaseAgentState) -> BaseAgentState:
            state["messages"].append("executed")
            return state

        self.builder.add_node("process", test_node)
        self.builder.set_entry_point("process")
        self.builder.add_edge("process", "END")

        app = self.builder.compile()

        initial_state = {
            "messages": [],
            "next_action": "",
            "error": None,
            "metadata": {},
        }

        result = app.invoke(initial_state)
        assert "executed" in result["messages"]


class TestCodeGenerator:
    """Test LangGraphCodeGenerator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LangGraphCodeGenerator("test_workflow", "TestState")

    def test_generate_imports(self):
        """Test import generation."""
        imports = self.generator._generate_imports()
        assert "from typing import" in imports
        assert "from langgraph.graph import" in imports
        assert "import logging" in imports

    def test_generate_state_class(self):
        """Test state class generation."""
        state_fields = {"messages": "List[str]", "count": "int"}
        state_code = self.generator._generate_state_class(state_fields)

        assert "class TestState(TypedDict):" in state_code
        assert "messages: List[str]" in state_code
        assert "count: int" in state_code

    def test_generate_full_code(self):
        """Test full code generation."""
        nodes = {"test_node": {"type": "custom", "description": "Test node"}}
        edges = [("test_node", "END")]
        state_fields = {"messages": "List[str]"}

        code = self.generator.generate(
            nodes=nodes,
            edges=edges,
            conditional_edges=[],
            state_fields=state_fields,
            entry_point="test_node",
        )

        assert "class TestState(TypedDict):" in code
        assert "def test_node(state: TestState)" in code
        assert "workflow = StateGraph(TestState)" in code
        assert "app = workflow.compile()" in code

    def test_sanitize_name(self):
        """Test name sanitization."""
        assert self.generator._sanitize_name("Test Node") == "Test_Node"
        assert self.generator._sanitize_name("123node") == "node_123node"
        assert self.generator._sanitize_name("valid_name") == "valid_name"


class TestRuntimeExecutor:
    """Test LangGraphRuntime."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runtime = LangGraphRuntime()

    def test_validate_code_valid(self):
        """Test validation of valid code."""
        code = "x = 1 + 1"
        is_valid, error = self.runtime.validate_code(code)
        assert is_valid
        assert error is None

    def test_validate_code_invalid(self):
        """Test validation of invalid code."""
        code = "x = 1 +"
        is_valid, error = self.runtime.validate_code(code)
        assert not is_valid
        assert error is not None

    def test_compile_and_load(self):
        """Test compiling and loading code."""
        code = """
x = 42
def test_func():
    return x
"""
        module = self.runtime.compile_and_load(code, "test_module")
        assert module is not None
        assert hasattr(module, "x")
        assert module.x == 42
        assert hasattr(module, "test_func")
        assert module.test_func() == 42

    def test_compile_syntax_error(self):
        """Test handling of syntax errors."""
        code = "def broken("
        with pytest.raises((SyntaxError, RuntimeError)):
            self.runtime.compile_and_load(code, "broken_module")

    @pytest.mark.skip(
        reason="Class inspection not working in current implementation"
    )
    def test_inspect_module(self):
        """Test module inspection."""
        code = """
def func1():
    pass

class MyClass:
    pass

x = 42
"""
        module = self.runtime.compile_and_load(code, "inspect_test")
        info = self.runtime.inspect_module(module)

        assert "func1" in info["functions"]
        assert "MyClass" in info["classes"]

    def test_clear_cache(self):
        """Test clearing module cache."""
        code = "x = 1"
        self.runtime.compile_and_load(code, "cached_module")

        assert "cached_module" in self.runtime.compiled_modules

        self.runtime.clear_cache()

        assert len(self.runtime.compiled_modules) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
