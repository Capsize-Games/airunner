"""
Browser settings data model for AI Runner.

This module defines the Pydantic data class for browser settings configuration.
"""

from pydantic import BaseModel as PydanticBaseModel, Field
from typing import Optional


class BrowserSettings(PydanticBaseModel):
    """Browser settings configuration.

    Attributes:
        id (Optional[int]): Unique identifier for the settings.
        browser_type (str): Type of browser (e.g., 'chrome', 'firefox').
        os_type (str): Operating system type (e.g., 'linux', 'windows').
        random (bool): Whether to randomize browser selection.
    """

    name: str = "browser"
    id: Optional[int] = Field(
        default=None, description="Unique identifier for the settings."
    )
    browser_type: str = Field(
        default="chrome",
        description="Type of browser (e.g., 'chrome', 'firefox').",
    )
    os_type: str = Field(
        default="linux",
        description="Operating system type (e.g., 'linux', 'windows').",
    )
    random: bool = Field(
        default=False, description="Whether to randomize browser selection."
    )
