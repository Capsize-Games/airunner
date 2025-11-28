"""
Restricted Python execution environment for tool orchestration.

Provides a sandboxed code execution environment that allows the LLM
to write Python code that orchestrates multiple tool calls efficiently,
reducing round-trips and context growth.
"""

import ast
import builtins
import io
import json
import re
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Callable, Dict, List, Optional

from airunner.utils.application import get_logger


logger = get_logger(__name__)


# Builtins that are safe to expose in the sandbox
SAFE_BUILTINS = {
    # Core functions
    'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable',
    'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate',
    'filter', 'float', 'format', 'frozenset', 'getattr', 'hasattr',
    'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next',
    'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
    'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple',
    'type', 'vars', 'zip',
    # Exceptions (for error handling)
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'RuntimeError', 'StopIteration', 'AttributeError',
}

# AST node types that are forbidden
FORBIDDEN_AST_NODES = {
    ast.Import,
    ast.ImportFrom,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Await,
}

# Forbidden function calls
FORBIDDEN_CALLS = {
    'exec', 'eval', 'compile', '__import__', 'open',
    'input', 'breakpoint', 'globals', 'locals',
    'setattr', 'delattr', '__builtins__',
}

# Forbidden attribute access patterns
FORBIDDEN_ATTR_PATTERNS = [
    r'^_',  # Private/dunder attributes
    r'^__',  # Dunder methods
    r'__class__',
    r'__bases__',
    r'__subclasses__',
    r'__mro__',
    r'__code__',
    r'__globals__',
    r'__builtins__',
]


class SandboxSecurityError(Exception):
    """Raised when sandbox security is violated."""
    pass


class CodeValidator(ast.NodeVisitor):
    """AST visitor that validates code for sandbox execution."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        self.errors.append(
            f"Import statements are not allowed: {ast.unparse(node)}"
        )
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.errors.append(
            f"Import statements are not allowed: {ast.unparse(node)}"
        )
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        # Check for forbidden function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(
                    f"Function '{node.func.id}' is not allowed in sandbox"
                )
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check for forbidden attribute access
        attr = node.attr
        for pattern in FORBIDDEN_ATTR_PATTERNS:
            if re.match(pattern, attr):
                self.errors.append(
                    f"Access to attribute '{attr}' is not allowed"
                )
                break
        self.generic_visit(node)
    
    def validate(self, code: str) -> List[str]:
        """Validate code and return list of errors."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        self.errors = []
        self.visit(tree)
        return self.errors


class CodeSandbox:
    """Restricted Python execution environment for tool orchestration.
    
    Provides a sandboxed environment where the LLM can write Python code
    to orchestrate multiple tool calls efficiently. Results stay in the
    sandbox, reducing context growth.
    
    Example usage:
        sandbox = CodeSandbox({"search_web": search_web_func})
        result = sandbox.execute('''
            results = []
            for query in ['python', 'javascript', 'rust']:
                results.append(search_web(query=query))
            result = {'searches': results}
        ''')
    
    Attributes:
        tools: Dict mapping tool names to callable functions
        globals: Restricted global namespace for execution
    """
    
    def __init__(self, tool_functions: Dict[str, Callable]):
        """Initialize the sandbox with available tools.
        
        Args:
            tool_functions: Dict mapping tool names to their functions.
                These will be available as global functions in the sandbox.
        """
        self.tools = tool_functions
        self.globals = self._create_safe_globals()
        self.validator = CodeValidator()
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create restricted global namespace for code execution.
        
        Returns:
            Dict with safe builtins, allowed modules, and tool functions
        """
        # Create safe builtins dict
        safe_builtins = {}
        for name in SAFE_BUILTINS:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)
        
        # Create globals dict
        globals_dict: Dict[str, Any] = {
            '__builtins__': safe_builtins,
            '__name__': '__sandbox__',
            '__doc__': None,
        }
        
        # Add safe modules
        globals_dict['json'] = json
        globals_dict['re'] = re
        
        # Add tool functions as globals
        globals_dict.update(self.tools)
        
        return globals_dict
    
    def execute(
        self,
        code: str,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute code in the sandbox.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds (currently advisory)
            
        Returns:
            Dict with:
                - result: Value of 'result' variable if set
                - stdout: Captured stdout output
                - stderr: Captured stderr output
                - error: Error message if execution failed
                - success: Boolean indicating success
        """
        # Validate code first
        errors = self.validator.validate(code)
        if errors:
            return {
                'result': None,
                'stdout': '',
                'stderr': '',
                'error': 'Security validation failed:\n' + '\n'.join(errors),
                'success': False,
            }
        
        # Create isolated local namespace
        local_ns: Dict[str, Any] = {'result': None}
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = None
        error = None
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code
                exec(code, self.globals, local_ns)
                result = local_ns.get('result')
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Sandbox execution error: {error}")
        
        return {
            'result': result,
            'stdout': stdout_capture.getvalue(),
            'stderr': stderr_capture.getvalue(),
            'error': error,
            'success': error is None,
        }
    
    def add_tool(self, name: str, func: Callable) -> None:
        """Add a tool function to the sandbox.
        
        Args:
            name: Name to use in sandbox
            func: Tool function
        """
        self.tools[name] = func
        self.globals[name] = func
    
    def remove_tool(self, name: str) -> None:
        """Remove a tool from the sandbox.
        
        Args:
            name: Tool name to remove
        """
        self.tools.pop(name, None)
        self.globals.pop(name, None)


def create_sandbox_with_registry_tools() -> CodeSandbox:
    """Create a sandbox with tools from the registry.
    
    Includes tools that allow code_execution caller or have no restrictions.
    
    Returns:
        Configured CodeSandbox instance
    """
    from airunner.components.llm.core.tool_registry import ToolRegistry
    
    code_tools: Dict[str, Callable] = {}
    
    for name, info in ToolRegistry.all().items():
        # Include if no restrictions or if code_execution is allowed
        if not info.allowed_callers or 'code_execution' in info.allowed_callers:
            code_tools[name] = info.func
    
    return CodeSandbox(code_tools)
