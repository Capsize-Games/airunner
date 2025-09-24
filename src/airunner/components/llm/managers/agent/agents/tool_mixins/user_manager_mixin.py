from typing import Optional

from airunner.components.user.data.user import User


class UserManagerMixin:
    """
    Mixin for managing user retrieval and updates.
    """

    def __init__(self):
        self._user = None

    @property
    def user(self) -> User:
        # If _user is set by test, always return it
        if hasattr(self, "_user_set_by_test") and getattr(
            self, "_user_set_by_test", False
        ):
            return self._user
        # If _user is set, always return it and never overwrite
        if hasattr(self, "_user") and self._user is not None:
            return self._user
        # Only fetch from DB if _user is not set
        user = None
        if self.conversation:
            user = User.objects.get(self.conversation.user_id)
        if not user:
            user = User.objects.filter_first(
                User.username == getattr(self, "_username", None)
                or getattr(self, "username", None)
            )
        if not user:
            user = User()
            user.save()
        # Only set _user if it was not set before
        if not hasattr(self, "_user") or self._user is None:
            self._user = user
        return self._user

    @user.setter
    def user(self, value: Optional[User]):
        self._user = value
        # Only update conversation if value is not None and has id
        if value is not None and hasattr(value, "id"):
            self._update_conversation("user_id", value.id)

    def _update_user(self, key: str, value):
        setattr(self.user, key, value)
        self.user.save()
