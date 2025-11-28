"""
Tool schema utilities for generating OpenAI-compatible function schemas.

Provides utilities for extracting parameter information and generating
tool schemas with examples for better LLM understanding.
"""

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, get_type_hints, get_origin, get_args

from airunner.components.llm.core.tool_registry import ToolInfo
from airunner.utils.application import get_logger


logger = get_logger(__name__)


def python_type_to_json_type(python_type: type) -> str:
    """Convert Python type to JSON Schema type.
    
    Args:
        python_type: Python type annotation
        
    Returns:
        JSON Schema type string
    """
    # Handle Optional types
    origin = get_origin(python_type)
    if origin is not None:
        args = get_args(python_type)
        # Optional[X] is Union[X, None]
        if type(None) in args:
            # Get the non-None type
            non_none_types = [t for t in args if t is not type(None)]
            if non_none_types:
                return python_type_to_json_type(non_none_types[0])
        # Handle List, Dict, etc.
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
    
    # Basic type mapping
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }
    
    return type_map.get(python_type, "string")


def get_annotated_description(annotation: Any) -> Optional[str]:
    """Extract description from Annotated type hint.
    
    Args:
        annotation: Type annotation (possibly Annotated)
        
    Returns:
        Description string if found, None otherwise
    """
    # Check if it's an Annotated type
    origin = get_origin(annotation)
    
    try:
        from typing import Annotated
        if origin is Annotated:
            args = get_args(annotation)
            # Second argument should be the description
            if len(args) >= 2 and isinstance(args[1], str):
                return args[1]
    except ImportError:
        pass
    
    return None


def get_base_type(annotation: Any) -> type:
    """Extract base type from Annotated or Optional.
    
    Args:
        annotation: Type annotation
        
    Returns:
        Base Python type
    """
    origin = get_origin(annotation)
    
    if origin is not None:
        args = get_args(annotation)
        
        # Handle Annotated
        try:
            from typing import Annotated
            if origin is Annotated:
                return get_base_type(args[0])
        except ImportError:
            pass
        
        # Handle Optional (Union with None)
        if type(None) in args:
            non_none_types = [t for t in args if t is not type(None)]
            if non_none_types:
                return get_base_type(non_none_types[0])
        
        # Return the origin for generic types
        return origin
    
    return annotation


def get_function_schema(func: Callable) -> Dict[str, Any]:
    """Generate parameter schema from function signature.
    
    Args:
        func: Function to analyze
        
    Returns:
        Dict with properties and required lists
    """
    sig = inspect.signature(func)
    
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:
        hints = {}
    
    properties: Dict[str, Dict[str, Any]] = {}
    required: List[str] = []
    
    for param_name, param in sig.parameters.items():
        # Skip special parameters
        if param_name in ("self", "cls", "api", "agent"):
            continue
        
        annotation = hints.get(param_name, str)
        
        # Get description from Annotated
        description = get_annotated_description(annotation)
        
        # Get base type for JSON schema
        base_type = get_base_type(annotation)
        json_type = python_type_to_json_type(base_type)
        
        prop_schema: Dict[str, Any] = {
            "type": json_type,
        }
        
        if description:
            prop_schema["description"] = description
        
        properties[param_name] = prop_schema
        
        # Check if required (no default value)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "properties": properties,
        "required": required,
    }


def get_tool_schema_with_examples(tool_info: ToolInfo) -> Dict[str, Any]:
    """Generate OpenAI-compatible function schema with examples.
    
    Args:
        tool_info: Tool metadata
        
    Returns:
        Complete tool schema dict with input_examples if available
    """
    param_schema = get_function_schema(tool_info.func)
    
    schema = {
        "name": tool_info.name,
        "description": tool_info.description,
        "input_schema": {
            "type": "object",
            "properties": param_schema["properties"],
            "required": param_schema["required"],
        },
    }
    
    if tool_info.input_examples:
        schema["input_examples"] = tool_info.input_examples
    
    return schema


def format_tool_for_llm(tool_info: ToolInfo, include_examples: bool = True) -> str:
    """Format tool information as a string for LLM context.
    
    Args:
        tool_info: Tool metadata
        include_examples: Whether to include usage examples
        
    Returns:
        Formatted tool description string
    """
    lines = [
        f"Tool: {tool_info.name}",
        f"Category: {tool_info.category.value}",
        f"Description: {tool_info.description}",
    ]
    
    # Add parameter info
    param_schema = get_function_schema(tool_info.func)
    if param_schema["properties"]:
        lines.append("Parameters:")
        for param_name, param_info in param_schema["properties"].items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            required = "(required)" if param_name in param_schema["required"] else "(optional)"
            lines.append(f"  - {param_name}: {param_type} {required}")
            if param_desc:
                lines.append(f"      {param_desc}")
    
    # Add examples if available
    if include_examples and tool_info.input_examples:
        lines.append("Examples:")
        for i, example in enumerate(tool_info.input_examples, 1):
            lines.append(f"  {i}. {json.dumps(example)}")
    
    return "\n".join(lines)
