from PySide6.QtCore import Qt

def enable_wayland_window_decorations(window):
    """
    Enable window decorations for a Qt window when running in Wayland.
    This helps fix issues with windows having no borders/decorations in Docker/Wayland environments.
    
    :param window: A QWindow or QWidget instance
    """
    # Make sure window has correct flags for Wayland decorations
    window.setWindowFlags(
        Qt.WindowType.Window | 
        Qt.WindowType.WindowSystemMenuHint | 
        Qt.WindowType.WindowTitleHint | 
        Qt.WindowType.WindowMinMaxButtonsHint | 
        Qt.WindowType.WindowCloseButtonHint
    )