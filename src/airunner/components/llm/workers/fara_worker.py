"""Fara Computer Use Agent Worker.

This worker handles computer use (USE_COMPUTER) action requests using the
Fara-7B model. It orchestrates screenshot capture, model inference, and
action execution.
"""

import os
import threading
from typing import Dict, Optional, Any

from PySide6.QtWidgets import QApplication

from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
)
from airunner.components.application.workers.worker import Worker
from airunner.components.llm.managers.llm_response import LLMResponse


class FaraWorker(Worker):
    """Worker for Fara-7B computer use agent.

    This worker:
    - Manages the FaraModelManager lifecycle
    - Handles USE_COMPUTER action requests
    - Coordinates screenshot capture and action execution
    - Emits progress and completion signals
    - Handles model download via HuggingFace download dialog
    """

    def __init__(self):
        """Initialize the Fara worker."""
        self._fara_manager = None
        self._fara_manager_lock = threading.Lock()
        self._interrupted = False
        self._current_request_id: Optional[str] = None
        self._download_dialog_showing = False
        self._download_dialog = None
        self._pending_fara_request = None
        self.download_manager = None
        super().__init__()

        # Register for download signals
        self.register(
            SignalCode.FARA_MODEL_DOWNLOAD_REQUIRED,
            self.on_fara_model_download_required_signal,
        )
        self.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            self.on_huggingface_download_complete_signal,
        )

        self.logger.info("FaraWorker initialized")

    @property
    def fara_manager(self):
        """Lazy-load the FaraModelManager.

        Returns:
            FaraModelManager instance
        """
        with self._fara_manager_lock:
            if self._fara_manager is None:
                from airunner.components.llm.managers.fara_model_manager import (
                    FaraModelManager,
                )

                self._fara_manager = FaraModelManager()
            return self._fara_manager

    @property
    def has_manager(self) -> bool:
        """Check if manager exists without creating it.

        Returns:
            True if manager is initialized
        """
        return self._fara_manager is not None

    @property
    def is_loaded(self) -> bool:
        """Check if the Fara model is loaded.

        Returns:
            True if model is loaded
        """
        if not self.has_manager:
            return False
        return self._fara_manager._model is not None

    def load(self, data: Optional[Dict] = None) -> None:
        """Load the Fara model.

        Args:
            data: Optional load configuration
        """
        self.logger.info("Loading Fara model...")
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.LOADING},
        )

        try:
            self.fara_manager.load()
            
            # Check if the model actually loaded by verifying model status
            model_status = self.fara_manager.model_status.get(ModelType.LLM, ModelStatus.UNLOADED)
            if model_status == ModelStatus.LOADED and self.fara_manager._model is not None:
                self.emit_signal(
                    SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                    {"model": ModelType.LLM, "status": ModelStatus.LOADED},
                )
                self.logger.info("Fara model loaded successfully")
            else:
                self.logger.error(f"Fara model failed to load - status: {model_status}, model: {self.fara_manager._model is not None}")
                self.emit_signal(
                    SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                    {"model": ModelType.LLM, "status": ModelStatus.FAILED},
                )
        except Exception as e:
            self.logger.error(f"Failed to load Fara model: {e}")
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": ModelType.LLM, "status": ModelStatus.FAILED},
            )

    def unload(self, data: Optional[Dict] = None) -> None:
        """Unload the Fara model.

        Args:
            data: Optional unload configuration
        """
        if not self.has_manager:
            return

        self.logger.info("Unloading Fara model...")
        try:
            self._fara_manager.unload()
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": ModelType.LLM, "status": ModelStatus.UNLOADED},
            )
            self.logger.info("Fara model unloaded")
        except Exception as e:
            self.logger.error(f"Error unloading Fara model: {e}")

    def on_fara_request_signal(self, message: Dict) -> None:
        """Handle incoming Fara/USE_COMPUTER request.

        Args:
            message: Request message dictionary
        """
        self.logger.info(f"Received Fara request: {list(message.keys())}")

        if self._interrupted:
            self.logger.info("Clearing interrupt flag - new message received")
            self._interrupted = False

        # Store pending request in case download is needed
        self._pending_fara_request = message
        self.add_to_queue(message)

    def on_interrupt_signal(self) -> None:
        """Handle interrupt signal."""
        self._interrupted = True
        self.clear_queue()
        self.logger.info("Fara worker interrupted")

    def on_fara_model_download_required_signal(self, data: Dict) -> None:
        """Handle Fara model download required signal - show download dialog.

        Args:
            data: Dictionary containing model_path, model_name, repo_id
        """
        if self._download_dialog_showing:
            self.logger.debug(
                "Download dialog already showing, ignoring duplicate signal"
            )
            return

        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Fara-7B")
        repo_id = data.get("repo_id", "microsoft/Fara-7B")

        self.logger.info(
            f"Fara model download required: {model_name} at {model_path}"
        )

        if not repo_id:
            self.logger.error("No repo_id provided in download request")
            return

        main_window = self._get_main_window()
        if not main_window:
            return

        self._show_download_dialog(
            main_window,
            model_name,
            model_path,
            repo_id,
        )

    def _get_main_window(self) -> Optional[object]:
        """Get the main application window.

        Returns:
            Main window object or None if not found
        """
        app = QApplication.instance()
        if app is None:
            self.logger.error("No QApplication instance found")
            return None

        for widget in app.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                return widget

        self.logger.error(
            "Cannot show download dialog - main window not found"
        )
        return None

    def _show_download_dialog(
        self,
        main_window: object,
        model_name: str,
        model_path: str,
        repo_id: str,
    ) -> None:
        """Create and show the download dialog.

        Args:
            main_window: Parent window for dialog
            model_name: Display name of the model
            model_path: Path where model will be saved
            repo_id: HuggingFace repository ID
        """
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )
        from airunner.components.llm.managers.download_huggingface import (
            DownloadHuggingFaceModel,
        )
        from airunner.utils.application.create_worker import create_worker

        self._download_dialog_showing = True

        try:
            self._download_dialog = HuggingFaceDownloadDialog(
                parent=main_window,
                model_name=model_name,
                model_path=model_path,
            )

            self.download_manager = create_worker(DownloadHuggingFaceModel)

            self.download_manager.download(
                repo_id=repo_id,
                model_type="fara",
                output_dir=os.path.dirname(model_path),
                setup_quantization=False,  # Fara uses its own quantization
                quantization_bits=4,
            )

            self._download_dialog.show()
        except Exception as e:
            self._download_dialog_showing = False
            self._download_dialog = None
            self.logger.error(f"Error showing download dialog: {e}")

    def on_huggingface_download_complete_signal(self, data: Dict) -> None:
        """Handle HuggingFace download completion.

        After download completes, automatically retry loading the Fara model.

        Args:
            data: Download completion data containing model_path and repo_id
        """
        repo_id = data.get("repo_id", "")

        # Only handle Fara downloads
        if "fara" not in repo_id.lower() and "Fara" not in repo_id:
            return

        self._download_dialog_showing = False
        self._download_dialog = None

        model_path = data.get("model_path", "")
        self.logger.info(
            f"Fara download complete for model at: {model_path} (repo_id: {repo_id})"
        )

        self._emit_download_complete_message()
        self._auto_load_fara_model()

    def _emit_download_complete_message(self) -> None:
        """Emit download completion message to user."""
        message = (
            "📦 Fara model download complete! "
            "Loading model with 4-bit quantization...\n"
        )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            {
                "response": LLMResponse(
                    message=message,
                    is_end_of_message=False,
                )
            },
        )

    def _auto_load_fara_model(self) -> None:
        """Automatically trigger Fara model loading after download and retry pending request."""
        self.logger.info("Triggering automatic Fara model load after download")

        try:
            self.load()

            # Check if model actually loaded
            if not self.is_loaded:
                self.logger.error("Fara model failed to load after download")
                self._pending_fara_request = None
                return

            self.logger.info("Fara model loaded successfully!")

            # If there's a pending request, retry it now
            if self._pending_fara_request:
                self.logger.info(
                    "Retrying pending Fara request after model download"
                )
                self.handle_message(self._pending_fara_request)
                self._pending_fara_request = None
            else:
                self.logger.info("No pending request to retry")
        except Exception as e:
            self.logger.error(f"Error auto-loading Fara model: {e}")
            self._pending_fara_request = None

        if self._fara_manager:
            self._fara_manager.reset_session()

    def handle_message(self, message: Dict) -> None:
        """Process queued messages for Fara generation.

        Args:
            message: Message dictionary to process
        """
        if self._interrupted:
            self.logger.info("Skipping message - worker interrupted")
            return

        self.logger.info(f"FaraWorker handling message: {list(message.keys())}")

        request_data = message.get("request_data", {})
        prompt = request_data.get("prompt", "")
        action = request_data.get("action", LLMActionType.USE_COMPUTER)
        self._current_request_id = message.get("request_id")

        # Ensure model is loaded
        if not self.is_loaded:
            self.load()

        if not self.is_loaded:
            self._emit_error("Failed to load Fara model")
            return

        try:
            result = self._execute_computer_use_task(prompt)
            self._emit_result(result, action)
        except Exception as e:
            self.logger.error(f"Error executing Fara task: {e}", exc_info=True)
            self._emit_error(str(e))

    def _execute_computer_use_task(self, goal: str) -> Dict[str, Any]:
        """Execute a computer use task using Fara.

        Args:
            goal: The task/goal description

        Returns:
            Task result dictionary
        """
        # Check if pyautogui is available and working
        try:
            # Suppress the tkinter warning from MouseInfo by redirecting stdout/stderr
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
            
            # Test that pyautogui can actually access the display
            try:
                pyautogui.size()
            except Exception as display_err:
                error_msg = (
                    f"Computer use cannot access the display: {display_err}\n\n"
                    "Note: Computer use requires a display server (X11/Wayland on Linux) "
                    "and cannot run in headless environments or Docker without display forwarding."
                )
                self.logger.error(error_msg)
                return {
                    "status": "failure",
                    "goal": goal,
                    "steps_taken": 0,
                    "action_history": [],
                    "memorized_facts": [],
                    "error": error_msg,
                }
        except ImportError:
            error_msg = (
                "Computer use requires the 'pyautogui' package which is not installed. "
                "Install it with: pip install airunner[computer_use]\n\n"
                "Note: Computer use also requires a display server (X11/Wayland on Linux) "
                "and cannot run in headless environments or Docker without display forwarding."
            )
            self.logger.error(error_msg)
            return {
                "status": "failure",
                "goal": goal,
                "steps_taken": 0,
                "action_history": [],
                "memorized_facts": [],
                "error": error_msg,
            }
        except Exception as e:
            error_msg = f"Unexpected error initializing computer use: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "status": "failure",
                "goal": goal,
                "steps_taken": 0,
                "action_history": [],
                "memorized_facts": [],
                "error": error_msg,
            }

        try:
            from airunner.components.llm.managers.fara_controller import (
                FaraController,
                FaraScreenCapture,
                FaraActionExecutor,
            )
            
            # Debug screenshot directory - saves to ~/.local/share/airunner/fara_debug/
            import os
            from pathlib import Path
            debug_dir = Path(os.path.expanduser("~/.local/share/airunner/fara_debug"))
            # Clean up old screenshots on new task
            if debug_dir.exists():
                for old_file in debug_dir.glob("screenshot_*.png"):
                    old_file.unlink()
            
            # Create controller with callbacks and debug screenshots
            controller = FaraController(
                fara_manager=self.fara_manager,
                action_executor=FaraActionExecutor(),
                screen_capture=FaraScreenCapture(debug_screenshot_dir=str(debug_dir)),
                on_step_callback=self._on_step_callback,
                on_critical_point_callback=self._on_critical_point_callback,
            )

            # Execute the task
            result = controller.execute_task(goal)
        except Exception as e:
            error_msg = f"Error executing computer use task: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "status": "failure",
                "goal": goal,
                "steps_taken": 0,
                "action_history": [],
                "memorized_facts": [],
                "error": error_msg,
            }

        return {
            "status": result.status.value,
            "goal": result.goal,
            "steps_taken": result.steps_taken,
            "action_history": result.action_history,
            "memorized_facts": result.memorized_facts,
            "error": result.error,
        }

    def _on_step_callback(self, step_num: int, action: Dict) -> None:
        """Callback for each step executed.

        Args:
            step_num: Current step number
            action: Action that was executed
        """
        self.emit_signal(
            SignalCode.FARA_ACTION_EXECUTED,
            {"step": step_num, "action": action},
        )

    def _on_critical_point_callback(self, critical_point_type) -> bool:
        """Callback for critical points.

        Args:
            critical_point_type: Type of critical point encountered

        Returns:
            True to continue, False to stop
        """
        self.emit_signal(
            SignalCode.FARA_CRITICAL_POINT,
            {"type": str(critical_point_type)},
        )
        # For now, stop at critical points (safety first)
        return False

    def _emit_result(self, result: Dict[str, Any], action: LLMActionType) -> None:
        """Emit the task result.

        Args:
            result: Task result dictionary
            action: The action type
        """
        # Build a summary message
        status = result.get("status", "unknown")
        steps = result.get("steps_taken", 0)
        error = result.get("error")

        if error:
            message = f"Task failed: {error}"
        elif status == "success":
            message = f"Task completed successfully in {steps} steps."
        elif status == "critical_point":
            message = f"Task stopped at critical point after {steps} steps. Manual action required."
        else:
            message = f"Task ended with status: {status} after {steps} steps."

        # Include action history summary
        history = result.get("action_history", [])
        if history:
            message += f"\n\nActions taken:\n"
            for i, act in enumerate(history[-5:], 1):  # Last 5 actions
                thought = act.get("thought", "")[:50]
                action_type = act.get("action", {}).get("action", "unknown")
                message += f"{i}. {action_type}: {thought}...\n"

        response = LLMResponse(
            message=message,
            is_end_of_message=True,
            action=action,
            request_id=self._current_request_id,
        )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            {"response": response},
        )

        self.emit_signal(
            SignalCode.FARA_TASK_COMPLETE,
            result,
        )

    def _emit_error(self, error_message: str) -> None:
        """Emit an error response.

        Args:
            error_message: The error message
        """
        response = LLMResponse(
            message=f"Error: {error_message}",
            is_end_of_message=True,
            action=LLMActionType.USE_COMPUTER,
            request_id=self._current_request_id,
        )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            {"response": response},
        )
