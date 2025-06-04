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
                    "created_at": bm.created_at,
                    "updated_at": bm.updated_at,
                },
                Qt.UserRole,
            )
            folder_item.appendRow(bm_item)
        model.appendRow(folder_item)
    return model


def history_to_model(history: list[HistoryEntry]) -> QStandardItemModel:
    model = QStandardItemModel()
    for entry in history:
        # Show the most recent visit date
        last_visited = entry.visits[-1] if entry.visits else None
        label = entry.title
        if last_visited:
            label = f"{entry.title} ({last_visited[:19].replace('T', ' ')})"
        item = QStandardItem(label)
        item.setEditable(False)
        item.setData(
            {
                "type": "history",
                "title": entry.title,
                "url": entry.url,
                "visited_at": last_visited,
                "visits": entry.visits,
            },
            Qt.UserRole,
        )
        model.appendRow(item)
    return model
