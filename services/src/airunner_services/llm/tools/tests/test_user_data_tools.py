"""Unit tests for user_data_tools module.

Tests the store_user_data and get_user_data tools with mocked User model
to ensure proper functionality without database dependencies.
"""

from unittest.mock import Mock, patch

from airunner.components.llm.tools.user_data_tools import (
    store_user_data,
    get_user_data,
)


class TestStoreUserData:
    """Test cases for store_user_data tool."""

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_success(self, mock_user_class):
        """Test successfully storing user data."""
        # Arrange
        mock_user = Mock()
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("name", "Alice")

        # Assert
        assert result == "Stored name: Alice"
        mock_user_class.objects.get_or_create.assert_called_once()
        assert hasattr(mock_user, "name")
        mock_user.save.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_email(self, mock_user_class):
        """Test storing user email."""
        # Arrange
        mock_user = Mock()
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("email", "alice@example.com")

        # Assert
        assert result == "Stored email: alice@example.com"
        mock_user_class.objects.get_or_create.assert_called_once()
        mock_user.save.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_preferences(self, mock_user_class):
        """Test storing user preferences."""
        # Arrange
        mock_user = Mock()
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("preferences", "dark_mode")

        # Assert
        assert result == "Stored preferences: dark_mode"
        mock_user_class.objects.get_or_create.assert_called_once()
        mock_user.save.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_overwrites_existing(self, mock_user_class):
        """Test that storing data overwrites existing values."""
        # Arrange
        mock_user = Mock()
        mock_user.name = "Bob"
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("name", "Alice")

        # Assert
        assert result == "Stored name: Alice"
        mock_user.save.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_error_handling(self, mock_user_class):
        """Test error handling when storage fails."""
        # Arrange
        mock_user_class.objects.get_or_create.side_effect = Exception("Database error")

        # Act
        result = store_user_data("name", "Alice")

        # Assert
        assert "Error storing data: Database error" in result

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_save_error(self, mock_user_class):
        """Test error handling when save fails."""
        # Arrange
        mock_user = Mock()
        mock_user.save.side_effect = Exception("Save failed")
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("name", "Alice")

        # Assert
        assert "Error storing data: Save failed" in result

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_empty_value(self, mock_user_class):
        """Test storing empty string value."""
        # Arrange
        mock_user = Mock()
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("name", "")

        # Assert
        assert result == "Stored name: "
        mock_user.save.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_store_user_data_special_characters(self, mock_user_class):
        """Test storing value with special characters."""
        # Arrange
        mock_user = Mock()
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = store_user_data("bio", "Hello! I'm a developer 🚀")

        # Assert
        assert result == "Stored bio: Hello! I'm a developer 🚀"
        mock_user.save.assert_called_once()


class TestGetUserData:
    """Test cases for get_user_data tool."""

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_success(self, mock_user_class):
        """Test successfully retrieving user data."""
        # Arrange
        mock_user = Mock()
        mock_user.name = "Alice"
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("name")

        # Assert
        assert result == "Alice"
        mock_user_class.objects.get_or_create.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_email(self, mock_user_class):
        """Test retrieving user email."""
        # Arrange
        mock_user = Mock()
        mock_user.email = "alice@example.com"
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("email")

        # Assert
        assert result == "alice@example.com"
        mock_user_class.objects.get_or_create.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_not_found(self, mock_user_class):
        """Test retrieving non-existent key."""
        # Arrange
        mock_user = Mock(spec=[])  # Empty spec means no attributes
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("nonexistent")

        # Assert
        assert "No data found for key: nonexistent" in result
        mock_user_class.objects.get_or_create.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_none_value(self, mock_user_class):
        """Test retrieving key with None value."""
        # Arrange
        mock_user = Mock()
        mock_user.name = None
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("name")

        # Assert
        assert "No data found for key: name" in result

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_integer_value(self, mock_user_class):
        """Test retrieving integer value (converted to string)."""
        # Arrange
        mock_user = Mock()
        mock_user.age = 30
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("age")

        # Assert
        assert result == "30"
        mock_user_class.objects.get_or_create.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_boolean_value(self, mock_user_class):
        """Test retrieving boolean value (converted to string)."""
        # Arrange
        mock_user = Mock()
        mock_user.is_active = True
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("is_active")

        # Assert
        assert result == "True"
        mock_user_class.objects.get_or_create.assert_called_once()

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_error_handling(self, mock_user_class):
        """Test error handling when retrieval fails."""
        # Arrange
        mock_user_class.objects.get_or_create.side_effect = Exception("Database error")

        # Act
        result = get_user_data("name")

        # Assert
        assert "Error retrieving data: Database error" in result

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_with_property_error(self, mock_user_class):
        """Test error handling when accessing property raises exception."""
        # Arrange
        mock_user = Mock()
        # Configure the mock so accessing 'name' raises an exception
        type(mock_user).name = property(
            lambda self: (_ for _ in ()).throw(Exception("Property error"))
        )
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("name")

        # Assert
        assert "Error retrieving data: Property error" in result

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_empty_string_value(self, mock_user_class):
        """Test retrieving empty string (should return the empty string)."""
        # Arrange
        mock_user = Mock()
        mock_user.name = ""
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("name")

        # Assert
        # Empty string is falsy but should still be returned
        assert result == ""

    @patch("airunner.components.llm.tools.user_data_tools.User")
    def test_get_user_data_zero_value(self, mock_user_class):
        """Test retrieving zero value (should return "0")."""
        # Arrange
        mock_user = Mock()
        mock_user.count = 0
        mock_user_class.objects.get_or_create.return_value = mock_user

        # Act
        result = get_user_data("count")

        # Assert
        # 0 is falsy but should still be returned
        assert result == "0"
