"""GUI-side re-export of the canonical conversation daemon client."""

from airunner_services.daemon_client.conversation_client import (
    ConversationDaemonClient,
)

__all__ = ["ConversationDaemonClient"]
