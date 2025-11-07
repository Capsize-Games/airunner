"""
multi_file_code_tool.py

Tool for generating multiple code files in a single operation.

Manages multiple CodeSession instances for concurrent file generation
with coordinated streaming and completion.
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from airunner.components.llm.tools.code_session import (
    CodeSession,
    CodeSessionConfig,
    CodeSessionManager,
)
from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.enums import CodeOperationType
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class FileSpec:
    """Specification for a single file to create."""

    rel_path: str
    operation: CodeOperationType = CodeOperationType.CREATE
    initial_content: str = ""


class MultiFileCodeSession:
    """
    Manages code generation for multiple files.

    Coordinates multiple CodeSession instances to generate several files
    simultaneously or sequentially with proper streaming and completion.
    """

    def __init__(
        self,
        multi_session_id: str,
        workspace: WorkspaceManager,
        file_specs: List[FileSpec],
        config: Optional[CodeSessionConfig] = None,
        on_file_flush: Optional[Callable[[str, str, str], None]] = None,
        on_file_complete: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialize multi-file code session.

        Args:
            multi_session_id: Unique identifier for this multi-file session
            workspace: WorkspaceManager instance
            file_specs: List of file specifications to create
            config: Session configuration (applied to all files)
            on_file_flush: Callback(file_path, session_id, content) for each file flush
            on_file_complete: Callback(file_path, session_id) when file is complete
        """
        self.multi_session_id = multi_session_id
        self.workspace = workspace
        self.file_specs = file_specs
        self.config = config or CodeSessionConfig()
        self.on_file_flush = on_file_flush
        self.on_file_complete = on_file_complete

        # Create individual sessions for each file
        self.sessions: Dict[str, CodeSession] = {}
        self._create_sessions()

        logger.info(
            f"MultiFileCodeSession {multi_session_id} created for {len(file_specs)} files"
        )

    def _create_sessions(self) -> None:
        """Create individual CodeSession for each file."""
        for idx, spec in enumerate(self.file_specs):
            session_id = f"{self.multi_session_id}_file{idx}"

            # Create flush callback for this specific file
            def make_flush_callback(file_path: str, sid: str):
                def on_flush(abs_path: str, content: str):
                    if self.on_file_flush:
                        try:
                            self.on_file_flush(file_path, sid, content)
                        except Exception as e:
                            logger.error(f"Error in file flush callback: {e}")

                return on_flush

            flush_callback = make_flush_callback(spec.rel_path, session_id)

            # Create session
            session = CodeSession(
                session_id=session_id,
                workspace=self.workspace,
                rel_path=spec.rel_path,
                operation=spec.operation,
                config=self.config,
                on_flush=flush_callback,
            )

            # Write initial content if provided
            if spec.initial_content:
                for char in spec.initial_content:
                    session.receive_token(char)

            self.sessions[spec.rel_path] = session

            logger.debug(f"Created session {session_id} for {spec.rel_path}")

    def receive_token(self, rel_path: str, token: str) -> None:
        """
        Receive a token for a specific file.

        Args:
            rel_path: Relative path to the file
            token: Text token to add
        """
        session = self.sessions.get(rel_path)
        if not session:
            logger.warning(f"No session found for {rel_path}")
            return

        session.receive_token(token)

    def complete_file(self, rel_path: str) -> Optional[str]:
        """
        Mark a specific file as complete.

        Args:
            rel_path: Relative path to the file

        Returns:
            Absolute path to completed file, or None if not found
        """
        session = self.sessions.get(rel_path)
        if not session:
            logger.warning(f"No session found for {rel_path}")
            return None

        try:
            abs_path = session.complete()

            # Trigger completion callback
            if self.on_file_complete:
                try:
                    self.on_file_complete(rel_path, session.session_id)
                except Exception as e:
                    logger.error(f"Error in file complete callback: {e}")

            logger.info(f"File completed: {abs_path}")
            return abs_path

        except Exception as e:
            logger.error(f"Error completing file {rel_path}: {e}")
            return None

    def complete_all(self) -> List[str]:
        """
        Complete all files in the session.

        Returns:
            List of absolute paths to completed files
        """
        completed_paths = []

        for rel_path in self.sessions.keys():
            abs_path = self.complete_file(rel_path)
            if abs_path:
                completed_paths.append(abs_path)

        logger.info(
            f"MultiFileCodeSession {self.multi_session_id} completed: "
            f"{len(completed_paths)}/{len(self.sessions)} files"
        )

        return completed_paths

    def get_session(self, rel_path: str) -> Optional[CodeSession]:
        """Get the CodeSession for a specific file."""
        return self.sessions.get(rel_path)

    def get_file_paths(self) -> List[str]:
        """Get list of all file paths being managed."""
        return list(self.sessions.keys())

    def is_complete(self, rel_path: str) -> bool:
        """Check if a specific file is complete."""
        session = self.sessions.get(rel_path)
        return session.is_complete if session else False

    def are_all_complete(self) -> bool:
        """Check if all files are complete."""
        return all(session.is_complete for session in self.sessions.values())


class MultiFileCodeTool:
    """
    Tool for creating multiple files in a single operation.

    Provides high-level API for multi-file code generation with
    proper workspace management and streaming coordination.
    """

    def __init__(self, workspace_base_path: str):
        """
        Initialize multi-file code tool.

        Args:
            workspace_base_path: Base directory for the workspace
        """
        self.workspace = WorkspaceManager(workspace_base_path)
        self.session_manager = CodeSessionManager(self.workspace)
        self._multi_sessions: Dict[str, MultiFileCodeSession] = {}

        logger.info(
            f"MultiFileCodeTool initialized with base: {workspace_base_path}"
        )

    def create_multi_file_session(
        self,
        file_specs: List[FileSpec],
        multi_session_id: Optional[str] = None,
        config: Optional[CodeSessionConfig] = None,
        on_file_flush: Optional[Callable[[str, str, str], None]] = None,
        on_file_complete: Optional[Callable[[str, str], None]] = None,
    ) -> MultiFileCodeSession:
        """
        Create a new multi-file session.

        Args:
            file_specs: List of file specifications
            multi_session_id: Optional session ID (generated if not provided)
            config: Session configuration
            on_file_flush: Callback for file flush events
            on_file_complete: Callback for file completion events

        Returns:
            MultiFileCodeSession instance
        """
        import time

        if not multi_session_id:
            multi_session_id = f"multi_code_{int(time.time() * 1000)}"

        session = MultiFileCodeSession(
            multi_session_id=multi_session_id,
            workspace=self.workspace,
            file_specs=file_specs,
            config=config,
            on_file_flush=on_file_flush,
            on_file_complete=on_file_complete,
        )

        self._multi_sessions[multi_session_id] = session

        return session

    def get_multi_session(
        self, multi_session_id: str
    ) -> Optional[MultiFileCodeSession]:
        """Get a multi-file session by ID."""
        return self._multi_sessions.get(multi_session_id)

    def remove_multi_session(self, multi_session_id: str) -> None:
        """Remove a completed multi-file session."""
        if multi_session_id in self._multi_sessions:
            del self._multi_sessions[multi_session_id]
            logger.info(f"Removed multi-session {multi_session_id}")

    def get_active_multi_sessions(self) -> List[MultiFileCodeSession]:
        """Get all active (non-complete) multi-file sessions."""
        return [
            s
            for s in self._multi_sessions.values()
            if not s.are_all_complete()
        ]
