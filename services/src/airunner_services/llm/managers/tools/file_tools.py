"""File system and document tools."""

import os
from typing import Callable

from langchain_core.tools import tool

from airunner_services.tools.base_tool import BaseTool


class FileTools(BaseTool):
    """Mixin class providing file system and document management tools."""

    def _granted_base(self) -> str:
        """Return the canonical base directory tools may touch."""
        base = os.path.expanduser(self.path_settings.base_path)
        return os.path.realpath(base)

    def _resolve_tool_path(
        self, raw_path: str, root: str | None = None
    ) -> str:
        """Resolve one tool-supplied path under the granted roots.

        Relative paths resolve against ``root`` (default: the base
        path); absolute paths are allowed only when they already sit
        under it. Anything else (``..`` escapes, symlinks out,
        absolute outsiders) raises ``ValueError`` so the tool returns
        an error instead of touching the path.
        """
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError("Access denied: path must be nonempty")
        base = self._granted_base()
        anchor = os.path.realpath(root) if root is not None else base
        if anchor != base and not anchor.startswith(base + os.sep):
            raise ValueError(
                "Access denied: path is outside the granted roots"
            )
        candidate = (
            raw_path
            if os.path.isabs(raw_path)
            else os.path.join(anchor, raw_path)
        )
        resolved = os.path.realpath(candidate)
        if resolved != anchor and not resolved.startswith(anchor + os.sep):
            raise ValueError(
                "Access denied: path is outside the granted roots"
            )
        return resolved

    def list_files_tool(self) -> Callable:
        """List files in a directory."""

        _resolve = self._resolve_tool_path

        @tool
        def list_files(directory: str) -> str:
            """List files in a directory.

            Args:
                directory: Path to directory (confined under granted roots)

            Returns:
                List of files or error message
            """
            try:
                resolved = _resolve(directory)
                if not os.path.isdir(resolved):
                    return f"Directory not found: {directory}"

                files = os.listdir(resolved)
                return "\n".join(files) if files else "Directory is empty"
            except ValueError as e:
                return f"Error listing files: {str(e)}"
            except Exception as e:
                return f"Error listing files: {str(e)}"

        return list_files

    def read_file_tool(self) -> Callable:
        """Read content from a file."""

        _resolve = self._resolve_tool_path

        @tool
        def read_file(file_path: str) -> str:
            """Read and return the contents of a file.

            Useful for analyzing code, reading documents, or accessing data files.

            Args:
                file_path: Path to the file to read.
                    Confined under the granted roots.

            Returns:
                File contents or error message
            """
            try:
                resolved = _resolve(file_path)
                if not os.path.exists(resolved):
                    return f"File not found: {file_path}"

                with open(resolved, "r") as f:
                    content = f.read()

                # Limit output size
                if len(content) > 10000:
                    content = (
                        content[:10000]
                        + f"\n\n... (truncated, file is {len(content)} characters)"
                    )

                return content
            except Exception as e:
                return f"Error reading file: {str(e)}"

        return read_file

    def write_code_tool(self) -> Callable:
        """Write and save Python code to a file."""

        _resolve = self._resolve_tool_path

        @tool
        def write_code(
            file_path: str, code_content: str, description: str = ""
        ) -> str:
            """Write Python code to a file and open it in the code editor.

            This tool allows creating new Python files or modifying existing ones.
            The code will be written to the specified path and opened in the editor.

            Args:
                file_path: Relative path where code should be saved (e.g., 'tools/my_tool.py')
                code_content: The Python code to write
                description: Optional description of what the code does

            Returns:
                Confirmation message
            """
            try:
                # Ensure it's a Python file
                if not file_path.endswith(".py"):
                    file_path += ".py"

                # Build full path confined under user_code: absolute
                # outsiders and `..` escapes resolve outside the code
                # root and are rejected instead of written.
                full_path = _resolve(
                    file_path,
                    root=os.path.join(self._granted_base(), "user_code"),
                )

                # Create directory if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # Write code
                with open(full_path, "w") as f:
                    if description:
                        f.write(f'"""{description}"""\n\n')
                    f.write(code_content)

                # Signal to open in editor (if implemented)
                self.dispatch_tool_action(
                    "open_code_editor",
                    {"file_path": full_path, "content": code_content},
                )

                return f"Code written to {file_path}"
            except Exception as e:
                return f"Error writing code: {str(e)}"

        return write_code
