def toggle_signals(ui: object, elements: list, block: bool = True):
    for element in elements:
        getattr(ui, element).blockSignals(block)
