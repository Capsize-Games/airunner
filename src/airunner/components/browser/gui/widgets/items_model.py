"""
QStandardItemModel helpers for browser bookmarks and history.
"""

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from airunner.components.browser.data.settings import (
    BookmarkFolder,
    Bookmark,
    HistoryEntry,
)


def bookmarks_to_model(
    bookmark_folders: list[BookmarkFolder],
) -> QStandardItemModel:
    model = QStandardItemModel()
    for folder in bookmark_folders:
        folder_item = QStandardItem(folder.name)
        folder_item.setEditable(False)
        folder_item.setData(
            {"type": "folder", "name": folder.name}, Qt.UserRole
        )
        for bm in folder.bookmarks:
            bm_item = QStandardItem(bm.title)
            bm_item.setEditable(False)
            bm_item.setData(
                {
                    "type": "bookmark",
                    "title": bm.title,
                    "url": bm.url,
                    "icon": bm.icon,
                },
                Qt.UserRole,
            )
            folder_item.appendRow(bm_item)
        model.appendRow(folder_item)
    return model


def history_to_model(history: list[HistoryEntry]) -> QStandardItemModel:
    model = QStandardItemModel()
    for entry in history:
        item = QStandardItem(entry.title)
        item.setEditable(False)
        item.setData(
            {
                "type": "history",
                "title": entry.title,
                "url": entry.url,
                "visited_at": entry.visited_at,
            },
            Qt.UserRole,
        )
        model.appendRow(item)
    return model
