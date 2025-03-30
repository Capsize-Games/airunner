from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget

def render_ui_from_spec(spec, main_window):
    if spec["type"] == "window":
        main_window.setWindowTitle(spec.get("title", "Untitled"))

        central_widget = QWidget()
        layout = QVBoxLayout()

        for widget_spec in spec.get("widgets", []):
            if widget_spec["type"] == "label":
                label = QLabel(widget_spec.get("text", ""))
                layout.addWidget(label)

        central_widget.setLayout(layout)
        main_window.setCentralWidget(central_widget)
        main_window.show()

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