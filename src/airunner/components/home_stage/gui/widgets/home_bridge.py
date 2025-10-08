from PySide6.QtCore import QObject, Signal, Slot


class HomeBridge(QObject):
    """Bridge for JavaScript-to-Python communication in the home stage widget."""

    updateStatsRequested = Signal()
    indexAllDocumentsRequested = Signal()
    cancelIndexRequested = Signal()

    @Slot()
    def requestUpdateStats(self):
        """Called from JavaScript to request document stats update."""
        self.updateStatsRequested.emit()

    @Slot()
    def requestIndexAllDocuments(self):
        """Called from JavaScript to start indexing all unindexed documents."""
        self.indexAllDocumentsRequested.emit()

    @Slot()
    def requestCancelIndex(self):
        """Called from JavaScript to request cancellation of indexing."""
        self.cancelIndexRequested.emit()
