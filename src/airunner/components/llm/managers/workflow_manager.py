"""Manages the LangGraph workflow for agent execution.

This is the refactored version with functionality split into focused mixins.
"""

from typing import Any, Annotated, Optional, List, Callable
from typing_extensions import TypedDict

from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import add_messages

from airunner.components.llm.managers.database_checkpoint_saver import (
    DatabaseCheckpointSaver,
)

# Import workflow mixins directly to avoid circular import
# (mixins/__init__.py imports component_loader_mixin which imports WorkflowManager)
from airunner.components.llm.managers.mixins.tool_management_mixin import (
    ToolManagementMixin,
)
from airunner.components.llm.managers.mixins.tool_execution_mixin import (
    ToolExecutionMixin,
)
from airunner.components.llm.managers.mixins.workflow_building_mixin import (
    WorkflowBuildingMixin,
)
from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)
from airunner.components.llm.managers.mixins.system_prompt_mixin import (
    SystemPromptMixin,
)
from airunner.components.llm.managers.mixins.streaming_mixin import (
    StreamingMixin,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class WorkflowState(TypedDict, total=False):
    """State schema for the workflow.
    
    Attributes:
        messages: List of conversation messages (required)
        workflow_continuation: Flag set when force_response should route back to model
    """

    messages: Annotated[list[BaseMessage], add_messages]
    workflow_continuation: bool


class WorkflowManager(
    ToolManagementMixin,
    ToolExecutionMixin,
    WorkflowBuildingMixin,
    SystemPromptMixin,  # Added to provide dynamic system_prompt property for mood regeneration
    NodeFunctionsMixin,
    StreamingMixin,
):
    """Manages the LangGraph workflow for agent execution.

    Inherits from:
        - ToolManagementMixin: Tool binding and schema generation
        - ToolExecutionMixin: Tool execution with status tracking
        - WorkflowBuildingMixin: Graph construction and compilation
        - NodeFunctionsMixin: Node function implementations
        - StreamingMixin: Workflow execution and streaming
    """

    def __init__(
        self,
        system_prompt: str,
        chat_model: Any,
        tools: Optional[List[Callable]] = None,
        max_history_tokens: int = 8000,
        conversation_id: Optional[int] = None,
        use_mode_routing: bool = False,
        mode_override: Optional[str] = None,
        llm_settings: Optional[Any] = None,
        chatbot: Optional[Any] = None,
        signal_emitter: Optional[Any] = None,
    ):
        """
        Initialize the workflow manager.

        Args:
            system_prompt: System prompt for the agent
            chat_model: LangChain ChatModel instance
                (ChatHuggingFaceLocal, ChatOllama, etc.)
            tools: List of LangChain tools
            max_history_tokens: Maximum tokens for conversation history trimming
            conversation_id: Optional conversation ID for persistence
            use_mode_routing: Enable mode-based routing
                (author/code/research/qa/general)
            mode_override: Force specific mode instead of auto-classification
            llm_settings: LLM settings for configuration (e.g., mood tracking)
            chatbot: Chatbot instance for settings (e.g., use_mood)
            signal_emitter: Object with emit_signal method (e.g., LLMModelManager)
        """
        # Initialize all mixins
        super().__init__()

        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

        # Core configuration
        self._system_prompt = system_prompt
        self._original_chat_model = chat_model  # Store original unbound model
        self._chat_model = chat_model
        self._tools = tools or []
        self._max_history_tokens = max_history_tokens
        self._token_counter = lambda msgs: count_tokens_approximately(msgs)
        self._conversation_id = conversation_id
        self._memory = DatabaseCheckpointSaver(conversation_id)
        self._response_format = None  # Optional response format override (e.g., "json", "conversational")
        self._force_tool = None  # Store forced tool for agentic research mode

        # Store settings for automatic mood tracking
        self.llm_settings = llm_settings
        self.chatbot = chatbot
        self._signal_emitter = signal_emitter  # Store signal emitter
        self._thread_id = (
            str(conversation_id) if conversation_id else "default"
        )

        # Workflow state
        self._workflow = None
        self._compiled_workflow = None
        self._token_callback: Optional[Callable[[str], None]] = None
        self._interrupted = False
        self._use_mode_routing = use_mode_routing
        self._mode_override = mode_override
        self._executed_tools: list[str] = (
            []
        )  # Track tools called in current invocation

        # Initialize model and build workflow
        self._initialize_model()
        self._build_and_compile_workflow()

    def clear_memory(self):
        """Clear the conversation memory/history and checkpoint state.

        This clears:
        1. Message history in database
        2. LangGraph checkpoint state (in-memory)
        3. Rebuilds workflow with fresh state

        CRITICAL: Must clear checkpoints to prevent state contamination
        between tests or conversation resets.
        """
        # Clear message history
        self._memory.message_history.clear()

        # CRITICAL: Clear LangGraph checkpoint state
        if hasattr(self._memory, "clear_checkpoints"):
            self._memory.clear_checkpoints()

        # Rebuild workflow with fresh memory
        self._build_and_compile_workflow()

    def set_conversation_id(
        self, conversation_id: int, ephemeral: bool = False
    ):
        """Set the conversation ID for persistence.

        Args:
            conversation_id: Conversation ID to use for storing messages
            ephemeral: If True, don't save messages to database (memory-only)
        """

        self._conversation_id = conversation_id
        self._thread_id = str(conversation_id)

        self._memory = DatabaseCheckpointSaver(
            conversation_id, ephemeral=ephemeral
        )

        # NOTE: We do NOT clear checkpoints here. The checkpoint saver loads
        # messages from the database when get() is called, which merges
        # existing history with new messages via the add_messages reducer.
        # Clearing would wipe in-flight state from other conversations.

        self._build_and_compile_workflow()

    def update_system_prompt(self, system_prompt: str):
        """Update the system prompt and rebuild the workflow.

        Args:
            system_prompt: New system prompt
        """
        self.logger.debug(
            f"Updating system prompt to: {system_prompt[:200]}...",
        )
        self._system_prompt = system_prompt
        self._build_and_compile_workflow()

    def set_response_format(self, response_format: Optional[str]):
        """Set the expected response format after tool execution.

        Args:
            response_format: Response format ("json", "conversational", or None for default)
        """
        self._response_format = response_format
        self.logger.info(f"Response format set to: {response_format}")

    def set_force_tool(self, force_tool: Optional[str]):
        """Set the forced tool for agentic research mode.
        
        When set, post-tool instructions will encourage continuing research
        instead of immediately answering the user's question.

        Args:
            force_tool: Tool name (e.g., "search_web") or None to disable
        """
        self._force_tool = force_tool
        self.logger.info(f"Force tool set to: {force_tool}")

    def set_token_callback(
        self, callback: Optional[Callable[[str], None]]
    ) -> None:
        """Register a callback for streaming tokens during model execution.

        Args:
            callback: Callback function that receives token strings
        """
        self._token_callback = callback
