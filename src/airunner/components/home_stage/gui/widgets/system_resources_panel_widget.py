from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QGroupBox, QLabel
from airunner.components.home_stage.gui.widgets.templates.system_resources_panel_ui import (
    Ui_system_resources_panel,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget


class SystemResourcesPanelWidget(BaseWidget):
    """Widget for displaying system resource statistics."""

    widget_class_ = Ui_system_resources_panel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_system_stats)
        self._timer.start(1000)
        self._device_cards = []
        self.update_system_stats()

    def update_system_stats(self):
        """Update system statistics display."""
        try:
            import psutil
            import torch

            self._clear_device_cards()
            scroll_widget = self.ui.devices_scroll_area.widget()
            layout = scroll_widget.layout()

            if layout is None:
                layout = QVBoxLayout(scroll_widget)
                scroll_widget.setLayout(layout)

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            cpu_card = self._create_device_card(
                "CPU",
                f"Usage: {cpu_percent:.1f}%",
                f"Memory: {memory.percent:.1f}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)",
            )
            layout.addWidget(cpu_card)
            self._device_cards.append(cpu_card)

            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    device_name = torch.cuda.get_device_name(i)
                    props = torch.cuda.get_device_properties(i)
                    mem_allocated = torch.cuda.memory_allocated(i) / (1024**3)
                    mem_reserved = torch.cuda.memory_reserved(i) / (1024**3)
                    mem_total = props.total_memory / (1024**3)
                    mem_percent = (
                        (mem_reserved / mem_total) * 100
                        if mem_total > 0
                        else 0
                    )

                    gpu_card = self._create_device_card(
                        f"GPU {i}: {device_name}",
                        f"Memory: {mem_percent:.1f}% ({mem_reserved:.2f}GB / {mem_total:.2f}GB)",
                        f"Allocated: {mem_allocated:.2f}GB",
                    )
                    layout.addWidget(gpu_card)
                    self._device_cards.append(gpu_card)

            layout.addStretch()

        except Exception as e:
            self.logger.error(f"Error updating system stats: {e}")

    def _create_device_card(
        self, title: str, line1: str, line2: str
    ) -> QGroupBox:
        """Create a device card with stats."""
        card = QGroupBox(title)
        card_layout = QVBoxLayout()

        label1 = QLabel(line1)
        label2 = QLabel(line2)

        card_layout.addWidget(label1)
        card_layout.addWidget(label2)
        card.setLayout(card_layout)

        return card

    def _clear_device_cards(self):
        """Clear existing device cards."""
        scroll_widget = self.ui.devices_scroll_area.widget()
        layout = scroll_widget.layout()

        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        self._device_cards.clear()

    def cleanup(self):
        """Stop the timer when widget is destroyed."""
        if self._timer:
            self._timer.stop()
        super().cleanup()
