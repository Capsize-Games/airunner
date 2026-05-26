"""File-based GUI probe support for interactive debugging."""

from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget


class GuiProbeController(QObject):
    """Execute simple GUI probe commands on a live main window."""

    def __init__(self, main_window: QWidget, probe_dir: str) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._root_dir = Path(probe_dir)
        self._commands_dir = self._root_dir / "commands"
        self._responses_dir = self._root_dir / "responses"
        self._artifacts_dir = self._root_dir / "artifacts"
        self._ensure_directories()
        self._timer = QTimer(self)
        self._timer.setInterval(self._poll_interval_ms())
        self._timer.timeout.connect(self._poll_commands)
        self._timer.start()
        self._write_ready_file()

    def _ensure_directories(self) -> None:
        self._commands_dir.mkdir(parents=True, exist_ok=True)
        self._responses_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _poll_interval_ms(self) -> int:
        value = os.environ.get("AIRUNNER_GUI_PROBE_POLL_MS", "100")
        try:
            return max(25, int(value))
        except ValueError:
            return 100

    def _write_ready_file(self) -> None:
        payload = {
            "pid": os.getpid(),
            "ready_at": time.time(),
            "window": self._widget_state(self._main_window),
        }
        ready_path = self._root_dir / "ready.json"
        ready_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _poll_commands(self) -> None:
        for command_path in sorted(self._commands_dir.glob("*.json")):
            self._process_command_file(command_path)
            return

    def _process_command_file(self, command_path: Path) -> None:
        response = {
            "id": command_path.stem,
            "action": "unknown",
            "ok": False,
        }
        try:
            command = json.loads(command_path.read_text(encoding="utf-8"))
            response["id"] = command.get("id", command_path.stem)
            response["action"] = command.get("action", "unknown")
            response["ok"] = True
            response["result"] = self._execute(command)
        except Exception as exc:
            response["error"] = str(exc)
            response["traceback"] = traceback.format_exc(limit=8)
        response_path = self._responses_dir / f"{response['id']}.json"
        response_path.write_text(
            json.dumps(response, indent=2),
            encoding="utf-8",
        )
        command_path.unlink(missing_ok=True)

    def _execute(self, command: dict[str, Any]) -> dict[str, Any]:
        action = command.get("action")
        if action == "ping":
            return self._widget_state(self._main_window)
        if action == "click":
            widget = self._require_widget(command.get("object_name", ""))
            self._click_widget(widget)
            return self._widget_state(widget)
        if action == "widget_state":
            widget = self._require_widget(command.get("object_name", ""))
            return self._widget_state(widget)
        if action == "dump_widget_tree":
            return self._dump_widget_tree(command.get("artifact"))
        if action == "screenshot":
            return self._save_screenshot(command.get("artifact"))
        raise ValueError(f"Unsupported probe action: {action}")

    def _dump_widget_tree(self, artifact_name: Any) -> dict[str, str]:
        artifact = self._artifact_path(artifact_name, "widget-tree.json")
        tree = self._widget_tree()
        artifact.write_text(json.dumps(tree, indent=2), encoding="utf-8")
        return {"artifact": str(artifact)}

    def _save_screenshot(self, artifact_name: Any) -> dict[str, Any]:
        artifact = self._artifact_path(artifact_name, "screenshot.png")
        saved = self._main_window.grab().save(str(artifact))
        return {"artifact": str(artifact), "saved": bool(saved)}

    def _artifact_path(self, requested: Any, default_name: str) -> Path:
        name = str(requested or default_name)
        return self._artifacts_dir / name

    def _require_widget(self, object_name: str) -> QWidget:
        if not object_name:
            raise ValueError("Probe command is missing object_name")
        widget = self._main_window.findChild(QWidget, object_name)
        if widget is None:
            raise LookupError(f"Widget not found: {object_name}")
        return widget

    def _click_widget(self, widget: QWidget) -> None:
        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=widget.rect().center(),
        )
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def _widget_tree(self) -> list[dict[str, Any]]:
        widgets = [self._main_window, *self._main_window.findChildren(QWidget)]
        return [self._widget_state(widget) for widget in widgets]

    def _widget_state(self, widget: QWidget) -> dict[str, Any]:
        checked = None
        if hasattr(widget, "isChecked") and callable(widget.isChecked):
            try:
                checked = bool(widget.isChecked())
            except Exception:
                checked = None
        text = None
        if hasattr(widget, "text") and callable(widget.text):
            try:
                text = str(widget.text())
            except Exception:
                text = None
        row_count = None
        if hasattr(widget, "rowCount") and callable(widget.rowCount):
            try:
                row_count = int(widget.rowCount())
            except Exception:
                row_count = None
        column_count = None
        if hasattr(widget, "columnCount") and callable(widget.columnCount):
            try:
                column_count = int(widget.columnCount())
            except Exception:
                column_count = None
        geometry = widget.geometry()
        return {
            "object_name": widget.objectName(),
            "class_name": type(widget).__name__,
            "visible": bool(widget.isVisible()),
            "enabled": bool(widget.isEnabled()),
            "checked": checked,
            "text": text,
            "row_count": row_count,
            "column_count": column_count,
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }


def maybe_create_gui_probe_controller(
    main_window: QWidget,
) -> GuiProbeController | None:
    """Create a probe controller only when debug probing is enabled."""
    probe_dir = os.environ.get("AIRUNNER_GUI_PROBE_DIR")
    if not probe_dir:
        return None
    return GuiProbeController(main_window=main_window, probe_dir=probe_dir)