"""
MathJaxViewer: Widget for rendering LaTeX/MathJax content in AIRunner EditorWidget.

Uses QWebEngineView to display MathJax-rendered HTML.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot
import os


class MathJaxViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        self._init_mathjax()

    def _init_mathjax(self):
        # Load a minimal HTML page with MathJax from static/mathjax
        mathjax_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "../../../../static/mathjax/tex-mml-chtml.js"
            )
        )
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src='file://{mathjax_path}'></script>
            <script>
                window.MathJax = {{
                    tex: {{ inlineMath: [['$','$'], ['\\(','\\)']] }},
                    svg: {{ fontCache: 'global' }}
                }};
            </script>
        </head>
        <body><div id='mathjax-content'></div></body>
        </html>
        """
        self.web_view.setHtml(html)

    @Slot(str)
    def set_latex(self, latex: str):
        # Set the LaTeX content and trigger MathJax typesetting
        js = f"""
        document.getElementById('mathjax-content').innerHTML = `{latex}`;
        MathJax.typesetPromise();
        """
        self.web_view.page().runJavaScript(js)
