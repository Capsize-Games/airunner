"""Window settings dataclass for main window geometry and state.

This module defines the WindowSettings dataclass, which is used to persist and restore the main window's geometry and state in AI Runner.

Attributes:
    is_maximized (bool): Whether the window is maximized.
    is_fullscreen (bool): Whether the window is fullscreen.
    width (int): Window width in pixels.
    height (int): Window height in pixels.
    x_pos (int): X position of the window.
    y_pos (int): Y position of the window.
    active_main_tab_index (int): Index of the active main tab.
"""

from dataclasses import dataclass


@dataclass
class WindowSettings:
    is_maximized: bool = False
    is_fullscreen: bool = False
    width: int = 800
    height: int = 600
    x_pos: int = 0
    y_pos: int = 0
    active_main_tab_index: int = 0
