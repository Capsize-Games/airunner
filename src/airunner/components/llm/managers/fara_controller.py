"""
Fara Computer Use Controller.

This module provides the controller for Fara-7B computer use agent,
managing the screenshot capture, action execution, and feedback loop.

The controller:
1. Captures screenshots of the current screen/window
2. Sends screenshots + goal to Fara for action prediction
3. Executes the predicted action (click, type, scroll, etc.)
4. Loops until task is complete or critical point reached

Usage:
    controller = FaraController()
    controller.execute_task("Search for flights to NYC")
"""

import time
import json
import re
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import io

from PIL import Image

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class TaskStatus(Enum):
    """Status of a Fara task execution."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"  # At critical point, waiting for user
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class CriticalPointType(Enum):
    """Types of critical points that require user permission."""
    CHECKOUT = "checkout"
    PURCHASE = "purchase"
    BOOKING = "booking"
    EMAIL = "email"
    CALL = "call"
    FORM_SUBMISSION = "form_submission"
    PERSONAL_INFO = "personal_info"
    PAYMENT = "payment"
    LOGIN = "login"


@dataclass
class ActionResult:
    """Result of executing an action."""
    success: bool
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    screenshot_after: Optional[Image.Image] = None


@dataclass
class TaskResult:
    """Result of a complete task execution."""
    status: TaskStatus
    goal: str
    steps_taken: int
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    memorized_facts: List[str] = field(default_factory=list)
    final_screenshot: Optional[Image.Image] = None
    critical_point: Optional[CriticalPointType] = None
    error: Optional[str] = None


class FaraActionExecutor:
    """
    Executes Fara's predicted actions on the system.

    This class handles the actual execution of actions like:
    - Mouse clicks and movements
    - Keyboard typing and key presses
    - Scrolling
    - Browser navigation

    NOTE: This uses pyautogui for desktop automation. For web-only
    automation, consider using Selenium or Playwright instead.
    """

    def __init__(
        self,
        use_pyautogui: bool = True,
        use_playwright: bool = False,
        browser_instance: Optional[Any] = None,
    ):
        """
        Initialize the action executor.

        Args:
            use_pyautogui: Use pyautogui for desktop automation
            use_playwright: Use playwright for web automation
            browser_instance: Pre-existing browser instance for web automation
        """
        self._use_pyautogui = use_pyautogui
        self._use_playwright = use_playwright
        self._browser = browser_instance
        self._page = None

        # Lazy import pyautogui
        self._pyautogui = None
        if use_pyautogui:
            try:
                # Suppress the tkinter NOTE from MouseInfo by redirecting stdout/stderr
                import sys
                import io
                
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                
                try:
                    import pyautogui
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                
                self._pyautogui = pyautogui
                # Safety settings
                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = 0.1
            except ImportError:
                logger.warning("pyautogui not installed. Desktop actions disabled.")

    def execute(self, action: Dict[str, Any]) -> ActionResult:
        """
        Execute a single action.

        Args:
            action: Action dictionary from Fara with 'action' key and parameters

        Returns:
            ActionResult with success status and details
        """
        action_type = action.get("action", "")

        try:
            if action_type == "left_click":
                return self._execute_click(action)
            elif action_type == "mouse_move":
                return self._execute_mouse_move(action)
            elif action_type == "type":
                return self._execute_type(action)
            elif action_type == "key":
                return self._execute_key(action)
            elif action_type == "scroll":
                return self._execute_scroll(action)
            elif action_type == "visit_url":
                return self._execute_visit_url(action)
            elif action_type == "web_search":
                return self._execute_web_search(action)
            elif action_type == "history_back":
                return self._execute_history_back(action)
            elif action_type == "wait":
                return self._execute_wait(action)
            elif action_type == "pause_and_memorize_fact":
                return self._execute_memorize(action)
            elif action_type == "terminate":
                return self._execute_terminate(action)
            # Extended desktop actions
            elif action_type == "right_click":
                return self._execute_right_click(action)
            elif action_type == "double_click":
                return self._execute_double_click(action)
            elif action_type == "drag":
                return self._execute_drag(action)
            elif action_type == "screenshot":
                return self._execute_screenshot(action)
            elif action_type == "hotkey":
                return self._execute_hotkey(action)
            elif action_type == "open_application":
                return self._execute_open_application(action)
            else:
                return ActionResult(
                    success=False,
                    action=action_type,
                    error=f"Unknown action type: {action_type}",
                )
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return ActionResult(
                success=False,
                action=action_type,
                error=str(e),
            )

    def _execute_click(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a left click at specified coordinates."""
        coords = action.get("coordinate", [])
        if len(coords) != 2:
            return ActionResult(
                success=False,
                action="left_click",
                error="Invalid coordinates",
            )

        x, y = int(coords[0]), int(coords[1])

        if self._pyautogui:
            logger.info(f"Executing click at ({x}, {y})")
            self._pyautogui.click(x, y)
            logger.info(f"Click executed successfully at ({x}, {y})")
            return ActionResult(
                success=True,
                action="left_click",
                details={"x": x, "y": y},
            )
        elif self._page:
            self._page.mouse.click(x, y)
            return ActionResult(
                success=True,
                action="left_click",
                details={"x": x, "y": y},
            )
        else:
            return ActionResult(
                success=False,
                action="left_click",
                error="No automation backend available",
            )

    def _execute_mouse_move(self, action: Dict[str, Any]) -> ActionResult:
        """Move mouse to specified coordinates."""
        coords = action.get("coordinate", [])
        if len(coords) != 2:
            return ActionResult(
                success=False,
                action="mouse_move",
                error="Invalid coordinates",
            )

        x, y = int(coords[0]), int(coords[1])

        if self._pyautogui:
            self._pyautogui.moveTo(x, y)
            return ActionResult(
                success=True,
                action="mouse_move",
                details={"x": x, "y": y},
            )
        elif self._page:
            self._page.mouse.move(x, y)
            return ActionResult(
                success=True,
                action="mouse_move",
                details={"x": x, "y": y},
            )
        else:
            return ActionResult(
                success=False,
                action="mouse_move",
                error="No automation backend available",
            )

    def _execute_type(self, action: Dict[str, Any]) -> ActionResult:
        """Type text at current position."""
        text = action.get("text", "")
        if not text:
            return ActionResult(
                success=False,
                action="type",
                error="No text provided",
            )

        # First move to coordinates if provided
        coords = action.get("coordinate", [])
        if len(coords) == 2:
            self._execute_click({"action": "left_click", "coordinate": coords})
            time.sleep(0.1)

        if self._pyautogui:
            # Use write() instead of typewrite() for better Unicode/special char support
            # typewrite() has issues with characters like : / etc in URLs
            self._pyautogui.write(text, interval=0.02)
            return ActionResult(
                success=True,
                action="type",
                details={"text": text},
            )
        elif self._page:
            self._page.keyboard.type(text)
            return ActionResult(
                success=True,
                action="type",
                details={"text": text},
            )
        else:
            return ActionResult(
                success=False,
                action="type",
                error="No automation backend available",
            )

    def _execute_key(self, action: Dict[str, Any]) -> ActionResult:
        """Press keyboard keys."""
        keys = action.get("keys", [])
        if not keys:
            return ActionResult(
                success=False,
                action="key",
                error="No keys provided",
            )

        # Map Fara key names to pyautogui key names
        key_map = {
            "Enter": "enter",
            "Alt": "alt",
            "Shift": "shift",
            "Tab": "tab",
            "Control": "ctrl",
            "Backspace": "backspace",
            "Delete": "delete",
            "Escape": "escape",
            "ArrowUp": "up",
            "ArrowDown": "down",
            "ArrowLeft": "left",
            "ArrowRight": "right",
            "PageDown": "pagedown",
            "PageUp": "pageup",
        }

        if self._pyautogui:
            mapped_keys = [key_map.get(k, k.lower()) for k in keys]
            self._pyautogui.hotkey(*mapped_keys)
            return ActionResult(
                success=True,
                action="key",
                details={"keys": keys},
            )
        elif self._page:
            for key in keys:
                self._page.keyboard.press(key)
            return ActionResult(
                success=True,
                action="key",
                details={"keys": keys},
            )
        else:
            return ActionResult(
                success=False,
                action="key",
                error="No automation backend available",
            )

    def _execute_scroll(self, action: Dict[str, Any]) -> ActionResult:
        """Scroll the mouse wheel."""
        pixels = action.get("pixels", 0)

        if self._pyautogui:
            # pyautogui scroll: positive = up, negative = down
            # Convert pixels to scroll clicks (roughly 120 pixels per click)
            clicks = int(pixels / 120) if pixels != 0 else 0
            self._pyautogui.scroll(clicks)
            return ActionResult(
                success=True,
                action="scroll",
                details={"pixels": pixels, "clicks": clicks},
            )
        elif self._page:
            self._page.mouse.wheel(0, -pixels)  # Playwright: negative = down
            return ActionResult(
                success=True,
                action="scroll",
                details={"pixels": pixels},
            )
        else:
            return ActionResult(
                success=False,
                action="scroll",
                error="No automation backend available",
            )

    def _execute_visit_url(self, action: Dict[str, Any]) -> ActionResult:
        """Navigate to a URL."""
        url = action.get("url", "")
        if not url:
            return ActionResult(
                success=False,
                action="visit_url",
                error="No URL provided",
            )

        if self._page:
            self._page.goto(url)
            return ActionResult(
                success=True,
                action="visit_url",
                details={"url": url},
            )
        elif self._pyautogui:
            # For desktop, we'd need to interact with browser address bar
            # This is a simplified approach
            import webbrowser
            webbrowser.open(url)
            time.sleep(1)  # Wait for browser to open
            return ActionResult(
                success=True,
                action="visit_url",
                details={"url": url},
            )
        else:
            return ActionResult(
                success=False,
                action="visit_url",
                error="No automation backend available",
            )

    def _execute_web_search(self, action: Dict[str, Any]) -> ActionResult:
        """Perform a web search."""
        query = action.get("query", "")
        if not query:
            return ActionResult(
                success=False,
                action="web_search",
                error="No query provided",
            )

        # Use Google search
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self._execute_visit_url({"url": search_url})

    def _execute_history_back(self, action: Dict[str, Any]) -> ActionResult:
        """Go back in browser history."""
        if self._page:
            self._page.go_back()
            return ActionResult(success=True, action="history_back")
        elif self._pyautogui:
            # Alt+Left for browser back
            self._pyautogui.hotkey("alt", "left")
            return ActionResult(success=True, action="history_back")
        else:
            return ActionResult(
                success=False,
                action="history_back",
                error="No automation backend available",
            )

    def _execute_wait(self, action: Dict[str, Any]) -> ActionResult:
        """Wait for specified time."""
        wait_time = action.get("time", 1)
        time.sleep(wait_time)
        return ActionResult(
            success=True,
            action="wait",
            details={"seconds": wait_time},
        )

    def _execute_memorize(self, action: Dict[str, Any]) -> ActionResult:
        """Memorize a fact (handled by FaraModelManager)."""
        fact = action.get("fact", "")
        return ActionResult(
            success=True,
            action="pause_and_memorize_fact",
            details={"fact": fact},
        )

    def _execute_terminate(self, action: Dict[str, Any]) -> ActionResult:
        """Terminate the task."""
        status = action.get("status", "success")
        return ActionResult(
            success=True,
            action="terminate",
            details={"status": status},
        )

    # Extended desktop actions for general computer use

    def _execute_right_click(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a right click at specified coordinates."""
        coords = action.get("coordinate", [])
        if len(coords) != 2:
            return ActionResult(
                success=False,
                action="right_click",
                error="Invalid coordinates",
            )

        x, y = int(coords[0]), int(coords[1])

        if self._pyautogui:
            self._pyautogui.rightClick(x, y)
            return ActionResult(
                success=True,
                action="right_click",
                details={"x": x, "y": y},
            )
        else:
            return ActionResult(
                success=False,
                action="right_click",
                error="No automation backend available",
            )

    def _execute_double_click(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a double click at specified coordinates."""
        coords = action.get("coordinate", [])
        if len(coords) != 2:
            return ActionResult(
                success=False,
                action="double_click",
                error="Invalid coordinates",
            )

        x, y = int(coords[0]), int(coords[1])

        if self._pyautogui:
            self._pyautogui.doubleClick(x, y)
            return ActionResult(
                success=True,
                action="double_click",
                details={"x": x, "y": y},
            )
        else:
            return ActionResult(
                success=False,
                action="double_click",
                error="No automation backend available",
            )

    def _execute_drag(self, action: Dict[str, Any]) -> ActionResult:
        """Drag from one coordinate to another."""
        start = action.get("start_coordinate", [])
        end = action.get("end_coordinate", action.get("coordinate", []))

        if len(start) != 2 or len(end) != 2:
            return ActionResult(
                success=False,
                action="drag",
                error="Invalid coordinates (need start_coordinate and end_coordinate)",
            )

        start_x, start_y = int(start[0]), int(start[1])
        end_x, end_y = int(end[0]), int(end[1])

        if self._pyautogui:
            self._pyautogui.moveTo(start_x, start_y)
            self._pyautogui.drag(end_x - start_x, end_y - start_y, duration=0.5)
            return ActionResult(
                success=True,
                action="drag",
                details={
                    "start": {"x": start_x, "y": start_y},
                    "end": {"x": end_x, "y": end_y},
                },
            )
        else:
            return ActionResult(
                success=False,
                action="drag",
                error="No automation backend available",
            )

    def _execute_screenshot(self, action: Dict[str, Any]) -> ActionResult:
        """Take a screenshot (for debugging or saving)."""
        if self._pyautogui:
            screenshot = self._pyautogui.screenshot()
            save_path = action.get("save_path")
            if save_path:
                screenshot.save(save_path)
            return ActionResult(
                success=True,
                action="screenshot",
                details={"saved": save_path is not None},
                screenshot_after=screenshot,
            )
        else:
            return ActionResult(
                success=False,
                action="screenshot",
                error="No automation backend available",
            )

    def _execute_hotkey(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a keyboard hotkey combination."""
        keys = action.get("keys", [])
        if not keys:
            return ActionResult(
                success=False,
                action="hotkey",
                error="No keys provided",
            )

        if self._pyautogui:
            # Map common key names
            key_map = {
                "Control": "ctrl",
                "Alt": "alt",
                "Shift": "shift",
                "Enter": "enter",
                "Tab": "tab",
                "Escape": "escape",
                "Backspace": "backspace",
                "Delete": "delete",
                "ArrowUp": "up",
                "ArrowDown": "down",
                "ArrowLeft": "left",
                "ArrowRight": "right",
            }
            mapped_keys = [key_map.get(k, k.lower()) for k in keys]
            self._pyautogui.hotkey(*mapped_keys)
            return ActionResult(
                success=True,
                action="hotkey",
                details={"keys": keys},
            )
        else:
            return ActionResult(
                success=False,
                action="hotkey",
                error="No automation backend available",
            )

    def _execute_open_application(self, action: Dict[str, Any]) -> ActionResult:
        """Open an application by name or path.
        
        This works differently on different OSes:
        - Linux: Uses xdg-open or direct execution
        - macOS: Uses 'open -a'
        - Windows: Uses 'start' or direct execution
        """
        app_name = action.get("application", action.get("app", ""))
        if not app_name:
            return ActionResult(
                success=False,
                action="open_application",
                error="No application name provided",
            )

        import subprocess
        import platform

        try:
            system = platform.system()
            
            if system == "Linux":
                # Try common Linux app launchers
                try:
                    subprocess.Popen(
                        ["gtk-launch", app_name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    # Fall back to direct execution
                    subprocess.Popen(
                        [app_name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", app_name])
            elif system == "Windows":
                subprocess.Popen(["start", "", app_name], shell=True)
            else:
                subprocess.Popen([app_name])

            time.sleep(1)  # Wait for app to start
            return ActionResult(
                success=True,
                action="open_application",
                details={"application": app_name},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="open_application",
                error=str(e),
            )


class FaraScreenCapture:
    """
    Handles screenshot capture for Fara.

    Supports both full screen capture and window-specific capture.
    """

    def __init__(self, debug_screenshot_dir: Optional[str] = None):
        """Initialize screen capture.
        
        Args:
            debug_screenshot_dir: If provided, save screenshots to this directory for debugging.
        """
        self._pyautogui = None
        self._debug_dir = debug_screenshot_dir
        self._screenshot_count = 0
        
        # Create debug directory if specified
        if self._debug_dir:
            from pathlib import Path
            Path(self._debug_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Debug screenshots will be saved to: {self._debug_dir}")
        
        try:
            # Suppress the tkinter NOTE from MouseInfo by redirecting stdout/stderr
            import sys
            import io
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            try:
                import pyautogui
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            self._pyautogui = pyautogui
        except ImportError:
            logger.warning("pyautogui not installed. Screenshot capture disabled.")

    def capture_screen(self) -> Optional[Image.Image]:
        """Capture the entire screen."""
        if self._pyautogui:
            screenshot = self._pyautogui.screenshot()
            
            # Save debug screenshot if enabled
            if self._debug_dir and screenshot:
                self._screenshot_count += 1
                from pathlib import Path
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{self._screenshot_count:03d}_{timestamp}.png"
                filepath = Path(self._debug_dir) / filename
                screenshot.save(filepath)
                logger.info(f"Saved debug screenshot: {filepath}")
            
            return screenshot
        return None

    def capture_region(
        self, x: int, y: int, width: int, height: int
    ) -> Optional[Image.Image]:
        """Capture a specific region of the screen."""
        if self._pyautogui:
            return self._pyautogui.screenshot(region=(x, y, width, height))
        return None

    def get_screen_size(self) -> tuple:
        """Get the screen resolution.
        
        Tries multiple methods to detect actual screen size:
        1. pyautogui (if available)
        2. PySide6/Qt (if available)
        3. xrandr on Linux
        4. Default fallback
        """
        # Method 1: pyautogui
        if self._pyautogui:
            return self._pyautogui.size()
        
        # Method 2: Try PySide6/Qt
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QGuiApplication
            
            app = QApplication.instance() or QGuiApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    geometry = screen.geometry()
                    return (geometry.width(), geometry.height())
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to get screen size via Qt: {e}")
        
        # Method 3: Try xrandr on Linux
        try:
            import subprocess
            result = subprocess.run(
                ["xrandr", "--current"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Look for "connected primary WIDTHxHEIGHT" or just "connected WIDTHxHEIGHT"
                match = re.search(r'connected\s+(?:primary\s+)?(\d+)x(\d+)', result.stdout)
                if match:
                    return (int(match.group(1)), int(match.group(2)))
        except Exception as e:
            logger.debug(f"Failed to get screen size via xrandr: {e}")
        
        # Default fallback - log a warning
        logger.warning(
            "Could not detect screen resolution. Using default 1920x1080. "
            "Install pyautogui for accurate screen detection: pip install airunner[computer_use]"
        )
        return (1920, 1080)


class FaraController:
    """
    Main controller for Fara computer use agent.

    Manages the loop of:
    1. Capture screenshot
    2. Get next action from Fara
    3. Execute action
    4. Repeat until complete or critical point
    """

    def __init__(
        self,
        fara_manager: Optional[Any] = None,
        action_executor: Optional[FaraActionExecutor] = None,
        screen_capture: Optional[FaraScreenCapture] = None,
        max_steps: int = 50,
        step_delay: float = 2.0,
        on_step_callback: Optional[Callable[[int, Dict], None]] = None,
        on_critical_point_callback: Optional[Callable[[CriticalPointType], bool]] = None,
    ):
        """
        Initialize the Fara controller.

        Args:
            fara_manager: FaraModelManager instance (will be created if None)
            action_executor: FaraActionExecutor instance
            screen_capture: FaraScreenCapture instance
            max_steps: Maximum steps before forced termination
            step_delay: Delay between steps in seconds
            on_step_callback: Called after each step with (step_num, action)
            on_critical_point_callback: Called at critical points, returns True to continue
        """
        self._fara_manager = fara_manager
        self._action_executor = action_executor or FaraActionExecutor()
        self._screen_capture = screen_capture or FaraScreenCapture()
        self._max_steps = max_steps
        self._step_delay = step_delay
        self._on_step_callback = on_step_callback
        self._on_critical_point_callback = on_critical_point_callback

        self._current_task: Optional[str] = None
        self._status = TaskStatus.NOT_STARTED
        self._steps_taken = 0

    def _ensure_fara_loaded(self) -> bool:
        """Ensure the Fara model is loaded."""
        if self._fara_manager is None:
            try:
                from airunner.components.llm.managers.fara_model_manager import (
                    FaraModelManager,
                )
                self._fara_manager = FaraModelManager()
            except Exception as e:
                logger.error(f"Failed to create FaraModelManager: {e}")
                return False

        if self._fara_manager._model is None:
            self._fara_manager.load()

        # Update screen resolution
        screen_size = self._screen_capture.get_screen_size()
        self._fara_manager.set_screen_resolution(*screen_size)

        return self._fara_manager._model is not None

    def execute_task(
        self,
        goal: str,
        initial_context: Optional[str] = None,
    ) -> TaskResult:
        """
        Execute a task using Fara.

        Args:
            goal: The task/goal description
            initial_context: Optional additional context

        Returns:
            TaskResult with execution details
        """
        logger.info(f"Starting Fara task: {goal}")

        if not self._ensure_fara_loaded():
            return TaskResult(
                status=TaskStatus.FAILURE,
                goal=goal,
                steps_taken=0,
                error="Failed to load Fara model",
            )

        self._current_task = goal
        self._status = TaskStatus.RUNNING
        self._steps_taken = 0

        # Reset Fara's session
        self._fara_manager.reset_session()

        try:
            while self._status == TaskStatus.RUNNING:
                if self._steps_taken >= self._max_steps:
                    logger.warning(f"Max steps ({self._max_steps}) reached")
                    self._status = TaskStatus.FAILURE
                    break

                # 1. Capture screenshot
                screenshot = self._screen_capture.capture_screen()
                if screenshot is None:
                    logger.error("Failed to capture screenshot")
                    self._status = TaskStatus.FAILURE
                    break

                # 2. Get next action from Fara
                result = self._fara_manager.get_next_action(
                    screenshot=screenshot,
                    goal=goal,
                    additional_context=initial_context if self._steps_taken == 0 else None,
                )

                if "error" in result:
                    logger.error(f"Fara error: {result['error']}")
                    self._status = TaskStatus.FAILURE
                    break

                action = result.get("action", {})
                thought = result.get("thought", "")

                # Check if action has an error
                if isinstance(action, dict) and "error" in action:
                    logger.error(f"Action parsing error: {action['error']}")
                    logger.debug(f"Raw response: {result.get('raw_response', 'N/A')[:500]}")
                    self._status = TaskStatus.FAILURE
                    break

                logger.info(f"Step {self._steps_taken + 1}: {thought[:100] if thought else 'No thought'}...")
                logger.debug(f"Action: {action}")

                # 3. Check for repeated actions and potentially intervene
                action_history = self._fara_manager.get_action_history()
                action_type = action.get("action", "")
                goal_lower = goal.lower()
                
                # Helper function to extract URL from goal
                def extract_url_from_goal(goal_text: str) -> Optional[str]:
                    goal_lower_local = goal_text.lower()
                    # Try to match explicit URL patterns
                    url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+|([a-zA-Z0-9-]+\.(com|org|net|io|gov|edu)[^\s]*))', goal_text)
                    if url_match:
                        extracted = url_match.group(0)
                        if not extracted.startswith('http'):
                            extracted = 'https://' + extracted.lstrip('www.')
                        return extracted
                    # Try to extract site name from common patterns
                    site_match = re.search(r'(?:to|visit|go to|navigate to|open)\s+(\w+\.(?:com|org|net|io|gov|edu))', goal_lower_local)
                    if site_match:
                        return f"https://{site_match.group(1)}"
                    # Try simpler pattern like "navigate to reddit"
                    site_match = re.search(r'(?:to|visit|go to|navigate to)\s+([a-zA-Z0-9]+)(?:\s|$|\.)', goal_lower_local)
                    if site_match:
                        site_name = site_match.group(1)
                        # Skip common words that aren't websites
                        if site_name not in ['the', 'a', 'an', 'this', 'that', 'firefox', 'chrome', 'browser']:
                            return f"https://www.{site_name}.com"
                    return None
                
                # Validate visit_url actions - make sure URL matches what's in the goal
                if action_type == "visit_url":
                    model_url = action.get("url", "").lower()
                    expected_url = extract_url_from_goal(goal)
                    
                    if expected_url:
                        expected_domain = re.search(r'://(?:www\.)?([^/]+)', expected_url.lower())
                        model_domain = re.search(r'://(?:www\.)?([^/]+)', model_url)
                        
                        if expected_domain and model_domain:
                            expected_site = expected_domain.group(1)
                            model_site = model_domain.group(1)
                            
                            # Check if model is going to wrong URL
                            if expected_site != model_site:
                                logger.warning(
                                    f"Model tried to visit '{model_url}' but goal mentions '{expected_url}'. "
                                    f"Correcting URL."
                                )
                                action["url"] = expected_url
                                logger.info(f"Corrected visit_url to: {expected_url}")
                
                # Check for 2 consecutive identical click actions on a URL task
                if len(action_history) >= 2 and action_type == "left_click":
                    last_two = [h.get("action", {}) for h in action_history[-2:]]
                    if last_two[0] == last_two[1]:
                        # Check if this is a URL navigation task
                        url_keywords = ["url", "navigate", "http", ".com", ".org", ".net", "website", "reddit", "google", "facebook", "open firefox", "open chrome"]
                        if any(kw in goal_lower for kw in url_keywords):
                            logger.warning(
                                f"Detected 2 consecutive identical clicks on URL task. "
                                f"Injecting corrective sequence: keyboard shortcut Ctrl+L and type URL"
                            )
                            
                            # Use the helper function to extract URL
                            extracted_url = extract_url_from_goal(goal)
                            
                            if extracted_url:
                                logger.info(f"Extracted URL: {extracted_url}. Injecting Ctrl+L + type sequence.")
                                
                                # First, execute Ctrl+L to focus URL bar
                                focus_result = self._action_executor.execute({
                                    "action": "hotkey",
                                    "keys": ["Control", "l"]
                                })
                                logger.debug(f"Ctrl+L result: {focus_result}")
                                
                                time.sleep(0.3)  # Brief pause for URL bar to focus
                                
                                # Now type the URL and press Enter
                                type_result = self._action_executor.execute({
                                    "action": "type",
                                    "text": extracted_url
                                })
                                logger.debug(f"Type URL result: {type_result}")
                                
                                time.sleep(0.3)  # Brief pause after typing
                                
                                # Press Enter to navigate
                                enter_result = self._action_executor.execute({
                                    "action": "key",
                                    "keys": ["Enter"]
                                })
                                logger.info(f"Injected complete sequence: Ctrl+L, type '{extracted_url}', Enter")
                                logger.debug(f"Enter result: {enter_result}")
                                
                                # Task is complete - we successfully navigated to the URL
                                # Add a longer delay to let the page load
                                time.sleep(2.0)
                                logger.info(f"URL navigation task complete. Navigated to {extracted_url}. BREAKING LOOP NOW.")
                                self._status = TaskStatus.SUCCESS
                                # Explicit break to exit the while loop
                                break  # <-- This MUST exit the while loop
                            else:
                                # Fallback: just click URL bar
                                screen_width = self._fara_manager._screen_width
                                url_bar_x = screen_width // 2
                                url_bar_y = 80
                                action = {
                                    "action": "left_click",
                                    "coordinate": [url_bar_x, url_bar_y]
                                }
                                logger.info(f"Injected corrective action: click URL bar at ({url_bar_x}, {url_bar_y})")
                
                # Force terminate after 3 consecutive identical actions
                if len(action_history) >= 3:
                    last_three = [h.get("action", {}) for h in action_history[-3:]]
                    if last_three[0] == last_three[1] == last_three[2]:
                        logger.warning(
                            f"Detected 3 consecutive identical actions: {last_three[0]}. "
                            f"Force terminating as task is likely stuck or complete."
                        )
                        self._status = TaskStatus.SUCCESS
                        break

                # 4. Check for critical point or termination
                action_type = action.get("action", "")

                if action_type == "terminate":
                    status = action.get("status", "success")
                    self._status = (
                        TaskStatus.SUCCESS if status == "success"
                        else TaskStatus.FAILURE
                    )
                    break

                # 4. Execute the action
                action_result = self._action_executor.execute(action)

                if not action_result.success:
                    logger.warning(f"Action failed: {action_result.error}")
                    # Don't fail immediately, let Fara try to recover

                self._steps_taken += 1

                # 5. Callback
                if self._on_step_callback:
                    self._on_step_callback(self._steps_taken, {
                        "thought": thought,
                        "action": action,
                        "result": action_result,
                    })

                # 6. Delay before next step - extra delay for click actions that may launch apps
                delay = self._step_delay
                if action_type in ("left_click", "double_click", "open_application", "visit_url"):
                    delay = max(delay, 0.2)  # At least 1 second for app launches
                time.sleep(delay)

        except Exception as e:
            import traceback
            logger.error(f"Task execution error: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self._status = TaskStatus.FAILURE
            return TaskResult(
                status=TaskStatus.FAILURE,
                goal=goal,
                steps_taken=self._steps_taken,
                error=str(e),
            )

        # Build final result
        final_screenshot = self._screen_capture.capture_screen()

        return TaskResult(
            status=self._status,
            goal=goal,
            steps_taken=self._steps_taken,
            action_history=self._fara_manager.get_action_history(),
            memorized_facts=self._fara_manager.get_memorized_facts(),
            final_screenshot=final_screenshot,
        )

    def cancel_task(self) -> None:
        """Cancel the current task."""
        if self._status == TaskStatus.RUNNING:
            self._status = TaskStatus.CANCELLED
            logger.info("Task cancelled")

    def pause_task(self) -> None:
        """Pause the current task."""
        if self._status == TaskStatus.RUNNING:
            self._status = TaskStatus.PAUSED
            logger.info("Task paused")

    def resume_task(self) -> None:
        """Resume a paused task."""
        if self._status == TaskStatus.PAUSED:
            self._status = TaskStatus.RUNNING
            logger.info("Task resumed")

    @property
    def status(self) -> TaskStatus:
        """Get the current task status."""
        return self._status

    @property
    def steps_taken(self) -> int:
        """Get the number of steps taken."""
        return self._steps_taken
