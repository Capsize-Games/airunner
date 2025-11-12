"""File system and document tools."""

import os
from typing import Callable

from langchain.tools import tool

from airunner.components.tools.base_tool import BaseTool


class FileTools(BaseTool):
    """Mixin class providing file system and document management tools."""

    def list_files_tool(self) -> Callable:
        """List files in a directory."""

        @tool
        def list_files(directory: str) -> str:
            """List files in a directory.

            Args:
                directory: Path to directory

            Returns:
                List of files or error message
            """
            try:
                if not os.path.exists(directory):
                    return f"Directory not found: {directory}"

                files = os.listdir(directory)
                return "\n".join(files) if files else "Directory is empty"
            except Exception as e:
                return f"Error listing files: {str(e)}"

        return list_files

    def read_file_tool(self) -> Callable:
        """Read content from a file."""

        @tool
        def read_file(file_path: str) -> str:
            """Read and return the contents of a file.

            Useful for analyzing code, reading documents, or accessing data files.

            Args:
                file_path: Path to the file to read

            Returns:
                File contents or error message
            """
            try:
                if not os.path.exists(file_path):
                    return f"File not found: {file_path}"

                with open(file_path, "r") as f:
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
                from airunner.enums import SignalCode

                # Ensure it's a Python file
                if not file_path.endswith(".py"):
                    file_path += ".py"

                # Build full path
                base_path = os.path.expanduser(self.path_settings.base_path)
                full_path = os.path.join(base_path, "user_code", file_path)

                # Create directory if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # Write code
                with open(full_path, "w") as f:
                    if description:
                        f.write(f'"""{description}"""\n\n')
                    f.write(code_content)

                # Signal to open in editor (if implemented)
                self.emit_signal(
                    SignalCode.OPEN_CODE_EDITOR,
                    {"file_path": full_path, "content": code_content},
                )

                return f"Code written to {file_path}"
            except Exception as e:
                return f"Error writing code: {str(e)}"

        return write_code
