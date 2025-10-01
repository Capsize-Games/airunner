from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QGuiApplication
from PySide6.QtCore import Qt as QtCoreQt


class SplashScreen(QSplashScreen):
    """
    Custom SplashScreen for AI Runner.
    Handles pixmap centering, positioning on target screen, and message display.
    """

    def __init__(self, screen, image_path, *args, **kwargs):
        """
        Initialize the splash screen on a specific monitor.

        Args:
            screen: QScreen object representing the target monitor
            image_path: Path to the splash screen image
        """
        from airunner.utils.settings import get_qsettings

        # Verify saved screen preference and use it if available
        qsettings = get_qsettings()
        qsettings.beginGroup("window_settings")
        saved_screen_name = qsettings.value("screen_name", None, type=str)
        qsettings.endGroup()

        # Try to find the saved screen by name
        target_screen = screen
        if saved_screen_name:
            screens = QGuiApplication.screens()
            for s in screens:
                if s.name() == saved_screen_name:
                    target_screen = s
                    break

        # Load the splash image at its original size
        original_pixmap = QPixmap(str(image_path))
        super().__init__(original_pixmap, *args, **kwargs)
        self.setMask(original_pixmap.mask())

        self.setWindowFlags(
            QtCoreQt.WindowType.FramelessWindowHint
            | QtCoreQt.WindowType.WindowStaysOnTopHint
            | QtCoreQt.WindowType.SplashScreen
        )

        # Set the screen before showing the window
        self.create()  # Ensure native window is created
        if self.windowHandle():
            self.windowHandle().setScreen(target_screen)

        # Center the splash on the target screen
        screen_geometry = target_screen.geometry()
        splash_x = (
            screen_geometry.x()
            + (screen_geometry.width() - original_pixmap.width()) // 2
        )
        splash_y = (
            screen_geometry.y()
            + (screen_geometry.height() - original_pixmap.height()) // 2
        )

        self.move(splash_x, splash_y)
        self.show()

        # Force position again after show (some window managers need this)
        self.move(splash_x, splash_y)
        QApplication.processEvents()

    def show_message(self, message: str):
        """Display a message on the splash screen."""
        self.showMessage(
            message,
            QtCoreQt.AlignmentFlag.AlignBottom
            | QtCoreQt.AlignmentFlag.AlignCenter,
            QtCoreQt.GlobalColor.white,
        )
