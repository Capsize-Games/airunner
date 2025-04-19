from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

from airunner.enums import LLMActionType


@dataclass
class LLMResponse:
    """
    Represents a response from a Large Language Model.

    This dataclass encapsulates the structured output from an LLM,
    including the generated text, token counts, and metadata.

    Attributes:
        text: The generated text response.
        tokens_generated: Number of tokens in the generated response.
        tokens_processed: Number of tokens in the input that were processed.
        total_time: Time taken for generation in seconds.
        metadata: Optional dictionary containing additional information.
    """

    text: str
    tokens_generated: int = 0
    tokens_processed: int = 0
    total_time: float = 0.0
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """
        Convert the response to a dictionary.

        Returns:
            Dict: Dictionary representation of the response.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "LLMResponse":
        """
        Create an LLMResponse from a dictionary.

        Args:
            data: Dictionary containing response data.

        Returns:
            LLMResponse: A new instance with data from the dictionary.
        """
        return cls(**data)
