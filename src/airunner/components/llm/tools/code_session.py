"""
code_session.py

Manages a code generation session with streaming token buffering and file updates.

Handles real-time code streaming from LLM to file with periodic flushes to disk
and editor tab updates.
"""

from typing import Optional, Callable
import time
from dataclasses import dataclass

from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.enums import CodeOperationType
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class CodeSessionConfig:
    """Configuration for code session behavior."""

    flush_token_count: int = 10  # Flush every N tokens
    flush_interval_seconds: float = 0.25  # Flush every N seconds
    auto_format: bool = True  # Run black/isort after completion
    create_backup: bool = True  # Create backup before overwriting
    strip_markdown: bool = True  # Remove markdown code blocks


class CodeSession:
    """
    Manages a single code generation session.

    Handles streaming tokens from LLM, buffering, periodic flushing to disk,
    and coordination with the document editor for real-time updates.
    """

    def __init__(
        self,
        session_id: str,
        workspace: WorkspaceManager,
        rel_path: str,
        operation: CodeOperationType = CodeOperationType.CREATE,
        config: Optional[CodeSessionConfig] = None,
        on_flush: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialize code session.

        Args:
            session_id: Unique identifier for this session
            workspace: WorkspaceManager instance
            rel_path: Relative path to file being edited
            operation: Type of operation (CREATE, EDIT, etc.)
            config: Session configuration
            on_flush: Callback called after each flush: on_flush(abs_path, content)
        """
        self.session_id = session_id
        self.workspace = workspace
        self.rel_path = rel_path
        self.operation = operation
        self.config = config or CodeSessionConfig()
        self.on_flush = on_flush

        # State
        self._buffer: list[str] = []
        self._accumulated_code = ""
        self._token_count = 0
        self._last_flush_time = time.time()
        self._is_complete = False

        logger.info(
            f"CodeSession {session_id} created for {rel_path} ({operation.value})"
        )

    def receive_token(self, token: str) -> None:
        """
        Receive a token from the LLM stream.

        Args:
            token: Text token to add to buffer
        """
        if self._is_complete:
            logger.warning(
                f"Session {self.session_id} already complete, ignoring token"
            )
            return

        self._buffer.append(token)
        self._token_count += 1

        # Check if we should flush
        should_flush = False

        # Flush based on token count
        if self._token_count >= self.config.flush_token_count:
            should_flush = True

        # Flush based on time interval
        elapsed = time.time() - self._last_flush_time
        if elapsed >= self.config.flush_interval_seconds:
            should_flush = True

        if should_flush and self._buffer:
            self.flush()

    def flush(self) -> None:
        """Flush buffered tokens to file and trigger editor update."""
        if not self._buffer:
            return

        try:
            # Combine buffer tokens
            new_content = "".join(self._buffer)
            self._accumulated_code += new_content
            self._buffer.clear()

            # Write to file
            abs_path = self.workspace.write_file(
                self.rel_path,
                self._accumulated_code,
                backup=self.config.create_backup,
            )

            self._token_count = 0
            self._last_flush_time = time.time()

            # Trigger callback for editor update
            if self.on_flush:
                try:
                    self.on_flush(abs_path, self._accumulated_code)
                except Exception as e:
                    logger.error(f"Error in flush callback: {e}")

            logger.debug(
                f"Session {self.session_id} flushed "
                f"{len(new_content)} chars to {self.rel_path}"
            )

        except Exception as e:
            logger.error(f"Error flushing session {self.session_id}: {e}")
            raise

    def complete(self) -> str:
        """
        Mark session as complete and perform final processing.

        Returns:
            Absolute path to the completed file
        """
        if self._is_complete:
            logger.warning(f"Session {self.session_id} already completed")
            return self.workspace._abs(self.rel_path)

        try:
            # Final flush
            self.flush()

            # Clean up markdown if needed
            if self.config.strip_markdown:
                self._accumulated_code = self._strip_markdown_blocks(
                    self._accumulated_code
                )

            # Format code if requested
            if self.config.auto_format:
                self._accumulated_code = self._format_code(
                    self._accumulated_code
                )

            # Final write with cleaned/formatted code
            abs_path = self.workspace.write_file(
                self.rel_path,
                self._accumulated_code,
                backup=self.config.create_backup,
            )

            # Final callback
            if self.on_flush:
                try:
                    self.on_flush(abs_path, self._accumulated_code)
                except Exception as e:
                    logger.error(f"Error in final flush callback: {e}")

            self._is_complete = True

            logger.info(
                f"Session {self.session_id} completed: {abs_path} "
                f"({len(self._accumulated_code)} chars)"
            )

            return abs_path

        except Exception as e:
            logger.error(f"Error completing session {self.session_id}: {e}")
            raise

    def _strip_markdown_blocks(self, code: str) -> str:
        """
        Remove markdown code block markers from code.

        Args:
            code: Code potentially containing ```python ... ``` markers

        Returns:
            Clean code without markdown
        """
        cleaned = code.strip()

        # Remove opening code block marker (```python or ```)
        if cleaned.startswith("```python"):
            cleaned = cleaned[len("```python") :].lstrip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].lstrip()

        # Remove closing code block marker (```)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()

        return cleaned

    def _format_code(self, code: str) -> str:
        """
        Format code using black and isort.

        Args:
            code: Python code to format

        Returns:
            Formatted code
        """
        try:
            # Try to import and use black
            try:
                import black

                mode = black.Mode(
                    line_length=88,
                    string_normalization=True,
                    is_pyi=False,
                )

                code = black.format_str(code, mode=mode)
                logger.debug("Code formatted with black")

            except ImportError:
                logger.debug("black not available, skipping formatting")
            except Exception as e:
                logger.warning(f"black formatting failed: {e}")

            # Try to import and use isort
            try:
                import isort

                code = isort.code(code)
                logger.debug("Imports sorted with isort")

            except ImportError:
                logger.debug("isort not available, skipping import sorting")
            except Exception as e:
                logger.warning(f"isort failed: {e}")

        except Exception as e:
            logger.error(f"Error during code formatting: {e}")

        return code

    def get_accumulated_code(self) -> str:
        """Get all accumulated code so far (including buffer)."""
        return self._accumulated_code + "".join(self._buffer)

    def get_line_count(self) -> int:
        """Get current line count of accumulated code."""
        return self.get_accumulated_code().count("\n") + 1

    def get_char_count(self) -> int:
        """Get character count of accumulated code."""
        return len(self.get_accumulated_code())

    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self._is_complete


class CodeSessionManager:
    """
    Manages multiple concurrent code sessions.

    Tracks active sessions and provides factory methods for creating
    new sessions with proper configuration.
    """

    def __init__(self, workspace: WorkspaceManager):
        """
        Initialize session manager.

        Args:
            workspace: WorkspaceManager instance
        """
        self.workspace = workspace
        self._sessions: dict[str, CodeSession] = {}
        self._next_session_id = 1

        logger.info("CodeSessionManager initialized")

    def create_session(
        self,
        rel_path: str,
        operation: CodeOperationType = CodeOperationType.CREATE,
        config: Optional[CodeSessionConfig] = None,
        on_flush: Optional[Callable[[str, str], None]] = None,
    ) -> CodeSession:
        """
        Create a new code session.

        Args:
            rel_path: Relative path to file
            operation: Operation type
            config: Session configuration
            on_flush: Flush callback

        Returns:
            New CodeSession instance
        """
        session_id = f"code_session_{self._next_session_id}"
        self._next_session_id += 1

        session = CodeSession(
            session_id=session_id,
            workspace=self.workspace,
            rel_path=rel_path,
            operation=operation,
            config=config,
            on_flush=on_flush,
        )

        self._sessions[session_id] = session

        logger.info(f"Created session {session_id} for {rel_path}")

        return session

    def get_session(self, session_id: str) -> Optional[CodeSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove completed session from tracking."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Removed session {session_id}")

    def get_active_sessions(self) -> list[CodeSession]:
        """Get all active (non-complete) sessions."""
        return [s for s in self._sessions.values() if not s.is_complete]

    def complete_all(self) -> None:
        """Complete all active sessions."""
        for session in self.get_active_sessions():
            try:
                session.complete()
            except Exception as e:
                logger.error(
                    f"Error completing session {session.session_id}: {e}"
                )
