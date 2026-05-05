"""Proxy model for showing only configured workspace roots."""

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel

from airunner.components.file_explorer.project_root_visibility import (
    path_visible_in_roots,
)


class MultiRootFileProxyModel(QSortFilterProxyModel):
    """Filter a QFileSystemModel down to configured project roots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_paths: list[str] = []
        self._common_parent = ""
        self.setRecursiveFilteringEnabled(True)

    def configure_roots(
        self,
        root_paths: list[str],
        common_parent: str,
    ) -> None:
        """Set the visible roots and refresh the filter."""
        self._root_paths = root_paths
        self._common_parent = common_parent
        self.invalidateFilter()

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        """Keep only configured roots, their descendants, and ancestors."""
        if not self._root_paths:
            return True
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        path = model.filePath(index)
        return path_visible_in_roots(
            path,
            self._root_paths,
            self._common_parent,
        )