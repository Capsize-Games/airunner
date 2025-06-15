from PySide6 import QtCore
from airunner.vendor.nodegraphqt.widgets.viewer import NodeViewer
from airunner.components.application.api.api import API


class DebouncedNodeViewer(NodeViewer):
    """
    Extended NodeViewer with debounced zoom and pan signals that emit to the API.
    """

    def __init__(self, parent=None, undo_stack=None):
        super(DebouncedNodeViewer, self).__init__(parent, undo_stack)

        # Initialize API reference
        self.api = API()

        # Create debounce timers for zoom and pan events
        self._zoom_timer = QtCore.QTimer()
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.timeout.connect(self._emit_zoom_changed)

        self._pan_timer = QtCore.QTimer()
        self._pan_timer.setSingleShot(True)
        self._pan_timer.timeout.connect(self._emit_pan_changed)

        # Timer delays in milliseconds
        self._debounce_delay = 250  # 250ms debouncing

        self.zooms = 0
        self.pan = (0, 0)

        # Ensure _zoom and _pan are initialized for property access
        self._zoom = 1.0
        self._pan = (0, 0)

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, value):
        self._zoom = value

    @property
    def pan(self):
        return self._pan

    @pan.setter
    def pan(self, value):
        self._pan = value

    def _set_viewer_zoom(self, value, sensitivity=None, pos=None):
        """Override the zoom method to add debouncing signal."""
        super()._set_viewer_zoom(value, sensitivity, pos)

        self._zoom = value

        # Start or restart the debounce timer
        self._zoom_timer.start(self._debounce_delay)

    def _set_viewer_pan(self, pos_x, pos_y):
        """Override the pan method to add debouncing signal."""
        super()._set_viewer_pan(pos_x, pos_y)

        self._pan = (pos_x, pos_y)

        # Start or restart the debounce timer
        self._pan_timer.start(self._debounce_delay)

    def _emit_zoom_changed(self):
        """Emit the zoom changed signal after debouncing."""
        zoom_level = self.get_zoom()
        self.api.nodegraph.zoom_changed(zoom_level)

    def _emit_pan_changed(self):
        """Emit the pan changed signal after debouncing."""
        center = self.scene_center()
        self.api.nodegraph.pan_changed(int(center[0]), int(center[1]))
