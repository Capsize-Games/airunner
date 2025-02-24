from PySide6.QtCore import QTimer, Slot

from airunner.data.models import Lora
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.lora_trigger_word_widget import LoraTriggerWordWidget
from airunner.widgets.lora.templates.lora_ui import Ui_lora


class LoraWidget(BaseWidget):
    """
    This class represents a single lora.
    It is responsible for displaying the lora's name, trigger words,
    and active status.
    """
    widget_class_ = Ui_lora

    def __init__(self, *args, **kwargs):
        self.icons = [
            ("recycle-bin-line-icon", "delete_button"),
        ]
        self.current_lora:Lora = kwargs.pop("lora")
        super().__init__(*args, **kwargs)
        name = self.current_lora.name
        enabled = self.current_lora.enabled
        trigger_word = self.current_lora.trigger_word

        # Block signals for batch updates
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.trigger_word_edit.blockSignals(True)

        self.ui.enabledCheckbox.setText(name)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(trigger_word)

        # Unblock signals after batch updates
        self.ui.enabledCheckbox.blockSignals(False)
        self.ui.trigger_word_edit.blockSignals(False)

        # Defer the creation of trigger word widgets
        self.create_trigger_word_widgets(self.current_lora, defer=True)

        self.ui.scale_slider.setProperty("table_id", self.current_lora.id)

    def disable_lora_widget(self):
        self.ui.enabledCheckbox.setEnabled(False)
        self.ui.delete_button.setEnabled(False)
        self.ui.scale_slider.setEnabled(False)

    def enable_lora_widget(self):
        self.ui.enabledCheckbox.setEnabled(True)
        self.ui.delete_button.setEnabled(True)
        self.ui.scale_slider.setEnabled(True)

    @Slot(bool)
    def action_toggled_lora_enabled(self, val):
        self.current_lora.enabled = val
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.enabledCheckbox.setChecked(val)
        self.ui.enabledCheckbox.blockSignals(False)
        self.update_lora(self.current_lora)
        self.emit_signal(SignalCode.LORA_STATUS_CHANGED)

    @Slot(str)
    def action_text_changed_trigger_word(self, val):
        self.current_lora.trigger_word = val
        self.update_lora(self.current_lora)

    @Slot()
    def action_clicked_button_deleted(self):
        self.emit_signal(
            SignalCode.LORA_DELETE_SIGNAL,
            {
                "lora_widget": self
            }
        )

    def create_trigger_word_widgets(self, lora, defer=False):
        if defer:
            # Defer the creation of trigger word widgets
            QTimer.singleShot(0, lambda: self._create_trigger_word_widgets(lora))
        else:
            self._create_trigger_word_widgets(lora)

    def _create_trigger_word_widgets(self, lora):
        for i in reversed(range(self.ui.lora_container.layout().count())):
            widget = self.ui.lora_container.layout().itemAt(i).widget()
            if isinstance(widget, LoraTriggerWordWidget):
                widget.deleteLater()
        for word in lora.trigger_word.split(","):
            if word.strip() == "":
                continue
            widget = LoraTriggerWordWidget(trigger_word=word)
            self.ui.lora_container.layout().addWidget(widget)

    def action_changed_trigger_words(self, val):
        self.current_lora.trigger_word = val
        self.update_lora(self.current_lora)
        self.create_trigger_word_widgets(self.current_lora)
