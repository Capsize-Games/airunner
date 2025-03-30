from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QBuffer, QIODevice, QObject
from PySide6.QtWidgets import QWidget

def load_ui_file(ui_file_path: str, parent: QWidget = None) -> QWidget:
    """
    Load a .ui file dynamically at runtime and return the corresponding QWidget.

    :param ui_file_path: Path to the .ui file.
    :param parent: Optional parent widget.
    :return: QWidget instance loaded from the .ui file.
    """
    loader = QUiLoader()
    ui_file = QFile(ui_file_path)
    if not ui_file.open(QFile.ReadOnly):
        raise FileNotFoundError(f"Unable to open UI file: {ui_file_path}")

    widget = loader.load(ui_file, parent)
    ui_file.close()

    if widget is None:
        raise RuntimeError(f"Failed to load UI file: {ui_file_path}")

    return widget

def load_ui_from_string(ui_content: str, parent: QWidget = None, signal_handler: QObject = None) -> QWidget:
    """
    Load a .ui file dynamically from a string and return the corresponding QWidget.

    :param ui_content: The content of the .ui file as a string.
    :param parent: Optional parent widget.
    :param signal_handler: Optional object to handle signals.
    :return: QWidget instance loaded from the .ui content.
    """
    loader = QUiLoader()
    buffer = QBuffer()
    buffer.setData(ui_content.encode('utf-8'))
    if not buffer.open(QIODevice.ReadOnly):
        raise RuntimeError("Unable to open UI content from string.")

    widget = loader.load(buffer, parent)
    buffer.close()

    if widget is None:
        raise RuntimeError("Failed to load UI content from string.")

    # Automatically connect signals if a signal handler is provided
    if signal_handler:
        for child in widget.findChildren(QObject):
            if hasattr(signal_handler, child.objectName()):
                signal = getattr(signal_handler, child.objectName())
                if callable(signal):
                    child.clicked.connect(signal)

    return widget