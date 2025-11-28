"""
Unit tests for the code sandbox.

Tests security validation, code execution, and tool injection.
"""

import pytest
from unittest.mock import MagicMock

from airunner.components.llm.core.code_sandbox import (
    CodeSandbox,
    CodeValidator,
    SandboxSecurityError,
    create_sandbox_with_registry_tools,
)
from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
    tool,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


class TestCodeValidator:
    """Tests for the CodeValidator AST checker."""

    def test_allows_safe_code(self):
        """Safe code should pass validation."""
        validator = CodeValidator()
        
        code = """
result = []
for i in range(10):
    result.append(i * 2)
result = sum(result)
"""
        errors = validator.validate(code)
        
        assert errors == []

    def test_blocks_imports(self):
        """Import statements should be blocked."""
        validator = CodeValidator()
        
        code = "import os"
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "Import" in errors[0] or "import" in errors[0].lower()

    def test_blocks_from_imports(self):
        """From imports should be blocked."""
        validator = CodeValidator()
        
        code = "from os import path"
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "Import" in errors[0] or "import" in errors[0].lower()

    def test_blocks_exec(self):
        """exec() calls should be blocked."""
        validator = CodeValidator()
        
        code = 'exec("print(1)")'
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "exec" in errors[0].lower()

    def test_blocks_eval(self):
        """eval() calls should be blocked."""
        validator = CodeValidator()
        
        code = 'eval("1+1")'
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "eval" in errors[0].lower()

    def test_blocks_dunder_access(self):
        """Access to dunder attributes should be blocked."""
        validator = CodeValidator()
        
        code = "x = obj.__class__"
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "__class__" in errors[0]

    def test_blocks_private_access(self):
        """Access to private attributes should be blocked."""
        validator = CodeValidator()
        
        code = "x = obj._private"
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "_private" in errors[0]

    def test_reports_syntax_errors(self):
        """Syntax errors should be reported."""
        validator = CodeValidator()
        
        code = "def broken("
        errors = validator.validate(code)
        
        assert len(errors) > 0
        assert "Syntax" in errors[0] or "syntax" in errors[0].lower()


class TestCodeSandbox:
    """Tests for the CodeSandbox execution environment."""

    def test_execute_simple_code(self):
        """Simple code should execute successfully."""
        sandbox = CodeSandbox({})
        
        output = sandbox.execute("result = 2 + 2")
        
        assert output['success'] is True
        assert output['result'] == 4
        assert output['error'] is None

    def test_execute_with_loops(self):
        """Loops should work in sandbox."""
        sandbox = CodeSandbox({})
        
        code = """
result = []
for i in range(5):
    result.append(i ** 2)
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result'] == [0, 1, 4, 9, 16]

    def test_execute_with_json(self):
        """json module should be available."""
        sandbox = CodeSandbox({})
        
        code = """
data = json.dumps({'key': 'value'})
result = json.loads(data)
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result'] == {'key': 'value'}

    def test_execute_with_re(self):
        """re module should be available."""
        sandbox = CodeSandbox({})
        
        code = """
import re  # This won't work, but re is pre-injected
text = 'abc123def456'
result = re.findall(r'\\d+', text)
"""
        # The import will fail, test that re is available another way
        code2 = """
text = 'abc123def456'
result = re.findall(r'\\d+', text)
"""
        output = sandbox.execute(code2)
        
        assert output['success'] is True
        assert output['result'] == ['123', '456']

    def test_execute_captures_stdout(self):
        """stdout should be captured."""
        sandbox = CodeSandbox({})
        
        code = """
print("Hello, sandbox!")
result = "done"
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert "Hello, sandbox!" in output['stdout']

    def test_execute_with_tool(self):
        """Injected tools should be callable."""
        def mock_tool(query: str) -> str:
            return f"Result: {query}"
        
        sandbox = CodeSandbox({"search": mock_tool})
        
        code = """
result = search(query="test query")
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result'] == "Result: test query"

    def test_execute_batch_tool_calls(self):
        """Multiple tool calls in a loop should work."""
        call_count = 0
        
        def counting_tool(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        sandbox = CodeSandbox({"double": counting_tool})
        
        code = """
result = [double(x=i) for i in range(5)]
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result'] == [0, 2, 4, 6, 8]
        assert call_count == 5

    def test_rejects_imports(self):
        """Import statements should fail validation."""
        sandbox = CodeSandbox({})
        
        code = "import os"
        output = sandbox.execute(code)
        
        assert output['success'] is False
        assert "Import" in output['error'] or "import" in output['error'].lower()

    def test_rejects_exec(self):
        """exec() should fail validation."""
        sandbox = CodeSandbox({})
        
        code = 'exec("print(1)")'
        output = sandbox.execute(code)
        
        assert output['success'] is False
        assert "exec" in output['error'].lower()

    def test_handles_runtime_errors(self):
        """Runtime errors should be caught and reported."""
        sandbox = CodeSandbox({})
        
        code = """
x = 1 / 0
"""
        output = sandbox.execute(code)
        
        assert output['success'] is False
        assert "ZeroDivision" in output['error']

    def test_add_tool(self):
        """Adding tools after initialization should work."""
        sandbox = CodeSandbox({})
        
        def new_tool() -> str:
            return "new tool result"
        
        sandbox.add_tool("my_tool", new_tool)
        
        code = "result = my_tool()"
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result'] == "new tool result"

    def test_remove_tool(self):
        """Removing tools should work."""
        def my_tool() -> str:
            return "result"
        
        sandbox = CodeSandbox({"my_tool": my_tool})
        sandbox.remove_tool("my_tool")
        
        code = "result = my_tool()"
        output = sandbox.execute(code)
        
        assert output['success'] is False
        # Should fail because my_tool is not defined

    def test_builtins_available(self):
        """Safe builtins should be available."""
        sandbox = CodeSandbox({})
        
        code = """
result = {
    'sum': sum([1, 2, 3]),
    'len': len([1, 2, 3]),
    'max': max([1, 2, 3]),
    'sorted': sorted([3, 1, 2]),
    'list': list(range(3)),
    'dict': dict(a=1, b=2),
    'str': str(123),
    'int': int('42'),
    'float': float('3.14'),
    'bool': bool(1),
    'isinstance': isinstance([], list),
}
"""
        output = sandbox.execute(code)
        
        assert output['success'] is True
        assert output['result']['sum'] == 6
        assert output['result']['len'] == 3
        assert output['result']['sorted'] == [1, 2, 3]


class TestCreateSandboxWithRegistryTools:
    """Tests for create_sandbox_with_registry_tools."""

    def test_creates_sandbox_with_tools(self):
        """Should create sandbox with registered tools."""
        # Register a test tool
        @tool(
            name="test_sandbox_tool",
            category=ToolCategory.SYSTEM,
            description="A test tool",
        )
        def test_tool(x: int) -> int:
            return x * 2
        
        sandbox = create_sandbox_with_registry_tools()
        
        assert "test_sandbox_tool" in sandbox.tools

    def test_respects_allowed_callers(self):
        """Should respect allowed_callers restrictions."""
        # Register a tool that only allows code_execution
        @tool(
            name="code_only_tool",
            category=ToolCategory.CODE,
            description="A code-only tool",
            allowed_callers=["code_execution"],
        )
        def code_only() -> str:
            return "code only"
        
        # Register a tool with other restrictions
        @tool(
            name="other_caller_tool",
            category=ToolCategory.CODE,
            description="A tool with other callers",
            allowed_callers=["other_context"],
        )
        def other_only() -> str:
            return "other only"
        
        sandbox = create_sandbox_with_registry_tools()
        
        # code_only_tool should be included
        assert "code_only_tool" in sandbox.tools
        # other_caller_tool should not be included
        assert "other_caller_tool" not in sandbox.tools
