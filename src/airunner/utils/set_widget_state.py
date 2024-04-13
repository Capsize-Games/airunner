def set_widget_state(widget, checked, block_signals=True):
    widget.blockSignals(block_signals)
    widget.setChecked(checked)
    widget.blockSignals(False)
