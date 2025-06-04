"""
CacheMixin for BrowserWidget.
Handles custom HTML cache and session clearing logic.

Google Python Style Guide applies.
"""

import os


class CacheMixin:
    def _clear_history(self):
        """Clear the browser history."""
        self.profile.clearAllVisitedLinks()

    def _clear_cookies(self):
        """Clear cookies associated with the browser widget."""
        cookie_store = self.profile.cookieStore()
        cookie_store.deleteAllCookies()

    def _clear_http_cache(self):
        """Clear the HTTP cache associated with the browser widget."""
        self.profile.clearHttpCache()

    def _clear_html5_storage(self):
        """Clear HTML5 Storage (Local Storage, IndexedDB, etc.) associated with the browser widget."""
        # Note: Direct localStorage clearing not available in Qt WebEngine
        # Storage is automatically cleared when OTR profile is destroyed
        pass

    def _clear_custom_html_cache(self):
        """Clear the custom HTML disk cache that bypasses OTR profile."""
        cache_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "cache",
            "browser",
        )
        if os.path.exists(cache_dir):
            cleared_count = 0
            try:
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            cleared_count += 1
                        elif os.path.isdir(item_path):
                            import shutil

                            shutil.rmtree(item_path)
                            cleared_count += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to remove {item_path}: {e}"
                        )
                self.logger.info(
                    f"Custom HTML disk cache cleared - {cleared_count} items removed"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to access cache directory {cache_dir}: {e}"
                )

    def clear_session(self):
        """
        Clear history, cookies, HTTP cache, HTML5 Storage (Local Storage, IndexedDB, etc.),
        and any other persistent data associated with the browser widget.
        """
        self._clear_history()
        self._clear_cookies()
        self._clear_http_cache()
        self._clear_html5_storage()
        self._clear_custom_html_cache()  # Clear custom disk cache to maintain OTR privacy
