from PySide6.QtWidgets import (
    QApplication,
    QMainWindow
)


def get_main_window():
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
