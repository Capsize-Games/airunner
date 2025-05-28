"""
SyntaxHighlighter: Multi-language syntax highlighting for EditorWidget.

Uses QSyntaxHighlighter to provide syntax highlighting for supported languages.
"""

from typing import Optional
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language: str = "Markdown"):
        super().__init__(document)
        self.language = language
        self.highlighting_rules = []
        self._setup_rules()

    def set_language(self, language: str):
        self.language = language
        self._setup_rules()
        self.rehighlight()

    def _setup_rules(self):
        self.highlighting_rules.clear()
        if self.language.lower() == "python":
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor("#569CD6"))
            keyword_format.setFontWeight(QFont.Bold)
            keywords = [
                "def",
                "class",
                "if",
                "elif",
                "else",
                "try",
                "except",
                "finally",
                "for",
                "while",
                "return",
                "import",
                "from",
                "as",
                "with",
                "pass",
                "break",
                "continue",
                "in",
                "is",
                "not",
                "and",
                "or",
                "lambda",
                "yield",
                "assert",
                "raise",
                "global",
                "nonlocal",
                "del",
                "True",
                "False",
                "None",
            ]
            for word in keywords:
                pattern = QRegularExpression(rf"\\b{word}\\b")
                self.highlighting_rules.append((pattern, keyword_format))
            # Strings
            string_format = QTextCharFormat()
            string_format.setForeground(QColor("#CE9178"))
            self.highlighting_rules.append(
                (QRegularExpression(r'".*?"'), string_format)
            )
            self.highlighting_rules.append(
                (QRegularExpression(r"'.*?'"), string_format)
            )
            # Comments
            comment_format = QTextCharFormat()
            comment_format.setForeground(QColor("#6A9955"))
            self.highlighting_rules.append((QRegularExpression(r"#.*"), comment_format))
        elif self.language.lower() == "markdown":
            header_format = QTextCharFormat()
            header_format.setForeground(QColor("#4EC9B0"))
            header_format.setFontWeight(QFont.Bold)
            self.highlighting_rules.append(
                (QRegularExpression(r"^#+.*"), header_format)
            )
            bold_format = QTextCharFormat()
            bold_format.setFontWeight(QFont.Bold)
            self.highlighting_rules.append(
                (QRegularExpression(r"\*\*.*?\*\*"), bold_format)
            )
            italic_format = QTextCharFormat()
            italic_format.setFontItalic(True)
            self.highlighting_rules.append(
                (QRegularExpression(r"\*.*?\*"), italic_format)
            )
            code_format = QTextCharFormat()
            code_format.setFontFamily("monospace")
            code_format.setForeground(QColor("#DCDCAA"))
            self.highlighting_rules.append(
                (QRegularExpression(r"`[^`]+`"), code_format)
            )
        # Add more languages as needed

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
