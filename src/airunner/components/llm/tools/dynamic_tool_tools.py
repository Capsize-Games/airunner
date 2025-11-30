"""Dynamic tool creation for LLM-generated tools.

This module allows the LLM to create new tools at runtime that persist
for the session (or optionally to the database for permanent storage).

Security: All tool code is validated through the CodeSandbox validator
before registration to prevent dangerous operations.
"""

import ast
import json
import inspect
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

from airunner.components.llm.core.tool_registry import (
    tool,
    ToolCategory,
    ToolRegistry,
    ToolInfo,
)
from airunner.components.llm.core.code_sandbox import CodeValidator
from airunner.utils.application import get_logger


logger = get_logger(__name__)


# Store for dynamically created tools (session-scoped)
_dynamic_tools: Dict[str, Dict[str, Any]] = {}


def get_dynamic_tools() -> Dict[str, Dict[str, Any]]:
    """Get all dynamically created tools."""
    return dict(_dynamic_tools)


def clear_dynamic_tools() -> None:
    """Clear all dynamic tools (useful for testing)."""
    global _dynamic_tools
    _dynamic_tools.clear()


def _create_function_from_code(
    name: str,
    parameters: Dict[str, Dict[str, Any]],
    code: str,
    return_type: str = "str",
) -> Callable:
    """Create a callable function from code string.
    
    Args:
        name: Function name
        parameters: Dict mapping param names to {"type": str, "description": str, "default": Any}
        code: Python code that sets 'result' variable
        return_type: Expected return type
        
    """
    # Build parameter signature
    param_parts = []
    for param_name, param_info in parameters.items():
        param_type = param_info.get("type", "str")
        default = param_info.get("default")
        
        if default is not None:
            param_parts.append(f"{param_name}={repr(default)}")
        else:
            param_parts.append(param_name)
    
    param_str = ", ".join(param_parts)
    
    # Create the function dynamically
    func_code = f'''
def {name}({param_str}):
    """Dynamically created tool."""
    result = None
    {code}
    return result
'''
    
    # Execute to create function
    local_ns: Dict[str, Any] = {}
    exec(func_code, {"__builtins__": __builtins__}, local_ns)
    
    return local_ns[name]


def _validate_tool_code(code: str) -> List[str]:
    """Validate tool code for safety.
    
    Args:
        code: Python code to validate
        
    """
    validator = CodeValidator()
    errors = validator.validate(code)
    
    # Additional checks for tool creation
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # No class definitions in tools
            if isinstance(node, ast.ClassDef):
                errors.append("Tool code cannot define classes")
            # No async
            if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                errors.append("Tool code cannot use async/await")
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
    
    return errors


@tool(
    name="create_dynamic_tool",
    category=ToolCategory.SYSTEM,
    description=(
        "Create a new tool that can be used in future interactions. "
        "Use this to extend your capabilities by creating reusable functions. "
        "The tool code runs in a restricted sandbox - no file/network access."
    ),
    keywords=["tool", "create", "function", "define", "extend", "capability"],
    input_examples=[
        {
            "name": "count_words",
            "description": "Count words in text",
            "parameters_json": '{"text": {"type": "str", "description": "Text to count words in"}}',
            "code": "result = len(text.split())",
        },
        {
            "name": "extract_emails",
            "description": "Extract email addresses from text",
            "parameters_json": '{"text": {"type": "str", "description": "Text to search"}}',
            "code": "import re; result = re.findall(r'[\\w.+-]+@[\\w-]+\\.[\\w.-]+', text)",
        },
    ],
)
def create_dynamic_tool(
    name: str,
    description: str,
    parameters_json: str,
    code: str,
    category: str = "system",
) -> str:
    """Create a new tool dynamically.
    
    The tool will be available for use in subsequent interactions.
    Code runs in a restricted environment - no file or network access.
    Store your result in the 'result' variable.
    
    Args:
        name: Unique tool name (lowercase, underscores allowed)
        description: What the tool does
        parameters_json: JSON object mapping param names to {type, description, default}
        code: Python code that sets 'result' variable. Parameters are available as variables.
        category: Tool category (system, code, research, etc.)
        
    """
    logger.info(f"Creating dynamic tool: {name}")
    
    # Validate name
    if not name.isidentifier():
        return f"Error: Invalid tool name '{name}'. Use lowercase letters and underscores."
    
    if name in ToolRegistry.all():
        return f"Error: Tool '{name}' already exists. Choose a different name."
    
    # Parse parameters
    try:
        parameters = json.loads(parameters_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid parameters JSON: {e}"
    
    # Validate code
    errors = _validate_tool_code(code)
    if errors:
        return f"Error: Code validation failed:\n" + "\n".join(f"- {e}" for e in errors)
    
    # Map category string to enum
    try:
        tool_category = ToolCategory(category.lower())
    except ValueError:
        tool_category = ToolCategory.SYSTEM
    
    try:
        # Create the function
        func = _create_function_from_code(name, parameters, code)
        
        # Register with ToolRegistry
        info = ToolInfo(
            func=func,
            name=name,
            category=tool_category,
            description=description,
            return_direct=False,
            requires_agent=False,
            requires_api=False,
            defer_loading=False,
            keywords=["dynamic", "custom", "user-created"],
        )
        ToolRegistry._tools[name] = info
        
        if tool_category not in ToolRegistry._categories:
            ToolRegistry._categories[tool_category] = []
        ToolRegistry._categories[tool_category].append(info)
        
        # Store in dynamic tools registry
        _dynamic_tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "code": code,
            "category": category,
        }
        
        logger.info(f"Successfully created dynamic tool: {name}")
        
        # Build parameter description
        param_desc = []
        for pname, pinfo in parameters.items():
            ptype = pinfo.get("type", "any")
            pdesc = pinfo.get("description", "")
            param_desc.append(f"  - {pname} ({ptype}): {pdesc}")
        
        return f"""✅ Tool '{name}' created successfully!

Description: {description}
Category: {tool_category.value}
Parameters:
{chr(10).join(param_desc) if param_desc else "  (none)"}

You can now use this tool by calling: {name}(...)"""
        
    except Exception as e:
        logger.error(f"Failed to create dynamic tool: {e}", exc_info=True)
        return f"Error creating tool: {str(e)}"


@tool(
    name="list_dynamic_tools",
    category=ToolCategory.SYSTEM,
    description="List all dynamically created tools in this session.",
    keywords=["tools", "list", "dynamic", "custom"],
)
def list_dynamic_tools() -> str:
    """List all tools created with create_dynamic_tool.
    
    """
    if not _dynamic_tools:
        return "No dynamic tools have been created in this session."
    
    lines = ["**Dynamic Tools:**\n"]
    for name, info in _dynamic_tools.items():
        lines.append(f"- **{name}**: {info['description']}")
        params = info.get("parameters", {})
        if params:
            param_strs = [f"{k}: {v.get('type', 'any')}" for k, v in params.items()]
            lines.append(f"  Parameters: ({', '.join(param_strs)})")
    
    return "\n".join(lines)


@tool(
    name="delete_dynamic_tool",
    category=ToolCategory.SYSTEM,
    description="Delete a dynamically created tool.",
    keywords=["tool", "delete", "remove", "dynamic"],
)
def delete_dynamic_tool(name: str) -> str:
    """Delete a dynamic tool by name.
    
    Args:
        name: Name of the tool to delete
        
    """
    if name not in _dynamic_tools:
        return f"Error: Dynamic tool '{name}' not found."
    
    # Remove from dynamic tools registry
    del _dynamic_tools[name]
    
    # Remove from ToolRegistry
    if name in ToolRegistry._tools:
        info = ToolRegistry._tools[name]
        del ToolRegistry._tools[name]
        
        # Remove from category list
        if info.category in ToolRegistry._categories:
            ToolRegistry._categories[info.category] = [
                t for t in ToolRegistry._categories[info.category]
                if t.name != name
            ]
    
    logger.info(f"Deleted dynamic tool: {name}")
    return f"✅ Tool '{name}' deleted successfully."


# Export tools
DYNAMIC_TOOL_TOOLS = [
    create_dynamic_tool,
    list_dynamic_tools,
    delete_dynamic_tool,
]
