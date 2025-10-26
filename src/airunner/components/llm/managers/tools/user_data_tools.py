"""User data storage and retrieval tools."""

from typing import Callable

from langchain.tools import tool

from airunner.components.user.data.user import User


class UserDataTools:
    """Mixin class providing user data management tools."""

    def store_user_data_tool(self) -> Callable:
        """Store user information."""

        @tool
        def store_user_data(key: str, value: str) -> str:
            """Store user information in the database.

            Args:
                key: The data field name
                value: The data value

            Returns:
                Confirmation message
            """
            try:
                user = User.get_or_create()
                setattr(user, key, value)
                user.save()
                return f"Stored {key}: {value}"
            except Exception as e:
                return f"Error storing data: {str(e)}"

        return store_user_data

    def get_user_data_tool(self) -> Callable:
        """Retrieve user information."""

        @tool
        def get_user_data(key: str) -> str:
            """Retrieve user information from the database.

            Args:
                key: The data field name to retrieve

            Returns:
                The stored value or error message
            """
            try:
                user = User.get_or_create()
                value = getattr(user, key, None)
                if value is None:
                    return f"No data found for key: {key}"
                return str(value)
            except Exception as e:
                return f"Error retrieving data: {str(e)}"

        return get_user_data
