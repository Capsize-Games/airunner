from __future__ import annotations

import os
from PySide6 import QtWidgets, QtGui, QtCore


class UpscalePreviewDialog(QtWidgets.QDialog):
    """Popup dialog that watches a preview image file and updates as it changes.

    Usage: open this dialog on the main thread before starting an upscale. The
    upscaler will write intermediate previews to the preview_path which this
    dialog will display.
    """

    def __init__(
        self, preview_path: str, poll_interval_ms: int = 300, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Upscale preview")
        self._preview_path = preview_path
        self._last_mtime = 0
        self._poll_interval_ms = poll_interval_ms

        self._label = QtWidgets.QLabel(self)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._label.setMinimumSize(400, 400)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._label, stretch=1)
        layout.addWidget(
            btn_close, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self._poll_interval_ms)
        self._timer.timeout.connect(self._check_and_update)

    def start(self):
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.close()

    def _check_and_update(self):
        try:
            if not os.path.exists(self._preview_path):
                return
            mtime = os.path.getmtime(self._preview_path)
            if mtime <= self._last_mtime:
                return
            self._last_mtime = mtime
            pix = QtGui.QPixmap(self._preview_path)
            if pix.isNull():
                return
            scaled = pix.scaled(
                self._label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            self._label.setPixmap(scaled)
        except Exception:
            # Silently ignore errors; preview is best-effort.
            pass

    def resizeEvent(
        self, event: QtGui.QResizeEvent
    ) -> None:  # keep preview scaled on resize
        super().resizeEvent(event)
        if self._label.pixmap() is not None:
            pix = self._label.pixmap()
            if pix:
                scaled = pix.scaled(
                    self._label.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                self._label.setPixmap(scaled)
