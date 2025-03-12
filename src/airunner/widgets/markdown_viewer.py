from PySide6.QtWidgets import QApplication, QTextBrowser, QVBoxLayout, QWidget
import markdown


class MarkdownViewer(QWidget):
    def __init__(self, markdown_file):
        super().__init__()

        # Create a QTextBrowser widget
        self.browser = QTextBrowser()

        # Load and convert markdown file
        self.load_markdown(markdown_file)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def load_markdown(self, markdown_file):
        try:
            with open(markdown_file, "r", encoding="utf-8") as f:
                md_text = f.read()
                html = markdown.markdown(md_text)  # Convert to HTML
                self.browser.setHtml(html)  # Display in QTextBrowser
        except Exception as e:
            self.browser.setText(f"Error loading Markdown: {e}")
