"""
Document editor component.

This component provides workspace management and file operations
for code editing and document management.
"""

from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.components.document_editor.project import (
    AirunnerAutonomyMode,
    AirunnerProjectManager,
    AirunnerProjectOpenResult,
    AirunnerProjectRoot,
    AirunnerProjectService,
    AirunnerProjectSettings,
    AirunnerRecentProjectEntry,
    AirunnerTrustLevel,
    AirunnerWorkspaceConfig,
)
from airunner.components.document_editor.terminal import (
    TerminalSessionInfo,
    TerminalSessionManager,
)

__all__ = [
    "AirunnerAutonomyMode",
    "AirunnerProjectManager",
    "AirunnerProjectOpenResult",
    "AirunnerProjectRoot",
    "AirunnerProjectService",
    "AirunnerProjectSettings",
    "AirunnerRecentProjectEntry",
    "AirunnerTrustLevel",
    "AirunnerWorkspaceConfig",
    "TerminalSessionInfo",
    "TerminalSessionManager",
    "WorkspaceManager",
]
