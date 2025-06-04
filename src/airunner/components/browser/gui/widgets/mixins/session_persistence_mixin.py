"""
SessionPersistenceMixin for BrowserWidget.
Handles session, history, and bookmarks persistence logic.

Google Python Style Guide applies.
"""

from airunner.data.models.airunner_settings import AIRunnerSettings
import json
import uuid
from datetime import datetime


class SessionPersistenceMixin:
    def add_bookmark(
        self,
        title: str = None,
        url: str = None,
        folder: str = "Bookmarks",
        uuid_key: str = None,
    ):
        if not title:
            title = self.ui.stage.title() or url or "(Untitled)"
        if not url:
            url = self.ui.stage.url().toString()
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            if not uuid_key:
                uuid_key = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            for f in bookmarks:
                if f["name"] == folder:
                    f["bookmarks"].append(
                        {
                            "title": title,
                            "url": url,
                            "uuid": uuid_key,
                            "created_at": now,
                        }
                    )
                    break
            else:
                bookmarks.append(
                    {
                        "name": folder,
                        "bookmarks": [
                            {
                                "title": title,
                                "url": url,
                                "uuid": uuid_key,
                                "created_at": now,
                            }
                        ],
                        "created_at": now,
                    }
                )
            data["bookmarks"] = bookmarks
            if "plaintext" not in data or not isinstance(
                data["plaintext"], dict
            ):
                data["plaintext"] = {}
            if "page_summary" not in data or not isinstance(
                data["page_summary"], dict
            ):
                data["page_summary"] = {}
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to add/update bookmark: {e}")

    def add_history_entry(
        self, title: str, url: str, visited_at: str, uuid_key: str = None
    ):
        self.logger.debug(
            f"add_history_entry called with title='{title}', visited_at='{visited_at}', uuid_key='{uuid_key}'"
        )
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            self.logger.warning(
                "add_history_entry: No settings_obj found for 'browser'. Cannot save history."
            )
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            found = False
            for entry in history:
                if entry["url"] == url:
                    entry.setdefault("visits", []).append(visited_at)
                    entry["title"] = title
                    found = True
                    break
            if not found:
                history.append(
                    {
                        "title": title,
                        "url": url,
                        "visits": [visited_at],
                    }
                )
            data["history"] = history[-1000:]
            if "plaintext" not in data or not isinstance(
                data["plaintext"], dict
            ):
                data["plaintext"] = {}
            if "page_summary" not in data or not isinstance(
                data["page_summary"], dict
            ):
                data["page_summary"] = {}
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.error(
                f"Failed to add history entry: {e}", exc_info=True
            )

    def is_page_bookmarked(self, url: str) -> bool:
        """Return True if the given URL is bookmarked in any folder."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return False
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            for folder in bookmarks:
                for bm in folder.get("bookmarks", []):
                    if bm.get("url") == url:
                        return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to check if page is bookmarked: {e}")
            return False

    def remove_bookmark(self, url: str):
        """Remove the bookmark for the given URL from all folders."""
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            changed = False
            for folder in bookmarks:
                before = len(folder.get("bookmarks", []))
                folder["bookmarks"] = [
                    bm
                    for bm in folder.get("bookmarks", [])
                    if bm.get("url") != url
                ]
                if len(folder["bookmarks"]) != before:
                    changed = True
            # Remove empty folders
            data["bookmarks"] = [f for f in bookmarks if f["bookmarks"]]
            if changed:
                AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
                if getattr(self, "_current_panel", None) == "bookmarks":
                    self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to remove bookmark: {e}")

    def _on_bookmarks_deleted(self, items: list):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            urls_to_delete = {
                item["url"] for item in items if item.get("type") == "bookmark"
            }
            for folder in bookmarks:
                folder["bookmarks"] = [
                    bm
                    for bm in folder["bookmarks"]
                    if bm["url"] not in urls_to_delete
                ]
            data["bookmarks"] = [f for f in bookmarks if f["bookmarks"]]
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to delete bookmarks: {e}")

    def _on_bookmark_edit_requested(self, item: dict):
        self.logger.info("Edit requested for bookmark")

    def _on_bookmarks_delete_all(self):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            data["bookmarks"] = []
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to delete all bookmarks: {e}")

    def _on_bookmarks_sort_requested(self, sort_mode: str):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            bookmarks = data.get("bookmarks", [])
            for folder in bookmarks:
                if sort_mode == "A-Z":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm["title"].lower()
                    )
                elif sort_mode == "Z-A":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm["title"].lower(), reverse=True
                    )
                elif sort_mode == "Date Added":
                    folder["bookmarks"].sort(
                        key=lambda bm: bm.get("created_at", "")
                    )
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "bookmarks":
                self._show_panel("bookmarks")
        except Exception as e:
            self.logger.warning(f"Failed to sort bookmarks: {e}")

    def _on_history_deleted(self, items: list):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            urls_to_delete = {
                item["url"] for item in items if item.get("type") == "history"
            }
            data["history"] = [
                h for h in history if h["url"] not in urls_to_delete
            ]
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to delete history entries: {e}")

    def _on_history_edit_requested(self, item: dict):
        self.logger.info("Edit requested for history entry")

    def _on_history_delete_all(self):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            data["history"] = []
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to delete all history: {e}")

    def _on_history_sort_requested(self, sort_mode: str):
        settings_obj = AIRunnerSettings.objects.filter_by_first(name="browser")
        if not settings_obj:
            return
        try:
            data = (
                settings_obj.data
                if isinstance(settings_obj.data, dict)
                else json.loads(settings_obj.data)
            )
            history = data.get("history", [])
            if sort_mode == "A-Z":
                history.sort(key=lambda h: h["title"].lower())
            elif sort_mode == "Z-A":
                history.sort(key=lambda h: h["title"].lower(), reverse=True)
            elif sort_mode == "Date Added":
                history.sort(
                    key=lambda h: h["visits"][-1] if h.get("visits") else ""
                )
            data["history"] = history
            AIRunnerSettings.objects.update(pk=settings_obj.id, data=data)
            if getattr(self, "_current_panel", None) == "history":
                self._show_panel("history")
        except Exception as e:
            self.logger.warning(f"Failed to sort history: {e}")
