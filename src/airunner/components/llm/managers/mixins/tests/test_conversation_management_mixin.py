"""Tests for ConversationManagementMixin.

Tests the conversation management mixin functionality including conversation
creation, loading, clearing, and RAG engine management.
"""

from unittest.mock import Mock, patch

from airunner.components.llm.managers.mixins.conversation_management_mixin import (
    ConversationManagementMixin,
)


class TestableConversationMixin(ConversationManagementMixin):
    """Testable version of ConversationManagementMixin."""

    def __init__(self):
        self.logger = Mock()
        self._workflow_manager = None
        self._tool_manager = None
        self._pending_conversation_message = None
        self.update_llm_generator_settings = Mock()
        self.tools = []
        self._unload_tool_manager = Mock()
        self._load_tool_manager = Mock()


class TestOnConversationDeleted:
    """Tests for on_conversation_deleted method."""

    def test_clears_workflow_memory_when_manager_exists(self):
        """Test clears workflow manager memory when available."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin.on_conversation_deleted({})

        mixin._workflow_manager.clear_memory.assert_called_once()

    def test_does_nothing_when_no_workflow_manager(self):
        """Test does nothing when workflow manager not loaded."""
        mixin = TestableConversationMixin()

        # Should not raise error
        mixin.on_conversation_deleted({})


class TestClearHistory:
    """Tests for clear_history method."""

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_creates_new_conversation(self, mock_conversation_class):
        """Test creates new conversation when none provided."""
        mock_conv = Mock()
        mock_conv.id = 123
        mock_conversation_class.create.return_value = mock_conv
        mock_conversation_class.make_current = Mock()

        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin.clear_history({})

        mock_conversation_class.create.assert_called_once()
        mock_conversation_class.make_current.assert_called_once_with(123)

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_updates_workflow_with_conversation(self, mock_conversation_class):
        """Test updates workflow manager with conversation ID."""
        mock_conv = Mock()
        mock_conv.id = 123
        mock_conversation_class.create.return_value = mock_conv
        mock_conversation_class.make_current = Mock()

        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin.clear_history({})

        mixin._workflow_manager.set_conversation_id.assert_called_once_with(
            123
        )

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_clears_memory_when_no_conversation(self, mock_conversation_class):
        """Test clears workflow memory when conversation creation fails."""
        mock_conversation_class.create.return_value = None

        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin.clear_history({})

        mixin._workflow_manager.clear_memory.assert_called_once()


class TestSetConversationAsCurrent:
    """Tests for _set_conversation_as_current method."""

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_marks_conversation_current(self, mock_conversation_class):
        """Test marks conversation as current."""
        mock_conv = Mock()
        mock_conv.id = 456
        mock_conversation_class.make_current = Mock()

        mixin = TestableConversationMixin()

        mixin._set_conversation_as_current(mock_conv)

        mock_conversation_class.make_current.assert_called_once_with(456)
        mixin.logger.info.assert_called()


class TestUpdateWorkflowWithConversation:
    """Tests for _update_workflow_with_conversation method."""

    def test_sets_conversation_id_when_present(self):
        """Test sets conversation ID in workflow manager."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()
        mock_conv = Mock()
        mock_conv.id = 789

        mixin._update_workflow_with_conversation(mock_conv)

        mixin._workflow_manager.set_conversation_id.assert_called_once_with(
            789
        )

    def test_clears_memory_when_no_conversation(self):
        """Test clears memory when conversation is None."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin._update_workflow_with_conversation(None)

        mixin._workflow_manager.clear_memory.assert_called_once()

    def test_does_nothing_when_no_workflow_manager(self):
        """Test does nothing when workflow manager not loaded."""
        mixin = TestableConversationMixin()

        # Should not raise error
        mixin._update_workflow_with_conversation(None)


class TestGetOrCreateConversation:
    """Tests for _get_or_create_conversation method."""

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_creates_new_when_no_id(self, mock_conversation_class):
        """Test creates new conversation when no ID provided."""
        mock_conv = Mock()
        mock_conversation_class.create.return_value = mock_conv

        mixin = TestableConversationMixin()
        data = {}

        result = mixin._get_or_create_conversation(data)

        assert result == mock_conv
        mock_conversation_class.create.assert_called_once()

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_loads_existing_when_id_provided(self, mock_conversation_class):
        """Test loads existing conversation when ID provided."""
        mock_conv = Mock()
        mock_conversation_class.objects.get.return_value = mock_conv

        mixin = TestableConversationMixin()
        data = {"conversation_id": 999}

        result = mixin._get_or_create_conversation(data)

        assert result == mock_conv
        mock_conversation_class.objects.get.assert_called_once_with(999)


class TestCreateNewConversation:
    """Tests for _create_new_conversation method."""

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_creates_and_updates_data(self, mock_conversation_class):
        """Test creates conversation and updates data dict."""
        mock_conv = Mock()
        mock_conv.id = 111
        mock_conversation_class.create.return_value = mock_conv

        mixin = TestableConversationMixin()
        data = {}

        result = mixin._create_new_conversation(data)

        assert result == mock_conv
        assert data["conversation_id"] == 111
        mixin.update_llm_generator_settings.assert_called_once()

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_returns_none_on_failure(self, mock_conversation_class):
        """Test returns None when conversation creation fails."""
        mock_conversation_class.create.return_value = None

        mixin = TestableConversationMixin()
        data = {}

        result = mixin._create_new_conversation(data)

        assert result is None


class TestLoadExistingConversation:
    """Tests for _load_existing_conversation method."""

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_loads_and_updates_settings(self, mock_conversation_class):
        """Test loads conversation and updates settings."""
        mock_conv = Mock()
        mock_conversation_class.objects.get.return_value = mock_conv

        mixin = TestableConversationMixin()

        result = mixin._load_existing_conversation(222)

        assert result == mock_conv
        mixin.update_llm_generator_settings.assert_called_once_with(
            current_conversation_id=222
        )

    @patch(
        "airunner.components.llm.managers.mixins.conversation_management_mixin.Conversation"
    )
    def test_returns_none_when_not_found(self, mock_conversation_class):
        """Test returns None when conversation not found."""
        mock_conversation_class.objects.get.return_value = None

        mixin = TestableConversationMixin()

        result = mixin._load_existing_conversation(222)

        assert result is None


class TestAddChatbotResponseToHistory:
    """Tests for add_chatbot_response_to_history method."""

    def test_is_placeholder(self):
        """Test is currently a no-op placeholder."""
        mixin = TestableConversationMixin()

        # Should not raise error
        mixin.add_chatbot_response_to_history("test message")


class TestLoadConversation:
    """Tests for load_conversation method."""

    def test_loads_into_workflow_when_available(self):
        """Test loads conversation into workflow manager."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()
        mixin._workflow_manager.set_conversation_id = Mock()

        mixin.load_conversation({"conversation_id": 333})

        mixin._workflow_manager.set_conversation_id.assert_called_once_with(
            333
        )
        assert mixin._pending_conversation_message is None

    def test_defers_when_workflow_not_ready(self):
        """Test defers loading when workflow manager not ready."""
        mixin = TestableConversationMixin()
        message = {"conversation_id": 444}

        mixin.load_conversation(message)

        assert mixin._pending_conversation_message == message
        mixin.logger.warning.assert_called()


class TestLoadConversationIntoWorkflow:
    """Tests for _load_conversation_into_workflow method."""

    def test_sets_conversation_id_when_has_method(self):
        """Test sets conversation ID when workflow supports it."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()

        mixin._load_conversation_into_workflow(555)

        mixin._workflow_manager.set_conversation_id.assert_called_once_with(
            555
        )

    def test_logs_when_no_setter_method(self):
        """Test logs info when workflow lacks setter method."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock(spec=[])  # No set_conversation_id

        mixin._load_conversation_into_workflow(666)

        mixin.logger.info.assert_called()


class TestDeferConversationLoad:
    """Tests for _defer_conversation_load method."""

    def test_stores_message_and_warns(self):
        """Test stores message for later and logs warning."""
        mixin = TestableConversationMixin()
        message = {"conversation_id": 777}

        mixin._defer_conversation_load(777, message)

        assert mixin._pending_conversation_message == message
        mixin.logger.warning.assert_called()


class TestReloadRagEngine:
    """Tests for reload_rag_engine method."""

    def test_reloads_tool_manager_and_updates_workflow(self):
        """Test reloads tool manager and updates workflow tools."""
        mixin = TestableConversationMixin()
        mixin._tool_manager = Mock()
        mixin._workflow_manager = Mock()
        mixin.tools = ["tool1", "tool2"]

        mixin.reload_rag_engine()

        mixin._unload_tool_manager.assert_called_once()
        mixin._load_tool_manager.assert_called_once()
        mixin._workflow_manager.update_tools.assert_called_once_with(
            ["tool1", "tool2"]
        )

    def test_warns_when_tool_manager_not_loaded(self):
        """Test logs warning when tool manager not available."""
        mixin = TestableConversationMixin()

        mixin.reload_rag_engine()

        mixin.logger.warning.assert_called()


class TestReloadToolManager:
    """Tests for _reload_tool_manager method."""

    def test_unloads_and_loads_tool_manager(self):
        """Test unloads then loads tool manager."""
        mixin = TestableConversationMixin()

        mixin._reload_tool_manager()

        mixin._unload_tool_manager.assert_called_once()
        mixin._load_tool_manager.assert_called_once()


class TestUpdateWorkflowTools:
    """Tests for _update_workflow_tools method."""

    def test_updates_tools_when_workflow_exists(self):
        """Test updates workflow manager with tools."""
        mixin = TestableConversationMixin()
        mixin._workflow_manager = Mock()
        mixin.tools = ["tool1"]

        mixin._update_workflow_tools()

        mixin._workflow_manager.update_tools.assert_called_once_with(["tool1"])

    def test_does_nothing_when_no_workflow(self):
        """Test does nothing when workflow manager not loaded."""
        mixin = TestableConversationMixin()

        # Should not raise error
        mixin._update_workflow_tools()
