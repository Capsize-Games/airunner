"""
Code execution tool for programmatic tool orchestration.

Allows the LLM to write Python code that orchestrates multiple tool calls,
significantly reducing round-trips and context growth for complex workflows.
"""

import json
from typing import Annotated

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.core.code_sandbox import create_sandbox_with_registry_tools
from airunner.utils.application import get_logger


logger = get_logger(__name__)


@tool(
    name="execute_code",
    category=ToolCategory.CODE,
    description=(
        "Execute Python code to process data or orchestrate multiple tools efficiently. "
        "Use this when you need to:\n"
        "- Call multiple tools in sequence or loops\n"
        "- Process and transform data between tool calls\n"
        "- Perform batch operations\n\n"
        "Available in sandbox:\n"
        "- json: JSON parsing/formatting\n"
        "- re: Regular expressions\n"
        "- All registered tools as functions\n\n"
        "Store your final output in the `result` variable."
    ),
    return_direct=False,
    defer_loading=False,
    keywords=[
        "code", "execute", "run", "script", "batch", 
        "orchestrate", "loop", "process", "transform",
    ],
    input_examples=[
        {
            "code": "# Batch search example\nresults = []\nfor query in ['topic1', 'topic2']:\n    results.append(search_web(query=query))\nresult = {'searches': results}"
        },
        {
            "code": "# Data processing example\ndata = json.loads(input_data)\nfiltered = [x for x in data if x['value'] > 10]\nresult = json.dumps(filtered)"
        },
        {
            "code": "# Pattern matching example\nimport re\nmatches = re.findall(r'\\d+', text)\nresult = {'numbers': [int(m) for m in matches]}"
        },
    ],
)
def execute_code(
    code: Annotated[str, "Python code to execute in the sandbox. Store output in 'result' variable."],
) -> str:
    """Execute Python code in a restricted sandbox.
    
    The sandbox provides:
    - Safe builtins (no file/network access)
    - json and re modules
    - All registered tools as callable functions
    
    Args:
        code: Python code to execute. Must store final output in 'result'.
        
    """
    logger.info(f"🔧 Executing code in sandbox ({len(code)} chars)")
    
    # Create sandbox with available tools
    sandbox = create_sandbox_with_registry_tools()
    
    # Execute the code
    output = sandbox.execute(code)
    
    if not output['success']:
        logger.warning(f"Sandbox execution failed: {output['error']}")
        return json.dumps({
            'success': False,
            'error': output['error'],
            'stdout': output['stdout'],
            'stderr': output['stderr'],
        }, indent=2)
    
    # Try to serialize the result
    result = output['result']
    try:
        # If result is already a string, use it directly
        if isinstance(result, str):
            result_str = result
        else:
            result_str = json.dumps(result, indent=2, default=str)
    except (TypeError, ValueError) as e:
        result_str = str(result)
    
    logger.info(f"Sandbox execution successful, result length: {len(result_str)}")
    
    return json.dumps({
        'success': True,
        'result': result_str,
        'stdout': output['stdout'],
    }, indent=2)


@tool(
    name="execute_code_with_context",
    category=ToolCategory.CODE,
    description=(
        "Execute Python code with additional context variables. "
        "Similar to execute_code but allows passing data into the sandbox."
    ),
    return_direct=False,
    defer_loading=True,  # Less commonly used
    keywords=["code", "execute", "context", "variables", "data"],
    input_examples=[
        {
            "code": "result = sum(numbers)",
            "context": {"numbers": [1, 2, 3, 4, 5]}
        },
        {
            "code": "result = {'greeting': f'Hello, {name}!'}",
            "context": {"name": "World"}
        },
    ],
)
def execute_code_with_context(
    code: Annotated[str, "Python code to execute"],
    context: Annotated[dict, "Dict of variable names to values to inject into sandbox"] = None,
) -> str:
    """Execute code with additional context variables injected.
    
    Args:
        code: Python code to execute
        context: Dict of variables to make available in the sandbox
        
    """
    logger.info(f"🔧 Executing code with context ({len(code)} chars)")
    
    sandbox = create_sandbox_with_registry_tools()
    
    # Inject context variables
    if context:
        for name, value in context.items():
            sandbox.globals[name] = value
    
    output = sandbox.execute(code)
    
    if not output['success']:
        return json.dumps({
            'success': False,
            'error': output['error'],
        }, indent=2)
    
    result = output['result']
    try:
        if isinstance(result, str):
            result_str = result
        else:
            result_str = json.dumps(result, indent=2, default=str)
    except (TypeError, ValueError):
        result_str = str(result)
    
    return json.dumps({
        'success': True,
        'result': result_str,
        'stdout': output['stdout'],
    }, indent=2)
