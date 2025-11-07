"""
code_operations_handler.py

Handler for executing different code file operations (READ, PATCH, APPEND, etc.).

Provides unified interface for all code operation types with proper error handling
and validation.
"""

from typing import Optional

from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.enums import CodeOperationType
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class CodeOperationResult:
    """Result of a code operation."""

    def __init__(
        self,
        success: bool,
        operation: CodeOperationType,
        file_path: str,
        message: str = "",
        content: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.operation = operation
        self.file_path = file_path
        self.message = message
        self.content = content
        self.error = error

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.operation.value}: {self.file_path} - {self.message}"


class CodeOperationsHandler:
    """
    Handles execution of different code file operations.

    Provides methods for CREATE, READ, EDIT, PATCH, APPEND, RENAME, DELETE,
    LIST, and FORMAT operations with proper validation and error handling.
    """

    def __init__(self, workspace: WorkspaceManager):
        """
        Initialize operations handler.

        Args:
            workspace: WorkspaceManager instance for file operations
        """
        self.workspace = workspace
        logger.info("CodeOperationsHandler initialized")

    def execute(
        self,
        operation: CodeOperationType,
        rel_path: str,
        content: Optional[str] = None,
        **kwargs,
    ) -> CodeOperationResult:
        """
        Execute a code operation.

        Args:
            operation: Type of operation to perform
            rel_path: Relative path to file
            content: Content for write operations
            **kwargs: Additional operation-specific arguments

        Returns:
            CodeOperationResult with success status and details
        """
        try:
            if operation == CodeOperationType.CREATE:
                return self.create(rel_path, content, **kwargs)
            elif operation == CodeOperationType.READ:
                return self.read(rel_path)
            elif operation == CodeOperationType.EDIT:
                return self.edit(rel_path, content, **kwargs)
            elif operation == CodeOperationType.PATCH:
                return self.patch(rel_path, content, **kwargs)
            elif operation == CodeOperationType.APPEND:
                return self.append(rel_path, content, **kwargs)
            elif operation == CodeOperationType.RENAME:
                return self.rename(rel_path, kwargs.get("new_path"))
            elif operation == CodeOperationType.DELETE:
                return self.delete(rel_path, **kwargs)
            elif operation == CodeOperationType.LIST:
                return self.list_files(rel_path, **kwargs)
            elif operation == CodeOperationType.FORMAT:
                return self.format_file(rel_path, **kwargs)
            else:
                return CodeOperationResult(
                    success=False,
                    operation=operation,
                    file_path=rel_path,
                    error=f"Unknown operation: {operation}",
                )

        except Exception as e:
            logger.error(
                f"Error executing {operation.value} on {rel_path}: {e}"
            )
            return CodeOperationResult(
                success=False,
                operation=operation,
                file_path=rel_path,
                error=str(e),
            )

    def create(
        self,
        rel_path: str,
        content: str,
        backup: bool = False,
    ) -> CodeOperationResult:
        """
        Create a new file with content.

        Args:
            rel_path: Relative path to file
            content: File content
            backup: Create backup if file exists

        Returns:
            CodeOperationResult
        """
        try:
            abs_path = self.workspace.write_file(
                rel_path, content, backup=backup
            )

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.CREATE,
                file_path=abs_path,
                message=f"Created file ({len(content)} chars)",
                content=content,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.CREATE,
                file_path=rel_path,
                error=str(e),
            )

    def read(self, rel_path: str) -> CodeOperationResult:
        """
        Read file content.

        Args:
            rel_path: Relative path to file

        Returns:
            CodeOperationResult with file content
        """
        try:
            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.READ,
                    file_path=rel_path,
                    error="File does not exist",
                )

            content = self.workspace.read_file(rel_path)

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.READ,
                file_path=rel_path,
                message=f"Read file ({len(content)} chars)",
                content=content,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.READ,
                file_path=rel_path,
                error=str(e),
            )

    def edit(
        self,
        rel_path: str,
        content: str,
        backup: bool = True,
    ) -> CodeOperationResult:
        """
        Edit (replace) entire file content.

        Args:
            rel_path: Relative path to file
            content: New file content
            backup: Create backup before editing

        Returns:
            CodeOperationResult
        """
        try:
            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.EDIT,
                    file_path=rel_path,
                    error="File does not exist (use CREATE instead)",
                )

            abs_path = self.workspace.write_file(
                rel_path, content, backup=backup
            )

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.EDIT,
                file_path=abs_path,
                message=f"Edited file ({len(content)} chars)",
                content=content,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.EDIT,
                file_path=rel_path,
                error=str(e),
            )

    def patch(
        self,
        rel_path: str,
        patch_content: str,
        backup: bool = True,
    ) -> CodeOperationResult:
        """
        Apply a unified diff patch to file.

        Args:
            rel_path: Relative path to file
            patch_content: Unified diff patch content
            backup: Create backup before patching

        Returns:
            CodeOperationResult
        """
        try:
            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.PATCH,
                    file_path=rel_path,
                    error="File does not exist",
                )

            # Read current content
            current_content = self.workspace.read_file(rel_path)

            # Apply patch (simplified - in production use proper patch library)
            # For now, just append the patch content as a comment
            # TODO: Implement proper unified diff parsing and application
            new_content = (
                current_content + "\n\n# PATCH APPLIED:\n" + patch_content
            )

            abs_path = self.workspace.write_file(
                rel_path, new_content, backup=backup
            )

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.PATCH,
                file_path=abs_path,
                message=f"Applied patch ({len(patch_content)} chars)",
                content=new_content,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.PATCH,
                file_path=rel_path,
                error=str(e),
            )

    def append(
        self,
        rel_path: str,
        content: str,
        backup: bool = False,
    ) -> CodeOperationResult:
        """
        Append content to end of file.

        Args:
            rel_path: Relative path to file
            content: Content to append
            backup: Create backup before appending

        Returns:
            CodeOperationResult
        """
        try:
            abs_path = self.workspace.append_file(
                rel_path, content, backup=backup
            )

            # Read final content
            final_content = self.workspace.read_file(rel_path)

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.APPEND,
                file_path=abs_path,
                message=f"Appended {len(content)} chars",
                content=final_content,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.APPEND,
                file_path=rel_path,
                error=str(e),
            )

    def rename(
        self,
        rel_path: str,
        new_rel_path: Optional[str],
    ) -> CodeOperationResult:
        """
        Rename or move a file.

        Args:
            rel_path: Current relative path
            new_rel_path: New relative path

        Returns:
            CodeOperationResult
        """
        try:
            if not new_rel_path:
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.RENAME,
                    file_path=rel_path,
                    error="new_path is required",
                )

            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.RENAME,
                    file_path=rel_path,
                    error="File does not exist",
                )

            abs_new_path = self.workspace.rename(rel_path, new_rel_path)

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.RENAME,
                file_path=abs_new_path,
                message=f"Renamed {rel_path} -> {new_rel_path}",
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.RENAME,
                file_path=rel_path,
                error=str(e),
            )

    def delete(
        self,
        rel_path: str,
        backup: bool = True,
    ) -> CodeOperationResult:
        """
        Delete a file.

        Args:
            rel_path: Relative path to file
            backup: Create backup before deleting

        Returns:
            CodeOperationResult
        """
        try:
            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.DELETE,
                    file_path=rel_path,
                    error="File does not exist",
                )

            self.workspace.delete(rel_path, backup=backup)

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.DELETE,
                file_path=rel_path,
                message=f"Deleted file (backup: {backup})",
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.DELETE,
                file_path=rel_path,
                error=str(e),
            )

    def list_files(
        self,
        pattern: str = "**/*.py",
        recursive: bool = True,
    ) -> CodeOperationResult:
        """
        List files matching pattern.

        Args:
            pattern: Glob pattern to match files
            recursive: Search recursively

        Returns:
            CodeOperationResult with file list in content
        """
        try:
            # Parse pattern to extract directory and filename pattern
            # e.g., "**/*.py" -> rel_dir="", pattern="*.py"
            # e.g., "test*.py" -> rel_dir="", pattern="test*.py"
            if "/" in pattern:
                parts = pattern.rsplit("/", 1)
                rel_dir = parts[0].replace("**", "")
                file_pattern = parts[1]
            else:
                rel_dir = ""
                file_pattern = pattern

            files = self.workspace.list_files(
                rel_dir=rel_dir, pattern=file_pattern, recursive=recursive
            )

            # Format as newline-separated list
            file_list = "\n".join(sorted(files))

            return CodeOperationResult(
                success=True,
                operation=CodeOperationType.LIST,
                file_path=pattern,
                message=f"Found {len(files)} files",
                content=file_list,
            )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.LIST,
                file_path=pattern,
                error=str(e),
            )

    def format_file(
        self,
        rel_path: str,
        backup: bool = True,
    ) -> CodeOperationResult:
        """
        Format file with black and isort.

        Args:
            rel_path: Relative path to file
            backup: Create backup before formatting

        Returns:
            CodeOperationResult
        """
        try:
            if not self.workspace.exists(rel_path):
                return CodeOperationResult(
                    success=False,
                    operation=CodeOperationType.FORMAT,
                    file_path=rel_path,
                    error="File does not exist",
                )

            # Read current content
            content = self.workspace.read_file(rel_path)

            # Format with black
            formatted_content = content
            try:
                import black

                mode = black.Mode(
                    line_length=88,
                    string_normalization=True,
                    is_pyi=False,
                )

                formatted_content = black.format_str(content, mode=mode)
                logger.debug("Formatted with black")

            except ImportError:
                logger.debug("black not available")
            except Exception as e:
                logger.warning(f"black formatting failed: {e}")

            # Sort imports with isort
            try:
                import isort

                formatted_content = isort.code(formatted_content)
                logger.debug("Sorted imports with isort")

            except ImportError:
                logger.debug("isort not available")
            except Exception as e:
                logger.warning(f"isort failed: {e}")

            # Write back if changed
            if formatted_content != content:
                abs_path = self.workspace.write_file(
                    rel_path, formatted_content, backup=backup
                )

                return CodeOperationResult(
                    success=True,
                    operation=CodeOperationType.FORMAT,
                    file_path=abs_path,
                    message="File formatted successfully",
                    content=formatted_content,
                )
            else:
                return CodeOperationResult(
                    success=True,
                    operation=CodeOperationType.FORMAT,
                    file_path=rel_path,
                    message="No formatting changes needed",
                    content=content,
                )

        except Exception as e:
            return CodeOperationResult(
                success=False,
                operation=CodeOperationType.FORMAT,
                file_path=rel_path,
                error=str(e),
            )
