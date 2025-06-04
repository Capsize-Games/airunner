import os
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread
from typing import List
import jinja2
import mimetypes
import json

from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST


class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True


class MultiDirectoryCORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler that can serve files from multiple directories and render Jinja2 templates for .html files."""

    def __init__(self, *args, directories=None, **kwargs):
        self.directories = directories or []
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        import os
        import urllib.parse

        path = self.path
        if path.startswith("/static/"):
            rel_path = path[len("/static/") :]
        else:
            rel_path = path.lstrip("/")
        # Only handle .jinja2.html files
        if rel_path.endswith(".jinja2.html"):
            for directory in self.directories:
                jinja2_path = os.path.join(directory, rel_path)
                if os.path.exists(jinja2_path):
                    # Parse query parameters as context
                    parsed_url = urllib.parse.urlparse(self.path)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    context = {}
                    for k, v in query_params.items():
                        val = v[0]
                        # Try to decode JSON, fallback to string
                        try:
                            context[k] = json.loads(val)
                        except Exception:
                            context[k] = val
                    loader = jinja2.FileSystemLoader(self.directories)
                    env = jinja2.Environment(
                        loader=loader,
                        autoescape=jinja2.select_autoescape(["html", "xml"]),
                    )
                    template = env.get_template(rel_path)
                    rendered = template.render(**context)
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(rendered.encode("utf-8"))
                    return
        # Fallback to normal static file serving
        return super().do_GET()

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax, checking multiple directories."""
        # Remove /static/ prefix if present
        if path.startswith("/static/"):
            path = path[len("/static/") :]
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
        # Always serve from all relevant static directories
        static_dirs = [
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../static")
            ),
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "../../../components/chat/gui/static",
                )
            ),
        ]
        if self.additional_directories:
            static_dirs.extend(self.additional_directories)
        # Remove duplicates
        static_dirs = list(dict.fromkeys(static_dirs))

        def handler_factory(*args, **kwargs):
            return MultiDirectoryCORSRequestHandler(
                *args, directories=static_dirs, **kwargs
            )

        handler_class = handler_factory

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
