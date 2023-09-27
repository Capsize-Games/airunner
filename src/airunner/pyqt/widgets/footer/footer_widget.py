import psutil
import torch

from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.footer.footer import Ui_footer_widget
from airunner.themes import Themes


class FooterWidget(BaseWidget):
    widget_class_ = Ui_footer_widget

    def set_stylesheet(self):
        color = "#ffffff" if \
            self.settings_manager.dark_mode_enabled else "#000000"
        self.ui.status_label.setStyleSheet(f"color: {color};")
        self.ui.setStyleSheet(Themes().css("footer_widget"))

    def update_system_stats(self, queue_size):
        system_memory_percentage = psutil.virtual_memory().percent
        has_cuda = torch.cuda.is_available()
        queue_items = f"Queued items: {queue_size}"
        cuda_memory = f"Using {'GPU' if has_cuda else 'CPU'}, VRAM allocated {torch.cuda.memory_allocated() / 1024 ** 3:.1f}GB cached {torch.cuda.memory_cached() / 1024 ** 3:.1f}GB"
        system_memory = f"RAM {system_memory_percentage:.1f}%"
        self.ui.system_status.setText(f"{queue_items}, {system_memory}, {cuda_memory}")