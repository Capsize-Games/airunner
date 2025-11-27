"""
Fara Settings Database Model.

This module defines the database schema for Fara-7B computer use agent settings.
"""

from sqlalchemy import Column, Integer, String, Boolean, Float

from airunner.data.models import BaseModel


# Default Fara model path
DEFAULT_FARA_MODEL = "microsoft/Fara-7B"


class FaraSettings(BaseModel):
    """
    Database model for Fara-7B agent settings.

    Stores configuration for the computer use agent including:
    - Model path and quantization settings
    - Screen resolution for coordinate mapping
    - Safety settings (max steps, critical points)
    - Integration settings (enable/disable, routing)
    """

    __tablename__ = "fara_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Model settings
    model_path = Column(String, default=DEFAULT_FARA_MODEL)
    use_quantization = Column(Boolean, default=True)
    quantization_bits = Column(Integer, default=4)  # 4-bit or 8-bit

    # Screen settings
    screen_width = Column(Integer, default=1428)
    screen_height = Column(Integer, default=896)
    auto_detect_resolution = Column(Boolean, default=True)

    # Execution settings
    max_steps = Column(Integer, default=50)
    step_delay = Column(Float, default=0.5)
    timeout_seconds = Column(Integer, default=300)

    # Safety settings
    enable_critical_points = Column(Boolean, default=True)
    require_confirmation = Column(Boolean, default=True)
    blocked_actions = Column(String, default="")  # Comma-separated

    # Integration settings
    enabled = Column(Boolean, default=False)
    use_for_all_tools = Column(Boolean, default=False)
    use_for_web_search = Column(Boolean, default=True)
    use_for_browser_automation = Column(Boolean, default=True)

    # Automation backend
    use_pyautogui = Column(Boolean, default=True)
    use_playwright = Column(Boolean, default=False)

    def get_blocked_actions_list(self) -> list:
        """Get blocked actions as a list."""
        if not self.blocked_actions:
            return []
        return [a.strip() for a in self.blocked_actions.split(",") if a.strip()]

    def set_blocked_actions_list(self, actions: list) -> None:
        """Set blocked actions from a list."""
        self.blocked_actions = ",".join(actions)
