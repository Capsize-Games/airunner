#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QLabel,
)
from PySide6.QtCore import Qt

# Import our content widgets
sys.path.append("/home/joe/Projects/airunner/src")
from airunner.gui.widgets.llm.content_widgets import (
    PlainTextWidget,
    LatexWidget,
    MarkdownWidget,
    MixedContentWidget,
)
from airunner.utils.text.formatter_extended import FormatterExtended


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Content Widgets Test")
        self.setGeometry(100, 100, 800, 600)

        # Sample content for testing
        self.test_content = {
            "plain": "This is plain text content.\nIt has multiple lines.\nEach line should display correctly without issues.",
            "latex": "$$E = mc^2$$\n$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$",
            "markdown": """# Syntax Highlighting Demo

## Python Code
```python
def hello_world():
    print('Hello, world!')
    for i in range(10):
        print(f'Count: {i}')
    return True
```

## JavaScript Code
```javascript
function calculateSum(arr) {
    return arr.reduce((a, b) => a + b, 0);
}

const numbers = [1, 2, 3, 4, 5];
console.log(`Sum: ${calculateSum(numbers)}`);
```

## JSON Example
```json
{
    "name": "John Doe",
    "age": 30,
    "isActive": true,
    "interests": ["programming", "music", "hiking"]
}
```

## Regular Markdown
**Bold text** and *italic text*

- List item 1
- List item 2
- List item 3

> This is a blockquote
""",
            "mixed": "Regular text with a formula $$E = mc^2$$ and more text after it.\n\nAnother paragraph with $$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$.",
        }

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Create controls
        control_layout = QHBoxLayout()
        main_layout.addLayout(control_layout)

        # Content type selector
        self.type_label = QLabel("Content Type:")
        control_layout.addWidget(self.type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Plain Text", "LaTeX", "Markdown", "Mixed"])
        self.type_combo.currentIndexChanged.connect(self.update_content)
        control_layout.addWidget(self.type_combo)

        control_layout.addStretch()

        # Container for the content widget
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.content_container)

        # Current content widget
        self.current_widget = None

        # Initial update
        self.update_content(0)

    def update_content(self, index):
        # Clear current widget if exists
        if self.current_widget:
            self.content_layout.removeWidget(self.current_widget)
            self.current_widget.deleteLater()
            self.current_widget = None

        # Create the appropriate widget based on selection
        if index == 0:  # Plain Text
            self.current_widget = PlainTextWidget(self.content_container)
            self.current_widget.setContent(self.test_content["plain"])

        elif index == 1:  # LaTeX
            self.current_widget = LatexWidget(self.content_container)
            self.current_widget.setContent(self.test_content["latex"])

        elif index == 2:  # Markdown
            self.current_widget = MarkdownWidget(self.content_container)
            # Use the formatter to convert markdown to HTML
            result = FormatterExtended.format_content(
                self.test_content["markdown"]
            )
            self.current_widget.setContent(result["content"])

        elif index == 3:  # Mixed
            self.current_widget = MixedContentWidget(self.content_container)
            result = FormatterExtended.format_content(
                self.test_content["mixed"]
            )
            self.current_widget.setContent(result["parts"])

        # Add the widget to layout
        self.content_layout.addWidget(self.current_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
