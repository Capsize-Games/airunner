"""
workspace_manager.py

Centralized workspace and file management for the code editor.

Provides safe, atomic file operations with backup support, path validation,
and file locking to ensure data integrity during LLM-driven code generation.
"""

from typing import List, Dict
import os
import shutil
import tempfile
import glob
from threading import RLock

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import (
    get_logger,
)  # Use RLock instead of Lock for reentrant locking

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    fcntl = None
    _HAS_FCNTL = False

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class WorkspaceManager:
    """
    Manages file operations within a workspace directory.

    Provides atomic writes, backup support, path validation, and file locking
    to ensure safe concurrent access during code generation and editing.
    """

    def __init__(self, base_path: str):
        """
        Initialize workspace manager.

        Args:
            base_path: Absolute path to the workspace root directory
        """
        self.base_path = os.path.expanduser(os.path.abspath(base_path))
        os.makedirs(self.base_path, exist_ok=True)
        self._locks: Dict[str, RLock] = (
            {}
        )  # In-memory reentrant locks per file
        self._lock_for_locks = RLock()  # Lock for the locks dict itself
        logger.info(
            f"WorkspaceManager initialized with base_path: {self.base_path}"
        )

    def _abs(self, rel_path: str) -> str:
        """
        Convert relative path to absolute, ensuring it's within workspace.

        Args:
            rel_path: Relative path from workspace root

        Returns:
            Absolute path

        Raises:
            ValueError: If path is outside workspace
        """
        # Normalize and join
        abs_path = os.path.normpath(os.path.join(self.base_path, rel_path))

        # Security check: ensure path is within workspace
        if not abs_path.startswith(self.base_path):
            raise ValueError(
                f"Path '{rel_path}' is outside workspace: {self.base_path}"
            )

        return abs_path

    def _get_file_lock(self, abs_path: str) -> RLock:
        """Get or create an in-memory reentrant lock for a specific file."""
        with self._lock_for_locks:
            if abs_path not in self._locks:
                self._locks[abs_path] = RLock()
            return self._locks[abs_path]

    def read_file(self, rel_path: str) -> str:
        """
        Read file content from workspace.

        Args:
            rel_path: Relative path to file

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        abs_path = self._abs(rel_path)
        lock = self._get_file_lock(abs_path)

        with lock:
            try:
                with open(abs_path, "r", encoding="utf-8") as fh:
                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
                        except Exception as e:
                            logger.warning(
                                f"Failed to acquire shared lock for {abs_path}: {e}"
                            )

                    content = fh.read()

                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                        except Exception:
                            pass

                    return content
            except FileNotFoundError:
                logger.error(f"File not found: {abs_path}")
                raise
            except Exception as e:
                logger.error(f"Error reading file {abs_path}: {e}")
                raise

    def write_file(
        self,
        rel_path: str,
        content: str,
        *,
        backup: bool = True,
        create_dirs: bool = True,
    ) -> str:
        """
        Write content to file atomically with optional backup.

        Uses a temporary file and atomic rename to ensure data integrity.

        Args:
            rel_path: Relative path to file
            content: Content to write
            backup: If True and file exists, create .bak backup
            create_dirs: If True, create parent directories if needed

        Returns:
            Absolute path to written file
        """
        abs_path = self._abs(rel_path)
        lock = self._get_file_lock(abs_path)

        with lock:
            try:
                # Create parent directories
                if create_dirs:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

                # Create backup if file exists
                if backup and os.path.exists(abs_path):
                    backup_path = abs_path + ".bak"
                    try:
                        shutil.copy2(abs_path, backup_path)
                        logger.debug(f"Created backup: {backup_path}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to create backup for {abs_path}: {e}"
                        )

                # Write to temporary file
                dir_name = os.path.dirname(abs_path)
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=dir_name, prefix=".tmp_", suffix=".py"
                )

                try:
                    with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                        if _HAS_FCNTL:
                            try:
                                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to acquire exclusive lock: {e}"
                                )

                        fh.write(content)
                        fh.flush()

                        try:
                            os.fsync(fh.fileno())
                        except Exception as e:
                            logger.warning(f"fsync failed for {tmp_path}: {e}")

                        if _HAS_FCNTL:
                            try:
                                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                            except Exception:
                                pass

                    # Atomic rename
                    os.replace(tmp_path, abs_path)
                    logger.info(f"File written: {abs_path}")
                    return abs_path

                except Exception:
                    # Clean up temp file on error
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception as cleanup_err:
                        logger.warning(
                            f"Failed to cleanup temp file {tmp_path}: {cleanup_err}"
                        )
                    raise

            except Exception as e:
                logger.error(f"Error writing file {abs_path}: {e}")
                raise

    def append_file(
        self, rel_path: str, content: str, *, backup: bool = False
    ) -> str:
        """
        Append content to existing file or create if doesn't exist.

        Args:
            rel_path: Relative path to file
            content: Content to append
            backup: Create backup before appending

        Returns:
            Absolute path to file
        """
        abs_path = self._abs(rel_path)
        lock = self._get_file_lock(abs_path)

        with lock:
            try:
                # Read existing content
                existing = ""
                if os.path.exists(abs_path):
                    existing = self.read_file(rel_path)

                # Write combined content
                return self.write_file(
                    rel_path, existing + content, backup=backup
                )
            except Exception as e:
                logger.error(f"Error appending to file {abs_path}: {e}")
                raise

    def apply_patch(self, rel_path: str, patch_content: str) -> str:
        """
        Apply a unified diff patch to a file.

        Args:
            rel_path: Relative path to file
            patch_content: Unified diff format patch

        Returns:
            Absolute path to patched file

        Raises:
            ValueError: If patch cannot be applied
        """
        abs_path = self._abs(rel_path)

        try:
            # Read original content
            if not os.path.exists(abs_path):
                raise FileNotFoundError(
                    f"Cannot patch non-existent file: {rel_path}"
                )

            original_lines = self.read_file(rel_path).splitlines(keepends=True)

            # Parse patch (simple implementation - could use external library)
            # For now, just log that this needs implementation
            logger.warning(
                "apply_patch is a placeholder - full implementation needed"
            )

            # TODO: Implement proper patch parsing and application
            # For basic implementation, you could use:
            # - difflib.unified_diff for generating patches
            # - Manual parsing for applying patches
            # Or integrate with 'patch' command or python-patch library

            raise NotImplementedError("Patch application not yet implemented")

        except Exception as e:
            logger.error(f"Error applying patch to {abs_path}: {e}")
            raise

    def unique_path(self, rel_dir: str, base_name: str) -> str:
        """
        Generate unique filename in directory by adding numeric suffix if needed.

        Args:
            rel_dir: Relative directory path
            base_name: Base filename

        Returns:
            Relative path to unique filename
        """
        base_dir_abs = self._abs(rel_dir)
        os.makedirs(base_dir_abs, exist_ok=True)

        candidate = os.path.join(base_dir_abs, base_name)

        if not os.path.exists(candidate):
            return os.path.relpath(candidate, self.base_path)

        # Add numeric suffix
        name, ext = os.path.splitext(base_name)
        counter = 1

        while True:
            candidate = os.path.join(base_dir_abs, f"{name}_{counter}{ext}")
            if not os.path.exists(candidate):
                return os.path.relpath(candidate, self.base_path)
            counter += 1

    def list_files(
        self, rel_dir: str = "", pattern: str = "*.py", recursive: bool = False
    ) -> List[str]:
        """
        List files in directory matching pattern.

        Args:
            rel_dir: Relative directory path (empty for workspace root)
            pattern: Glob pattern for matching files
            recursive: If True, search recursively

        Returns:
            List of relative paths to matching files
        """
        search_dir = self._abs(rel_dir)

        if not os.path.exists(search_dir):
            return []

        pattern_path = os.path.join(
            search_dir, "**" if recursive else "", pattern
        )
        matches = glob.glob(pattern_path, recursive=recursive)

        # Convert to relative paths
        return [os.path.relpath(m, self.base_path) for m in matches]

    def rename(self, old_rel_path: str, new_rel_path: str) -> str:
        """
        Rename or move a file within workspace.

        Args:
            old_rel_path: Current relative path
            new_rel_path: New relative path

        Returns:
            Absolute path to renamed file
        """
        old_abs = self._abs(old_rel_path)
        new_abs = self._abs(new_rel_path)

        if not os.path.exists(old_abs):
            raise FileNotFoundError(
                f"Cannot rename non-existent file: {old_rel_path}"
            )

        # Create parent directories for new location
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)

        # Use shutil.move for cross-filesystem support
        shutil.move(old_abs, new_abs)
        logger.info(f"Renamed: {old_rel_path} -> {new_rel_path}")

        return new_abs

    def delete(self, rel_path: str, backup: bool = True) -> None:
        """
        Delete a file from workspace.

        Args:
            rel_path: Relative path to file
            backup: If True, create .bak backup before deletion
        """
        abs_path = self._abs(rel_path)

        if not os.path.exists(abs_path):
            logger.warning(f"Cannot delete non-existent file: {rel_path}")
            return

        if backup:
            backup_path = abs_path + ".deleted.bak"
            try:
                shutil.copy2(abs_path, backup_path)
                logger.debug(f"Created deletion backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create deletion backup: {e}")

        os.remove(abs_path)
        logger.info(f"Deleted: {rel_path}")

    def exists(self, rel_path: str) -> bool:
        """Check if file exists in workspace."""
        abs_path = self._abs(rel_path)
        return os.path.exists(abs_path)

    def get_file_info(self, rel_path: str) -> Dict:
        """
        Get file metadata.

        Returns:
            Dictionary with keys: size, modified_time, exists, is_file, is_dir
        """
        abs_path = self._abs(rel_path)

        if not os.path.exists(abs_path):
            return {
                "exists": False,
                "size": 0,
                "modified_time": None,
                "is_file": False,
                "is_dir": False,
            }

        stat = os.stat(abs_path)
        return {
            "exists": True,
            "size": stat.st_size,
            "modified_time": stat.st_mtime,
            "is_file": os.path.isfile(abs_path),
            "is_dir": os.path.isdir(abs_path),
            "abs_path": abs_path,
        }
