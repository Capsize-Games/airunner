"""State definitions for LangGraph workflows.

This module provides predefined state classes for common agentic workflows,
as well as utilities for creating custom states.
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum


class AgentStateType(str, Enum):
    """Predefined state types for common workflows."""

    SIMPLE = "simple"  # Basic message passing
    RAG = "rag"  # RAG with context
    TOOL_CALLING = "tool"  # Tool execution
    CUSTOM = "custom"  # User-defined


class BaseAgentState(TypedDict):
    """Base state for all LangGraph workflows.

    Attributes:
        messages: List of messages in the conversation
        next_action: Name of the next node to execute
        error: Optional error message if something went wrong
        metadata: Additional metadata for the workflow
    """

    messages: List[str]
    next_action: str
    error: Optional[str]
    metadata: Dict[str, Any]


class RAGAgentState(BaseAgentState):
    """State for RAG (Retrieval-Augmented Generation) workflows.

    Extends BaseAgentState with RAG-specific fields.

    Attributes:
        rag_context: Retrieved context from RAG system
        retrieved_docs: List of retrieved document chunks with metadata
        query: Current query being processed
    """

    rag_context: str
    retrieved_docs: List[Dict[str, Any]]
    query: str


class ToolAgentState(BaseAgentState):
    """State for tool-based workflows.

    Extends BaseAgentState with tool execution tracking.

    Attributes:
        tool_calls: List of tool calls to execute
        tool_results: Results from executed tools
        current_tool: Name of currently executing tool
    """

    tool_calls: List[Dict[str, Any]]
    tool_results: List[Any]
    current_tool: Optional[str]


class StateFactory:
    """Factory for creating state classes dynamically."""

    @staticmethod
    def create_state_class(
        name: str,
        base_class: type = BaseAgentState,
        additional_fields: Optional[Dict[str, type]] = None,
    ) -> type:
        """Create a custom state class.

        Args:
            name: Name for the state class
            base_class: Base class to extend
            additional_fields: Additional fields to add {field_name: type}

        Returns:
            New state class
        """
        if additional_fields is None:
            additional_fields = {}

        # Get base annotations
        annotations = getattr(base_class, "__annotations__", {}).copy()

        # Add additional fields
        annotations.update(additional_fields)

        # Create new class
        new_class = type(
            name,
            (base_class,),
            {"__annotations__": annotations},
        )

        return new_class

    @staticmethod
    def from_dict(state_dict: Dict[str, Any]) -> Dict[str, type]:
        """Convert a dictionary to field definitions.

        Args:
            state_dict: Dict with field names as keys and type names as values
                       (e.g., {"field1": "str", "field2": "int"})

        Returns:
            Dict of field_name: type
        """
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": List,
            "dict": Dict,
            "any": Any,
            "optional": Optional,
        }

        fields = {}
        for field_name, type_name in state_dict.items():
            if isinstance(type_name, str):
                fields[field_name] = type_map.get(type_name.lower(), Any)
            else:
                fields[field_name] = type_name

        return fields
