"""Conversation management mixin for LLM model manager.

This mixin handles conversation lifecycle operations including creating,
loading, clearing, and managing conversation history in the database.
"""

from typing import TYPE_CHECKING, Dict, Optional

from airunner.components.llm.data.conversation import Conversation

if TYPE_CHECKING:
    from airunner.components.llm.managers.llm_model_manager import (
        LLMModelManager,
    )


class ConversationManagementMixin:
    """Mixin for managing conversation history and state.

    Handles conversation creation, loading, deletion, and integration
    with the workflow manager's memory system.
    """

    def on_conversation_deleted(self: "LLMModelManager", data: Dict) -> None:
        """Handle conversation deletion event.

        Clears workflow manager memory when a conversation is deleted.

        Args:
            data: Event data dictionary (not currently used).
        """
        if self._workflow_manager:
            self._workflow_manager.clear_memory()

    def clear_history(
        self: "LLMModelManager", data: Optional[Dict] = None
    ) -> None:
        """Clear chat history and start a new conversation.

        Creates or retrieves a conversation and sets it as current,
        then updates the workflow manager with the new conversation ID.

        Args:
            data: Optional dict with conversation_id key.
        """
        data = data or {}
        conversation = self._get_or_create_conversation(data)

        if conversation:
            self._set_conversation_as_current(conversation)

        self._update_workflow_with_conversation(conversation)

    def _set_conversation_as_current(
        self: "LLMModelManager", conversation: Conversation
    ) -> None:
        """Set conversation as the current active conversation.

        Args:
            conversation: Conversation object to set as current.
        """
        Conversation.make_current(conversation.id)
        self.logger.info(
            f"Starting new conversation with ID: {conversation.id}"
        )

    def _update_workflow_with_conversation(
        self: "LLMModelManager",
        conversation: Optional[Conversation],
        ephemeral: bool = False,
    ) -> None:
        """Update workflow manager with conversation ID or clear memory.

        Args:
            conversation: Conversation object, or None to clear memory.
            ephemeral: If True, don't save conversation to database (memory-only).
        """
        if not self._workflow_manager:
            return

        if conversation:
            self._workflow_manager.set_conversation_id(
                conversation.id, ephemeral=ephemeral
            )
        else:
            self._workflow_manager.clear_memory()

    def _get_or_create_conversation(
        self: "LLMModelManager", data: Dict
    ) -> Optional[Conversation]:
        """Get existing conversation or create a new one.

        Args:
            data: Dict that may contain conversation_id key.

        Returns:
            Conversation object, or None if creation/retrieval failed.
        """
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            return self._create_new_conversation(data)

        return self._load_existing_conversation(conversation_id)

    def _create_new_conversation(
        self: "LLMModelManager", data: Dict
    ) -> Optional[Conversation]:
        """Create a new conversation and update settings.

        Args:
            data: Dict to update with new conversation_id.

        Returns:
            New Conversation object, or None if creation failed.
        """
        conversation = Conversation.create()

        if not conversation:
            return None

        data["conversation_id"] = conversation.id
        self.update_llm_generator_settings(
            current_conversation_id=conversation.id
        )
        return conversation

    def _load_existing_conversation(
        self: "LLMModelManager", conversation_id: int
    ) -> Optional[Conversation]:
        """Load an existing conversation by ID.

        Args:
            conversation_id: Database ID of conversation to load.

        Returns:
            Conversation object, or None if not found.
        """
        conversation = Conversation.objects.get(conversation_id)

        if conversation:
            self.update_llm_generator_settings(
                current_conversation_id=conversation_id
            )

        return conversation

    def add_chatbot_response_to_history(
        self: "LLMModelManager", message: str
    ) -> None:
        """Add a chatbot-generated response to chat history.

        Currently a no-op placeholder for future implementation.

        Args:
            message: The chatbot's response message.
        """

    def load_conversation(self: "LLMModelManager", message: Dict) -> None:
        """Load an existing conversation into the chat workflow.

        If workflow manager is loaded, sets the conversation ID immediately.
        Otherwise, stores message as pending for later processing.

        Args:
            message: Dict containing conversation_id key.
        """
        conversation_id = message.get("conversation_id")

        if self._workflow_manager is not None:
            self._load_conversation_into_workflow(conversation_id)
            self._pending_conversation_message = None
        else:
            self._defer_conversation_load(conversation_id, message)

    def _load_conversation_into_workflow(
        self: "LLMModelManager", conversation_id: Optional[int]
    ) -> None:
        """Load conversation into the workflow manager.

        Args:
            conversation_id: ID of conversation to load, or None.
        """
        if conversation_id and hasattr(
            self._workflow_manager, "set_conversation_id"
        ):
            self._workflow_manager.set_conversation_id(conversation_id)
            self.logger.info(
                f"Updated workflow manager with conversation ID: "
                f"{conversation_id}"
            )
        else:
            self.logger.info(
                f"Workflow manager loaded. Conversation {conversation_id} "
                "context available."
            )

    def _defer_conversation_load(
        self: "LLMModelManager", conversation_id: Optional[int], message: Dict
    ) -> None:
        """Defer conversation loading until workflow manager is ready.

        Args:
            conversation_id: ID of conversation to load.
            message: Original message dict to process later.
        """
        self.logger.warning(
            f"Workflow manager not loaded. Will use "
            f"ConversationHistoryManager for conversation ID: {conversation_id}."
        )
        self._pending_conversation_message = message

    def reload_rag_engine(self: "LLMModelManager") -> None:
        """Reload the Retrieval-Augmented Generation engine.

        Unloads and reloads the tool manager, then updates workflow
        manager with refreshed tools.
        """
        if not self._tool_manager:
            self.logger.warning("Cannot reload RAG - tool manager not loaded")
            return

        self._reload_tool_manager()
        self._update_workflow_tools()

    def _reload_tool_manager(self: "LLMModelManager") -> None:
        """Unload and reload the tool manager."""
        self._unload_tool_manager()
        self._load_tool_manager()

    def _update_workflow_tools(self: "LLMModelManager") -> None:
        """Update workflow manager with refreshed tools."""
        if self._workflow_manager:
            self._workflow_manager.update_tools(self.tools)
