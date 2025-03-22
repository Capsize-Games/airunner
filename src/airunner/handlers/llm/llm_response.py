from typing import Optional
from dataclasses import dataclass

from airunner.enums import LLMActionType


@dataclass
class LLMResponse:
    message: str = ""
    is_first_message: bool = False
    is_end_of_message: bool = False
    name: Optional[str] = None
    action: LLMActionType = LLMActionType.CHAT
