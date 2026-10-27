"""Schema-formatting helpers for GPT-OSS tool prompts."""

import json
from typing import Any, Dict, List


def format_gpt_oss_namespace(adapter: Any) -> str:
    """Format bound tools as a Harmony functions namespace."""
    shared_defs: Dict[str, Dict[str, Any]] = {}
    lines = ["namespace functions {", ""]

    for tool in adapter.tools or []:
        function = tool.get("function", tool)
        parameters = function.get("parameters", {})
        shared_defs.update(parameters.get("$defs", {}))

    if shared_defs:
        lines.extend(format_gpt_oss_shared_definitions(shared_defs))
        lines.append("")

    for tool in adapter.tools or []:
        function = tool.get("function", tool)
        lines.extend(format_gpt_oss_tool(function))
        lines.append("")

    while lines and not lines[-1]:
        lines.pop()
    lines.append("} // namespace functions")
    return "\n".join(lines)


def format_gpt_oss_shared_definitions(
    shared_defs: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Format shared schema definitions for Harmony tool prompts."""
    lines: List[str] = []
    for name, schema in shared_defs.items():
        type_definition = format_gpt_oss_type(schema, 1)
        lines.append(f"type {name} = {type_definition};")
    return lines


def format_gpt_oss_tool(tool: Dict[str, Any]) -> List[str]:
    """Format one tool schema as a Harmony type definition."""
    description = tool.get("description", "")
    parameters = tool.get("parameters", {})
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))
    name = tool.get("name", "unknown_tool")
    lines = [f"// {description}" if description else "// Tool"]

    if not properties:
        lines.append(f"type {name} = () => any;")
        return lines

    lines.append(f"type {name} = (_: {{")
    for param_name, schema in properties.items():
        param_description = schema.get("description", "")
        if param_description:
            lines.append(f"// {param_description}")
        param_type = format_gpt_oss_type(schema, 1)
        optional = "" if param_name in required else "?"
        lines.append(f"{param_name}{optional}: {param_type},")
    lines.append("}) => any;")
    return lines


def format_gpt_oss_type(
    schema: Dict[str, Any],
    indent_level: int = 0,
) -> str:
    """Convert a JSON schema fragment to a Harmony-style type."""
    if not isinstance(schema, dict):
        return "any"
    ref_type = _referenced_type(schema)
    if ref_type is not None:
        return ref_type
    union_type = _union_type(schema, indent_level)
    if union_type is not None:
        return union_type
    if "enum" in schema:
        return _enum_type(schema)
    return _primitive_schema_type(schema, indent_level)


def _referenced_type(schema: Dict[str, Any]) -> str | None:
    """Return one referenced type name when the schema uses $ref."""
    ref = schema.get("$ref")
    if ref is None:
        return None
    return str(ref).rsplit("/", 1)[-1]


def _union_type(
    schema: Dict[str, Any],
    indent_level: int,
) -> str | None:
    """Return one union type for anyOf/oneOf schemas."""
    variants = schema.get("anyOf") or schema.get("oneOf")
    if not variants:
        return None
    return " | ".join(
        format_gpt_oss_type(variant, indent_level) for variant in variants
    )


def _enum_type(schema: Dict[str, Any]) -> str:
    """Return one enum type representation."""
    return " | ".join(json.dumps(value) for value in schema.get("enum", []))


def _primitive_schema_type(
    schema: Dict[str, Any],
    indent_level: int,
) -> str:
    """Return one primitive, array, or object type representation."""
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(str(item) for item in schema_type)
    if schema_type == "array":
        return _array_item_type(schema, indent_level)
    if schema_type == "object":
        return format_gpt_oss_object_type(schema, indent_level + 1)
    if isinstance(schema_type, str):
        return schema_type
    return "any"


def _array_item_type(schema: Dict[str, Any], indent_level: int) -> str:
    """Return one array item type representation."""
    item_type = format_gpt_oss_type(
        schema.get("items", {}),
        indent_level + 1,
    )
    return f"Array<{item_type}>"


def format_gpt_oss_object_type(
    schema: Dict[str, Any],
    indent_level: int,
) -> str:
    """Format one JSON object schema as an inline type block."""
    properties = schema.get("properties", {})
    if not properties:
        return "object"

    required = set(schema.get("required", []))
    indent = "  " * indent_level
    closing_indent = "  " * max(indent_level - 1, 0)
    lines = ["{"]
    for name, child in properties.items():
        child_type = format_gpt_oss_type(child, indent_level + 1)
        optional = "" if name in required else "?"
        lines.append(f"{indent}{name}{optional}: {child_type},")
    lines.append(f"{closing_indent}}}")
    return "\n".join(lines)
