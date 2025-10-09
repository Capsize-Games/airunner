from typing import Optional
import os
import subprocess
import psutil
import torch
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats
import json
from requests_cache import Dict
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QTimer
from airunner.components.home_stage.gui.widgets.home_bridge import HomeBridge
from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.enums import TemplateName, SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.models.document import Document

try:
    from importlib.metadata import version as pkg_version
except ImportError:
    from importlib_metadata import version as pkg_version  # type: ignore


class HomeStageWidget(BaseWidget):
    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.RAG_INDEXING_PROGRESS: self.on_indexing_progress,
            SignalCode.RAG_INDEXING_COMPLETE: self.on_indexing_complete,
        }
        super().__init__(*args, **kwargs)

        # Set up QWebChannel bridge
        self._web_channel = QWebChannel(self.ui.webEngineView.page())
        self._home_bridge = HomeBridge()
        self._home_bridge.updateStatsRequested.connect(
            self._handle_update_stats_request
        )
        self._home_bridge.indexAllDocumentsRequested.connect(
            self._handle_index_all_request
        )
        self._home_bridge.cancelIndexRequested.connect(
            self._handle_cancel_index_request
        )
        self._web_channel.registerObject("homeBridge", self._home_bridge)
        self.ui.webEngineView.page().setWebChannel(self._web_channel)

        # Timer for system stats updates
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_system_stats)
        self._stats_timer.start(1000)  # Update every second

    def _handle_update_stats_request(self):
        """Handle JavaScript request to update document stats."""
        self._update_document_stats()

    def _handle_index_all_request(self):
        """Handle JavaScript request to index all unindexed documents."""
        if hasattr(self, "logger"):
            self.logger.info(
                "_handle_index_all_request invoked from JS - emitting RAG_INDEX_ALL_DOCUMENTS signal"
            )

        # Emit initial progress to show loading/preparation
        try:
            initial_progress = {
                "progress": 0,
                "current": 0,
                "total": 0,
                "documentName": "Initializing...",
            }
            js_payload = json.dumps(initial_progress)
            js = f"window.updateIndexingProgress && window.updateIndexingProgress({js_payload});"
            self.ui.webEngineView.page().runJavaScript(js)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.debug(f"Failed to send initial progress: {e}")

        self.emit_signal(SignalCode.RAG_INDEX_ALL_DOCUMENTS, {})

    def _handle_cancel_index_request(self):
        """Handle JavaScript request to cancel indexing."""
        # Emit a cancel signal to any listeners (worker/agent)
        self.emit_signal(SignalCode.RAG_INDEX_CANCEL, {})

    def _update_document_stats(self):
        """Calculate and send document stats to JavaScript."""
        try:
            all_docs = Document.objects.all()
            total_count = len(all_docs)
            indexed_count = len([d for d in all_docs if d.indexed])
            unindexed_count = total_count - indexed_count

            stats = {
                "total": total_count,
                "indexed": indexed_count,
                "unindexed": unindexed_count,
            }

            # Log the stats for debugging
            if hasattr(self, "logger"):
                self.logger.info(f"Document stats: {stats}")
                self.logger.info(f"All docs count: {len(all_docs)}")
                if len(all_docs) > 0:
                    self.logger.info(f"Sample doc: {all_docs[0]}")

            # Send stats to JavaScript (convert dict to JSON)
            js = f"window.updateDocumentStats && window.updateDocumentStats({json.dumps(stats)});"
            self.ui.webEngineView.page().runJavaScript(js)

            # Log the JavaScript being executed
            if hasattr(self, "logger"):
                self.logger.info(f"Executing JS: {js}")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error updating document stats: {e}")

    def _update_system_stats(self):
        """Calculate and send system stats to JavaScript."""
        try:
            devices = []

            # Get GPU stats
            device_count = torch.cuda.device_count()

            # Get nvidia-smi stats
            nvidia_smi_stats = []
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                for line in result.stdout.strip().split("\n"):
                    used, total = line.split(",")
                    nvidia_smi_stats.append(
                        (
                            float(used.strip()) / 1024,
                            float(total.strip()) / 1024,
                        )
                    )  # Convert MB to GB
            except Exception:
                nvidia_smi_stats = [(0, 0)] * device_count

            for i in range(device_count):
                device = torch.device(f"cuda:{i}")
                try:
                    torch.cuda.set_device(device)
                    stats = gpu_memory_stats(device)
                    free_mem = stats["free"]
                    device_name = stats["device_name"]

                    nvidia_used, nvidia_total = (
                        nvidia_smi_stats[i]
                        if i < len(nvidia_smi_stats)
                        else (0, 0)
                    )
                    used_mem = (
                        round(nvidia_used, 2)
                        if nvidia_used
                        else round(stats["allocated"], 2)
                    )
                    total_mem = (
                        round(nvidia_total, 2)
                        if nvidia_total
                        else round(stats["total"], 2)
                    )
                    free_mem = round(free_mem, 2)

                    devices.append(
                        {
                            "name": device_name,
                            "used": used_mem,
                            "total": total_mem,
                            "free": free_mem,
                            "type": "gpu",
                        }
                    )
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.debug(f"Error getting GPU {i} stats: {e}")

            # Get CPU stats
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                used = round(memory_info.rss / (1024.0**3), 2)
                total = round(psutil.virtual_memory().total / (1024.0**3), 2)
                available = round(total - used, 2)

                devices.append(
                    {
                        "name": "CPU (RAM)",
                        "used": used,
                        "total": total,
                        "free": available,
                        "type": "cpu",
                    }
                )
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.debug(f"Error getting CPU stats: {e}")

            # Send to JavaScript
            js = f"window.updateSystemStats && window.updateSystemStats({json.dumps(devices)});"
            self.ui.webEngineView.page().runJavaScript(js)

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error updating system stats: {e}")

    def on_indexing_progress(self, data: Dict):
        """Handle indexing progress updates."""
        if hasattr(self, "logger"):
            self.logger.debug(f"on_indexing_progress called with data: {data}")

        progress = data.get("progress", 0)
        current = data.get("current", 0)
        total = data.get("total", 0)
        document_name = data.get("document_name", "")

        progress_data = {
            "progress": progress,
            "current": current,
            "total": total,
            "documentName": document_name,
        }

        # Send progress to JavaScript
        # Use json.dumps to safely serialize payload into JS
        try:
            js_payload = json.dumps(progress_data)
            js = f"window.updateIndexingProgress && window.updateIndexingProgress({js_payload});"
            if hasattr(self, "logger"):
                self.logger.debug(f"Sending progress to JS: {js}")
            self.ui.webEngineView.page().runJavaScript(js)
        except Exception:
            # Fallback: build minimal payload safely
            try:
                fallback = {
                    "progress": progress,
                    "current": current,
                    "total": total,
                }
                js = f"window.updateIndexingProgress && window.updateIndexingProgress({json.dumps(fallback)});"
                self.ui.webEngineView.page().runJavaScript(js)
            except Exception:
                # Last-resort simple numeric update
                js = f"window.updateIndexingProgress && window.updateIndexingProgress({{progress: {progress}}});"
                self.ui.webEngineView.page().runJavaScript(js)

    def on_indexing_complete(self, data: Dict):
        """Handle indexing completion."""
        success = data.get("success", True)
        message = data.get("message", "Indexing complete")

        # Update stats after indexing
        self._update_document_stats()

        # Notify JavaScript
        try:
            js_payload = json.dumps({"success": success, "message": message})
            js = f"window.onIndexingComplete && window.onIndexingComplete({js_payload});"
            self.ui.webEngineView.page().runJavaScript(js)
        except Exception:
            js = f"window.onIndexingComplete && window.onIndexingComplete({{success: {str(success).lower()}, message: '{message}'}});"
            self.ui.webEngineView.page().runJavaScript(js)

    @property
    def web_engine_view(self) -> Optional[object]:
        return self.ui.webEngineView

    @property
    def template(self) -> Optional[str]:
        return "home.jinja2.html"

    @property
    def template_context(self) -> Dict:
        context = super().template_context
        context["version"] = pkg_version("airunner")
        return context

    def on_theme_changed_signal(self, data: Dict):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        if hasattr(self.ui, "webEngineView"):
            theme_name = data.get(
                "template", TemplateName.SYSTEM_DEFAULT
            ).value.lower()
            # Set window.currentTheme before calling setTheme
            js = f"window.currentTheme = '{theme_name}'; window.setTheme && window.setTheme('{theme_name}');"
            self.ui.webEngineView.page().runJavaScript(js)
        super().on_theme_changed_signal(data)
