import os
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread
from typing import List
import jinja2
import mimetypes
import json
import ssl

from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST


class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True


class MultiDirectoryCORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler with CORS, Jinja2 template rendering, and multiple directory support."""

    def __init__(self, *args, directories=None, **kwargs):
        self.directories = directories or []
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-XSS-Protection", "1; mode=block")
        super().end_headers()

    def do_GET(self):
        import os
        import urllib.parse

        path = self.path
        if path.startswith("/static/"):
            rel_path = path[len("/static/") :]
        else:
            rel_path = path.lstrip("/")
        if rel_path.endswith(".jinja2.html"):
            for directory in self.directories:
                normalized_rel_path = os.path.normpath(rel_path)
                # Prevent directory traversal: reject paths with '..' after normalization
                if normalized_rel_path.startswith("..") or os.path.isabs(
                    normalized_rel_path
                ):
                    continue
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(
                    os.path.join(abs_directory, normalized_rel_path)
                )
                try:
                    if (
                        os.path.commonpath([abs_directory, abs_target])
                        != abs_directory
                    ):
                        continue
                except ValueError:
                    continue
                jinja2_path = abs_target
                if os.path.exists(jinja2_path):
                    parsed_url = urllib.parse.urlparse(self.path)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    context = {}
                    for k, v in query_params.items():
                        val = v[0]
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
        return super().do_GET()

    def do_HEAD(self):
        return self.do_GET()

    def do_POST(self):
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self):
        self.send_error(405, "Method Not Allowed")

    def list_directory(self, path):
        self.send_error(403, "Directory listing not allowed")
        return None

    def translate_path(self, path):
        if path.startswith("/static/"):
            path = path[len("/static/") :]
        original_path = super().translate_path(path)
        if os.path.exists(original_path):
            return original_path
        import urllib.parse
        import posixpath

        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        path = urllib.parse.unquote(path, errors="surrogatepass")
        path = posixpath.normpath(path)
        if path.startswith("/"):
            path = path[1:]
        for directory in self.directories:
            potential_path = os.path.join(directory, path)
            if os.path.exists(potential_path):
                return potential_path
        return original_path


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler with CORS support."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-XSS-Protection", "1; mode=block")
        super().end_headers()

    def do_HEAD(self):
        return self.do_GET()

    def do_POST(self):
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self):
        self.send_error(405, "Method Not Allowed")

    def list_directory(self, path):
        self.send_error(403, "Directory listing not allowed")
        return None


class LocalHttpServerThread(QThread):
    """Thread to run a local HTTPS server with optional directory and SSL support."""

    def __init__(
        self,
        directory=None,
        additional_directories=None,
        port=LOCAL_SERVER_PORT,
        parent=None,
        certfile=None,
        keyfile=None,
    ):
        super().__init__(parent)
        self.directory = directory
        self.additional_directories = additional_directories or []
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self._server = None

    def run(self):
        import logging
        from airunner.settings import AIRUNNER_BASE_PATH

        # Determine cert/key paths as in launcher.py
        cert_dir = os.path.join(AIRUNNER_BASE_PATH, "certs")
        cert_file = os.environ.get(
            "AIRUNNER_SSL_CERT", os.path.join(cert_dir, "cert.pem")
        )
        key_file = os.environ.get(
            "AIRUNNER_SSL_KEY", os.path.join(cert_dir, "key.pem")
        )
        # Use explicit overrides if provided
        if self.certfile:
            cert_file = self.certfile
        if self.keyfile:
            key_file = self.keyfile
        # Validate cert/key existence
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            logging.error(
                f"SSL certificate or key not found. Expected cert: {cert_file}, key: {key_file}. Cannot start HTTPS server."
            )
            raise RuntimeError(
                "SSL certificate or key not found. Cannot start HTTPS server."
            )
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
        # --- HTTPS support ---
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        self._server.socket = context.wrap_socket(
            self._server.socket, server_side=True
        )
        logging.info(
            f"Local HTTPS server running with HTTPS on port {self.port} (cert: {cert_file}, key: {key_file})"
        )
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
