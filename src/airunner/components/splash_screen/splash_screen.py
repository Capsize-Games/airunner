from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, Qt
from PySide6.QtCore import Qt as QtCoreQt


class SplashScreen(QSplashScreen):
    """
    Custom SplashScreen for AI Runner.
    Handles pixmap centering, transparency, geometry, and message display.
    """

    def __init__(self, screen, image_path, *args, **kwargs):
        # Load the splash image
        original_pixmap = QPixmap(str(image_path))
        screen_size = screen.geometry().size()
        centered_pixmap = QPixmap(screen_size)
        centered_pixmap.fill(Qt.transparent)
        # Center the splash image
        x_pos = (screen_size.width() - original_pixmap.width()) // 2
        y_pos = (screen_size.height() - original_pixmap.height()) // 2
        painter = QPainter(centered_pixmap)
        painter.drawPixmap(x_pos, y_pos, original_pixmap)
        painter.end()
        super().__init__(screen, centered_pixmap, *args, **kwargs)
        self.setMask(centered_pixmap.mask())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(
            screen.geometry().x(),
            screen.geometry().y(),
            screen.geometry().width(),
            screen.geometry().height() - original_pixmap.height(),
        )
        self.setWindowFlags(
            QtCoreQt.WindowType.FramelessWindowHint
            | QtCoreQt.WindowType.WindowStaysOnTopHint
            | QtCoreQt.WindowType.SplashScreen
        )
        self.show()

    def show_message(self, message: str):
        self.showMessage(
            message,
            QtCoreQt.AlignmentFlag.AlignBottom
            | QtCoreQt.AlignmentFlag.AlignCenter,
            QtCoreQt.GlobalColor.white,
        )
