"""User data storage and retrieval tools for ToolRegistry.

This module provides tools for storing and retrieving user information
in the database. User data is stored in the User model and can be accessed
by key-value pairs.

Tools:
    - store_user_data: Store user information in the database
    - get_user_data: Retrieve user information from the database

Examples:
    >>> # Store user's name
    >>> store_user_data("name", "Alice")
    'Stored name: Alice'

    >>> # Retrieve user's name
    >>> get_user_data("name")
    'Alice'
"""

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.user.data.user import User


@tool(
    name="store_user_data",
    category=ToolCategory.KNOWLEDGE,
    description="Store user information in the database by key-value pairs",
    requires_api=False,
    keywords=["save", "store", "user", "data", "remember", "profile", "setting"],
    input_examples=[
        {"key": "name", "value": "Alice"},
        {"key": "email", "value": "alice@example.com"},
        {"key": "timezone", "value": "America/New_York"},
    ],
)
def store_user_data(key: str, value: str) -> str:
    """Store user information in the database.

    This tool allows the LLM to remember information about the user by
    storing it in the User model. The data is persisted across sessions
    and can be retrieved later using get_user_data.

    Args:
        key: The data field name (e.g., "name", "email", "preferences")
        value: The data value to store


    Examples:
        >>> store_user_data("name", "Alice")
        'Stored name: Alice'

        >>> store_user_data("email", "alice@example.com")
        'Stored email: alice@example.com'

    Note:
        - Data is automatically saved to the database
        - Existing values will be overwritten
        - The key must be a valid field name in the User model
    """
    try:
        user = User.objects.get_or_create()
        setattr(user, key, value)
        user.save()
        return f"Stored {key}: {value}"
    except Exception as e:
        return f"Error storing data: {str(e)}"


@tool(
    name="get_user_data",
    category=ToolCategory.KNOWLEDGE,
    description="Retrieve user information from the database by key",
    requires_api=False,
    keywords=["get", "retrieve", "user", "data", "recall", "profile", "setting"],
    input_examples=[
        {"key": "name"},
        {"key": "email"},
        {"key": "preferences"},
    ],
)
def get_user_data(key: str) -> str:
    """Retrieve user information from the database.

    This tool allows the LLM to recall previously stored information
    about the user. The data must have been stored using store_user_data.

    Args:
        key: The data field name to retrieve


    Examples:
        >>> get_user_data("name")
        'Alice'

        >>> get_user_data("nonexistent")
        'No data found for key: nonexistent'

    Note:
        - Returns None if the key doesn't exist
        - Values are converted to strings
        - Automatically retrieves from current user
    """
    try:
        user = User.objects.get_or_create()
        value = getattr(user, key, None)
        if value is None:
            return f"No data found for key: {key}"
        return str(value)
    except Exception as e:
        return f"Error retrieving data: {str(e)}"
