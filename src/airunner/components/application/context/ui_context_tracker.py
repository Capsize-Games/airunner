"""UI context tracker for tracking active application section.

This module provides a singleton service that tracks which UI section
is currently active in the application. The LLM uses this context to
understand what the user is working on and provide relevant assistance.

Follows project conventions for signal-based communication using MediatorMixin.
"""

from typing import Optional
from airunner.enums import UISection, SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin


class UIContextTracker(MediatorMixin):
    """Singleton service for tracking active UI section.
    
    This class tracks which section of the application is currently active
    (e.g., art editor, document editor, calendar) and provides methods to
    query this context for the LLM system prompts.
    
    Uses signal-based communication to receive section change notifications
    from the main window.
    
    Attributes:
        _instance: Singleton instance
        _active_section: Currently active UI section
        _document_context: Optional context about the active document
    """
    
    _instance: Optional["UIContextTracker"] = None
    
    def __new__(cls) -> "UIContextTracker":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the tracker with default section."""
        if getattr(self, "_initialized", False):
            return
            
        super().__init__()
        self._active_section: UISection = UISection.HOME
        self._document_context: Optional[dict] = None
        self._initialized = True
        
        # Register for section change signals
        self.register(SignalCode.SECTION_CHANGED, self._on_section_changed)
    
    def _on_section_changed(self, data: dict) -> None:
        """Handle section change signal.
        
        Args:
            data: Signal data containing 'section' key with button name or UISection
        """
        section = data.get("section")
        if section is None:
            return
            
        if isinstance(section, UISection):
            self._active_section = section
        elif isinstance(section, str):
            # Convert button name to UISection
            self._active_section = UISection.from_button_name(section)
        
        # Clear document context when section changes
        self._document_context = None
    
    def set_section(self, section: UISection) -> None:
        """Manually set the active section.
        
        Args:
            section: The UISection to set as active
        """
        self._active_section = section
        self._document_context = None
    
    def set_document_context(self, context: dict) -> None:
        """Set document-specific context for the current section.
        
        Args:
            context: Dictionary with document context (e.g., file path, language)
        """
        self._document_context = context
    
    @property
    def active_section(self) -> UISection:
        """Get the currently active UI section.
        
        Returns:
            The current UISection enum value
        """
        return self._active_section
    
    @property
    def section_context(self) -> str:
        """Get context description for the active section.
        
        Returns:
            Human-readable description for the LLM system prompt
        """
        return self._active_section.get_context_description()
    
    @property
    def document_context(self) -> Optional[dict]:
        """Get document-specific context if available.
        
        Returns:
            Dictionary with document context or None
        """
        return self._document_context
    
    def get_full_context(self) -> str:
        """Get complete context string for system prompt injection.
        
        Combines section context with any document-specific context.
        
        Returns:
            Complete context string for the system prompt
        """
        parts = []
        
        section_desc = self.section_context
        if section_desc:
            parts.append(f"**CURRENT UI CONTEXT:**\n{section_desc}")
        
        if self._document_context:
            doc_parts = []
            if "file_path" in self._document_context:
                doc_parts.append(f"Active file: {self._document_context['file_path']}")
            if "language" in self._document_context:
                doc_parts.append(f"Language: {self._document_context['language']}")
            if "line_count" in self._document_context:
                doc_parts.append(f"Lines: {self._document_context['line_count']}")
            if "cursor_position" in self._document_context:
                doc_parts.append(f"Cursor: {self._document_context['cursor_position']}")
            
            if doc_parts:
                parts.append("Document: " + ", ".join(doc_parts))
        
        return "\n".join(parts)
    
    def should_include_section_context(self, action_type) -> bool:
        """Determine if section context should be included for an action.
        
        Some actions benefit from knowing the UI context, while others
        (like RAG search or mood updates) do not need it.
        
        Args:
            action_type: The LLMActionType being performed
            
        Returns:
            True if section context should be included
        """
        from airunner.enums import LLMActionType
        
        # Actions that benefit from UI context
        context_aware_actions = {
            LLMActionType.CHAT,
            LLMActionType.APPLICATION_COMMAND,
            LLMActionType.GENERATE_IMAGE,
            LLMActionType.CODE,
            LLMActionType.FILE_INTERACTION,
            LLMActionType.WORKFLOW_INTERACTION,
        }
        
        return action_type in context_aware_actions


def get_ui_context_tracker() -> UIContextTracker:
    """Get the singleton UIContextTracker instance.
    
    Returns:
        The global UIContextTracker instance
    """
    return UIContextTracker()
