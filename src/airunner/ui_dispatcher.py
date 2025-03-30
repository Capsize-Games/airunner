from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget, QDialog

def render_ui_from_spec(spec, parent_window):
    if spec["type"] == "window":
        if isinstance(parent_window, QDialog):
            layout = QVBoxLayout(parent_window)
        else:
            parent_window.setWindowTitle(spec.get("title", "Untitled"))
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            parent_window.setCentralWidget(central_widget)

        for widget_spec in spec.get("widgets", []):
            if widget_spec["type"] == "label":
                label = QLabel(widget_spec.get("text", ""))
                layout.addWidget(label)

        if isinstance(parent_window, QDialog):
            parent_window.setLayout(layout)
        parent_window.show()

def test_hello_world_window():
    app = QApplication([])
    main_window = QMainWindow()
    spec = {
        "type": "window",
        "title": "Hello Window",
        "layout": "vertical",
        "widgets": [
            {"type": "label", "text": "Hello, world!"}
        ]
    }
    render_ui_from_spec(spec, main_window)
    app.exec()