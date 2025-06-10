from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, Qt, QGuiApplication
from PySide6.QtCore import Qt as QtCoreQt


class SplashScreen(QSplashScreen):
    """
    Custom SplashScreen for AI Runner.
    Handles pixmap centering, transparency, geometry, and message display.
    """

    def __init__(self, screen, image_path, *args, **kwargs):
        # Always use the second screen if available (by index from QGuiApplication)
        screens = QGuiApplication.screens()
        if len(screens) > 1:
            screen = screens[1]
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
        self.setGeometry(screen.geometry())
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
