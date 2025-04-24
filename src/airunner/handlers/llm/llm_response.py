from typing import Optional
from dataclasses import dataclass

from airunner.enums import LLMActionType


@dataclass
class LLMResponse:
    """
    Represents a response from a Large Language Model.

    This class encapsulates the message content and metadata about the message state,
    such as whether it's the first or last message in a sequence.

    Attributes:
        message: The text content of the LLM response.
        is_first_message: Flag indicating if this is the first message in a sequence.
        is_end_of_message: Flag indicating if this is the last message in a sequence.
        name: Optional name associated with the response (e.g., assistant name).
        action: The type of action this response represents.
    """

    message: str = ""
    is_first_message: bool = False
    is_end_of_message: bool = False
    name: Optional[str] = None
    action: LLMActionType = LLMActionType.CHAT
    node_id: Optional[str] = None
