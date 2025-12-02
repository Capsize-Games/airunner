"""
System and application control tools.

Tools for controlling the application, managing files, and system operations.
"""

import os
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory


@tool(
    name="quit_application",
    category=ToolCategory.SYSTEM,
    description="Quit the AI Runner application",
    return_direct=True,
    requires_api=True,
    defer_loading=False,  # Essential tool - always available
)
def quit_application(api: Any = None) -> str:
    """Quit the application."""
    api.quit_application()
    return "Quitting application..."


@tool(
    name="toggle_tts",
    category=ToolCategory.SYSTEM,
    description="Enable or disable text-to-speech",
    return_direct=True,
    requires_api=True,
    defer_loading=False,  # Essential tool - always available
)
def toggle_tts(
    enabled: Annotated[bool, "True to enable, False to disable"],
    api: Any = None,
) -> str:
    """Toggle text-to-speech."""
    api.tts.toggle(enabled)
    status = "enabled" if enabled else "disabled"
    return f"Text-to-speech {status}"


@tool(
    name="list_directory",
    category=ToolCategory.FILE,
    description="List files and directories in a path",
    return_direct=False,
    requires_api=False,
)
def list_directory(
    path: Annotated[str, "Directory path to list"],
) -> str:
    """List directory contents."""
    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        return f"Error: Path does not exist: {abs_path}"

    if not os.path.isdir(abs_path):
        return f"Error: Not a directory: {abs_path}"

    try:
        items = os.listdir(abs_path)
        return "\n".join(sorted(items))
    except PermissionError:
        return f"Error: Permission denied: {abs_path}"
    except Exception as e:
        return f"Error listing directory: {e}"


@tool(
    name="read_file",
    category=ToolCategory.FILE,
    description="Read contents of a text file",
    return_direct=False,
    requires_api=False,
)
def read_file(
    path: Annotated[str, "File path to read"],
) -> str:
    """Read file contents."""
    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        return f"Error: File does not exist: {abs_path}"

    if not os.path.isfile(abs_path):
        return f"Error: Not a file: {abs_path}"

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except PermissionError:
        return f"Error: Permission denied: {abs_path}"
    except UnicodeDecodeError:
        return f"Error: Cannot read file (binary or unsupported encoding): {abs_path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool(
    name="write_file",
    category=ToolCategory.FILE,
    description="Write content to a text file",
    return_direct=True,
    requires_api=False,
)
def write_file(
    path: Annotated[str, "File path to write to"],
    content: Annotated[str, "Content to write"],
) -> str:
    """Write content to file."""
    abs_path = os.path.abspath(path)

    try:
        # Create parent directories if needed
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote to: {abs_path}"
    except PermissionError:
        return f"Error: Permission denied: {abs_path}"
    except Exception as e:
        return f"Error writing file: {e}"
