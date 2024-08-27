from PySide6.QtCore import QTimer

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
        self.lora = kwargs.pop("lora", None)
        super().__init__(*args, **kwargs)
        name = self.lora["name"]
        enabled = self.lora["enabled"]
        trigger_word = self.lora.get("trigger_word", "")

        # Block signals for batch updates
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.trigger_word_edit.blockSignals(True)

        self.ui.enabledCheckbox.setTitle(name)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(trigger_word)

        # Unblock signals after batch updates
        self.ui.enabledCheckbox.blockSignals(False)
        self.ui.trigger_word_edit.blockSignals(False)

        # Defer the creation of trigger word widgets
        self.create_trigger_word_widgets(self.lora, defer=True)

    def create_trigger_word_widgets(self, lora, defer=False):
        if defer:
            # Defer the creation of trigger word widgets
            QTimer.singleShot(0, lambda: self._create_trigger_word_widgets(lora))
        else:
            self._create_trigger_word_widgets(lora)

    def _create_trigger_word_widgets(self, lora):
        for i in reversed(range(self.ui.enabledCheckbox.layout().count())):
            widget = self.ui.enabledCheckbox.layout().itemAt(i).widget()
            if isinstance(widget, LoraTriggerWordWidget):
                widget.deleteLater()
        for word in lora.get("trigger_word", "").split(","):
            if word.strip() == "":
                continue
            widget = LoraTriggerWordWidget(trigger_word=word)
            self.ui.enabledCheckbox.layout().addWidget(widget)

    def action_changed_trigger_words(self, val):
        self.lora["trigger_word"] = val
        self.create_trigger_word_widgets(self.lora)
        self.update_lora()

    def action_toggled_lora_enabled(self, val):
        self.ui.enabledCheckbox.setChecked(val)
        self.lora['enabled'] = val
        self.update_lora()
        self.emit_signal(SignalCode.LORA_UPDATE_SIGNAL, self.lora)
    
    def action_text_changed_trigger_word(self, val):
        self.lora["trigger_word"] = val
        self.update_lora()

    def update_lora(self):
        lora = self.lora
        settings = self.settings
        version = lora["version"]
        if version not in settings["lora"]:
            settings["lora"][version] = []
        lora_found = False
        for index, _lora in enumerate(settings["lora"][version]):
            if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                settings["lora"][version][index] = lora
                lora_found = True
                break
        if not lora_found:
            settings["lora"][version].append(lora)
        self.settings = settings

    def action_clicked_button_deleted(self):
        self.emit_signal(
            SignalCode.LORA_DELETE_SIGNAL,
            {
                "lora_widget": self
            }
        )
