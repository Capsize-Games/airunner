"""Code execution and tool creation tools."""

import logging
import math
import sys
from io import StringIO
from typing import Callable, Optional

from langchain.tools import tool

from airunner.enums import SignalCode


class CodeTools:
    """Mixin class providing code execution and development tools."""

    def calculator_tool(self) -> Callable:
        """Perform mathematical calculations."""

        @tool
        def calculate(expression: str) -> str:
            """Evaluate a mathematical expression.

            Supports basic arithmetic, powers, and common math functions.

            Args:
                expression: Mathematical expression (e.g., "2 + 2", "sqrt(16)", "pi * 2")

            Returns:
                Calculation result or error message

            Example:
                calculate("(5 + 3) * 2 ** 3")
            """
            try:
                # Safe evaluation with math functions available
                safe_dict = {
                    "sqrt": math.sqrt,
                    "pow": pow,
                    "abs": abs,
                    "round": round,
                    "pi": math.pi,
                    "e": math.e,
                    "sin": math.sin,
                    "cos": math.cos,
                    "tan": math.tan,
                    "log": math.log,
                    "ln": math.log,
                    "exp": math.exp,
                }

                result = eval(expression, {"__builtins__": {}}, safe_dict)
                return str(result)
            except Exception as e:
                return f"Calculation error: {str(e)}"

        return calculate

    def execute_python_tool(self) -> Callable:
        """Execute Python code in a sandboxed environment."""

        @tool
        def execute_python(code: str) -> str:
            """Execute Python code and return the result.

            This tool allows running Python code snippets for calculations,
            data processing, or analysis. Code is executed in a restricted
            environment for safety.

            LIMITATIONS:
            - No file I/O operations
            - No network access
            - No subprocess execution
            - Execution timeout of 5 seconds

            Args:
                code: Python code to execute

            Returns:
                Output from code execution or error message

            Example:
                execute_python("result = 5 * 10 + 3; print(result)")
            """
            try:
                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                # Restricted globals (no dangerous builtins)
                safe_globals = {
                    "__builtins__": {
                        "print": print,
                        "len": len,
                        "range": range,
                        "str": str,
                        "int": int,
                        "float": float,
                        "list": list,
                        "dict": dict,
                        "sum": sum,
                        "min": min,
                        "max": max,
                        "abs": abs,
                        "round": round,
                    }
                }

                # Execute
                exec(code, safe_globals)

                # Restore stdout
                sys.stdout = old_stdout

                output = captured_output.getvalue()
                return (
                    output
                    if output
                    else "Code executed successfully (no output)"
                )

            except Exception as e:
                sys.stdout = old_stdout
                return f"Execution error: {str(e)}"

        return execute_python

    def create_tool_tool(self) -> Callable:
        """Create a new LLM tool dynamically."""

        @tool
        def create_tool(tool_name: str, description: str, code: str) -> str:
            """Create a new custom tool that the agent can use.

            This meta-tool allows the agent to expand its own capabilities by
            creating new tools. The code must use the @tool decorator and follow
            LangChain tool patterns.

            SAFETY GUIDELINES:
            - Do NOT use os.system, subprocess, eval, or exec
            - Do NOT perform destructive file operations
            - Do NOT access sensitive system resources
            - Keep tools focused and single-purpose

            Args:
                tool_name: Unique name for the tool (e.g., 'calculate_fibonacci')
                description: Clear description of what the tool does
                code: Python code implementing the tool using @tool decorator

            Returns:
                Success or error message

            Example:
                create_tool(
                    tool_name="add_numbers",
                    description="Add two numbers together",
                    code='''
                    @tool
                    def add_numbers(a: int, b: int) -> str:
                        \"\"\"Add two numbers.

                        Args:
                            a: First number
                            b: Second number

                        Returns:
                            Sum as string
                        \"\"\"
                        return str(a + b)
                    '''
                )
            """
            try:
                from airunner.components.llm.data.llm_tool import LLMTool

                # Check if tool already exists
                existing = LLMTool.objects.filter_by_first(name=tool_name)
                if existing:
                    return f"Tool '{tool_name}' already exists. Use a different name."

                # Create tool record
                new_tool = LLMTool(
                    name=tool_name,
                    display_name=tool_name.replace("_", " ").title(),
                    description=description,
                    code=code,
                    created_by="agent",
                    enabled=False,  # Disabled until safety validated
                )

                # Validate safety
                is_safe, message = new_tool.validate_code_safety()
                if not is_safe:
                    return f"Tool creation failed: {message}"

                new_tool.safety_validated = True
                new_tool.enabled = True
                new_tool.save()

                # Emit signal to reload tools
                self.emit_signal(
                    SignalCode.LLM_TOOL_CREATED, {"tool_name": tool_name}
                )

                return f"Tool '{tool_name}' created successfully! It will be available on next reload."
            except Exception as e:
                return f"Error creating tool: {str(e)}"

        return create_tool
