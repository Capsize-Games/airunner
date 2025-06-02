import os
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread
from typing import List

from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST


class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True


class MultiDirectoryCORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler that can serve files from multiple directories."""

    def __init__(self, *args, directories=None, **kwargs):
        self.directories = directories or []
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax, checking multiple directories."""
        # Get the original path from the parent class
        original_path = super().translate_path(path)

        # If the file exists in the current directory, use it
        if os.path.exists(original_path):
            return original_path

        # Extract the relative path from the URL
        import urllib.parse
        import posixpath

        # Clean up the path
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        path = urllib.parse.unquote(path, errors="surrogatepass")
        path = posixpath.normpath(path)

        # Remove leading slash
        if path.startswith("/"):
            path = path[1:]

        # Check each directory in order
        for directory in self.directories:
            potential_path = os.path.join(directory, path)
            if os.path.exists(potential_path):
                return potential_path

        # If not found in any directory, return the original path
        return original_path


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


class LocalHttpServerThread(QThread):
    def __init__(
        self,
        directory=None,
        additional_directories=None,
        port=LOCAL_SERVER_PORT,
        parent=None,
    ):
        super().__init__(parent)
        self.directory = directory
        self.additional_directories = additional_directories or []
        self.port = port
        self._server = None

    def run(self):
        if self.additional_directories:
            # Use multi-directory handler
            def handler_factory(*args, **kwargs):
                return MultiDirectoryCORSRequestHandler(
                    *args, directories=self.additional_directories, **kwargs
                )

            handler_class = handler_factory
        else:
            # Use original single-directory handler
            handler_class = CORSRequestHandler

        if self.directory:
            os.chdir(self.directory)

        self._server = ReusableTCPServer(
            (LOCAL_SERVER_HOST, self.port), handler_class
        )
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
