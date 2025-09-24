import os
import urllib.parse
import posixpath
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread, QFileSystemWatcher, QTimer
import jinja2
import mimetypes
import json
import ssl
import logging
import functools

from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST


class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True


class MultiDirectoryCORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler with CORS, Jinja2 template rendering, and multiple directory support.

    Args:
        lna_enabled (bool): If True, send LNA and permissive CORS headers for Chromium LNA compliance.
    """

    DANGEROUS_EXTENSIONS = {
        ".py",
        ".sh",
        ".exe",
        ".bat",
        ".env",
        ".ini",
        ".json",
        ".sqlite",
        ".db",
        ".pkl",
        ".so",
        ".dll",
        ".pem",
        ".crt",
        ".key",
        ".cfg",
        ".yaml",
        ".yml",
        ".md",
        ".rst",
        ".log",
        ".git",
        ".htpasswd",
        ".htaccess",
    }
    ALLOWED_MIME_PREFIXES = (
        "text/",
        "image/",
        "application/javascript",
        "application/json",
        "application/pdf",
        "application/font-woff",
        "font/",
    )

    def __init__(self, *args, directories=None, lna_enabled=False, **kwargs):
        self._add_no_cache_headers = None
        self.directories = directories or []
        self.lna_enabled = lna_enabled
        super().__init__(*args, **kwargs)

    def _send_lna_cors_headers(self):
        """Send LNA and CORS headers if lna_enabled, else do nothing (strict mode)."""
        if self.lna_enabled:
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, POST, OPTIONS, PUT, DELETE",
            )
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization, X-Requested-With",
            )
        # else: strict mode, do not send permissive headers

    def end_headers(self):
        if self.lna_enabled:
            self._send_lna_cors_headers()
        self.send_header(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-XSS-Protection", "1; mode=block")

        # Add no-cache headers if flag is set
        if (
            hasattr(self, "_add_no_cache_headers")
            and self._add_no_cache_headers
        ):
            self.send_header(
                "Cache-Control", "no-cache, no-store, must-revalidate"
            )
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self._add_no_cache_headers = False

        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        # Minimal error info: no file paths, no stack traces
        short_messages = {
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }
        msg = short_messages.get(code, "Error")
        super().send_error(code, msg)

    def do_GET(self):
        path = self.path
        # --- BEGIN: Custom logic for /game -> game/html/index.jinja2.html or index.html ---
        rel_path = path.lstrip("/")
        rel_path_no_query = rel_path.split("?", 1)[0]
        # If the path is a single segment (e.g. /game), try to serve game/html/index.jinja2.html or index.html
        if (
            rel_path_no_query
            and "/" not in rel_path_no_query
            and "." not in rel_path_no_query
        ):
            for directory in self.directories:
                # Normalize and validate the path to prevent directory traversal
                normalized_rel_path = os.path.normpath(rel_path_no_query)
                abs_directory = os.path.abspath(directory)
                abs_target_dir = os.path.abspath(
                    os.path.join(abs_directory, normalized_rel_path, "html")
                )
                # Ensure the target is within the allowed directory
                if not abs_target_dir.startswith(abs_directory):
                    self.send_error(403, "Forbidden")
                    return
                # Try Jinja2 template first
                jinja2_index = os.path.join(
                    abs_target_dir, "index.jinja2.html"
                )
                if os.path.exists(jinja2_index):
                    loader = jinja2.FileSystemLoader(self.directories)
                    env = jinja2.Environment(
                        loader=loader,
                        autoescape=jinja2.select_autoescape(["html", "xml"]),
                    )
                    # Relative path for Jinja2 loader
                    template_rel = os.path.relpath(jinja2_index, directory)
                    template = env.get_template(template_rel)
                    # Provide static_base_path for template rendering
                    context = {
                        "static_base_path": f"https://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}"
                    }
                    rendered = template.render(**context)
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    # Add cache-control headers to ensure fresh content on reload
                    self.send_header(
                        "Cache-Control", "no-cache, no-store, must-revalidate"
                    )
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.end_headers()
                    self.wfile.write(rendered.encode("utf-8"))
                    return
                # Try static HTML fallback
                html_index = os.path.join(abs_target_dir, "index.html")
                if os.path.exists(html_index):
                    with open(html_index, "rb") as f:
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        # Add cache-control headers to ensure fresh content on reload
                        self.send_header(
                            "Cache-Control",
                            "no-cache, no-store, must-revalidate",
                        )
                        self.send_header("Pragma", "no-cache")
                        self.send_header("Expires", "0")
                        self.end_headers()
                        self.wfile.write(f.read())
                    return
        # --- END: Custom logic ---        # --- BEGIN: Static files for project directories (e.g. /game/css/game.css) ---
        rel_path = path.lstrip("/")
        rel_path_no_query = rel_path.split("?", 1)[0]

        # Check if this is a static file within a project directory (e.g. game/css/file.css, game/js/file.js)
        path_parts = rel_path_no_query.split("/")
        if len(path_parts) >= 3:  # e.g. ["game", "css", "file.css"]
            project_name = path_parts[0]
            static_type = path_parts[1]  # "css", "js", "images", etc.
            if static_type in [
                "css",
                "js",
                "images",
                "img",
                "fonts",
                "static",
            ]:
                # Look for the file in project_name/static_type/filename
                for directory in self.directories:
                    static_file_path = os.path.join(directory, *path_parts)
                    if os.path.exists(static_file_path):
                        # Security check: ensure the file is within the allowed directory
                        abs_directory = os.path.abspath(directory)
                        abs_file_path = os.path.abspath(static_file_path)
                        try:
                            if (
                                os.path.commonpath(
                                    [abs_directory, abs_file_path]
                                )
                                != abs_directory
                            ):
                                logging.warning(
                                    f"[SECURITY] Attempted escape from base directory: {abs_file_path} not in {abs_directory}"
                                )
                                self.send_error(403)
                                return
                        except ValueError:
                            self.send_error(403)
                            return

                        # Check MIME type
                        mime, _ = mimetypes.guess_type(static_file_path)
                        if not mime or not mime.startswith(
                            self.ALLOWED_MIME_PREFIXES
                        ):
                            logging.warning(
                                f"[SECURITY] Refused to serve file with MIME type: {mime} ({static_file_path})"
                            )
                            self.send_error(403)
                            return

                        # Serve the file directly
                        try:
                            with open(static_file_path, "rb") as f:
                                self.send_response(200)
                                self.send_header("Content-type", mime)
                                # Add no-cache headers for CSS files to ensure fresh content on reload
                                if static_file_path.endswith(".css"):
                                    self.send_header(
                                        "Cache-Control",
                                        "no-cache, no-store, must-revalidate",
                                    )
                                    self.send_header("Pragma", "no-cache")
                                    self.send_header("Expires", "0")
                                self.end_headers()
                                self.wfile.write(f.read())
                                return
                        except IOError:
                            self.send_error(404)
                            return
        # --- END: Static files for project directories ---

        if path.startswith("/static/"):
            rel_path = path[len("/static/") :]
        else:
            rel_path = path.lstrip("/")
        # Directory traversal detection
        if (
            ".." in rel_path.split(os.sep)
            or rel_path.startswith("/")
            or os.path.isabs(rel_path)
        ):
            logging.warning(
                f"[SECURITY] Directory traversal attempt: {self.path}"
            )
            self.send_error(403)
            return
        # Jinja2 template rendering
        rel_path_no_query = rel_path.split("?", 1)[0]
        if rel_path_no_query.endswith(".jinja2.html"):
            for directory in self.directories:
                normalized_rel_path = os.path.normpath(rel_path_no_query)
                abs_directory = os.path.abspath(os.path.normpath(directory))
                # Reject absolute paths or any path with '..' after normalization
                if (
                    os.path.isabs(normalized_rel_path)
                    or normalized_rel_path.startswith("..")
                    or ".." in normalized_rel_path.split(os.sep)
                ):
                    logging.warning(
                        f"[SECURITY] Attempted directory traversal in template path: {normalized_rel_path}"
                    )
                    self.send_error(403)
                    return
                abs_target = os.path.abspath(
                    os.path.join(abs_directory, normalized_rel_path)
                )
                try:
                    if (
                        os.path.commonpath([abs_directory, abs_target])
                        != abs_directory
                    ):
                        logging.warning(
                            f"[SECURITY] Attempted escape from base directory: {abs_target} not in {abs_directory}"
                        )
                        self.send_error(403)
                        return
                except ValueError:
                    self.send_error(403)
                    return
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
                    template = env.get_template(rel_path_no_query)
                    rendered = template.render(**context)
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    # Add cache-control headers to ensure fresh content on reload
                    self.send_header(
                        "Cache-Control", "no-cache, no-store, must-revalidate"
                    )
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.end_headers()
                    self.wfile.write(rendered.encode("utf-8"))
                    return
            # If we reach here, template was not found in any directory
            self.send_error(404)
            return
        # Strict MIME type enforcement
        abs_path = self.translate_path(self.path)
        ext = os.path.splitext(abs_path)[1].lower()
        if ext in self.DANGEROUS_EXTENSIONS:
            logging.warning(
                f"[SECURITY] Refused to serve dangerous file type: {abs_path}"
            )
            self.send_error(403)
            return
        mime, _ = mimetypes.guess_type(abs_path)
        if not mime or not mime.startswith(self.ALLOWED_MIME_PREFIXES):
            logging.warning(
                f"[SECURITY] Refused to serve file with MIME type: {mime} ({abs_path})"
            )
            self.send_error(403)
            return

        # Add no-cache headers for CSS files to ensure fresh content on reload
        if abs_path.endswith(".css"):
            # We'll add the headers in the parent class call, but we need to set a flag
            self._add_no_cache_headers = True

        return super().do_GET()

    def do_HEAD(self):
        return self.do_GET()

    def do_POST(self):
        logging.warning(f"[SECURITY] Blocked POST request: {self.path}")
        self.send_error(405)

    def do_PUT(self):
        logging.warning(f"[SECURITY] Blocked PUT request: {self.path}")
        self.send_error(405)

    def do_DELETE(self):
        logging.warning(f"[SECURITY] Blocked DELETE request: {self.path}")
        self.send_error(405)

    def do_OPTIONS(self):
        if self.lna_enabled:
            self.send_response(204)
            self._send_lna_cors_headers()
            self.end_headers()
        else:
            logging.warning(f"[SECURITY] Blocked OPTIONS request: {self.path}")
            self.send_error(403)

    def list_directory(self, path):
        logging.warning(f"[SECURITY] Directory listing attempt: {path}")
        self.send_error(403)
        return None

    def translate_path(self, path):
        if path.startswith("/static/"):
            path = path[len("/static/") :]

        # Remove query and fragment
        safe_path = path.split("?", 1)[0]
        safe_path = safe_path.split("#", 1)[0]
        safe_path = urllib.parse.unquote(safe_path, errors="surrogatepass")
        safe_path = posixpath.normpath(safe_path)

        # Strip leading slash to make it relative
        if safe_path.startswith("/"):
            safe_path = safe_path[1:]

        # Prevent absolute paths and directory traversal
        if (
            safe_path.startswith("..")
            or ".." in safe_path.split(os.sep)
            or os.path.isabs(safe_path)
        ):
            logging.warning(
                f"[SECURITY] Attempted directory traversal or absolute path: {path}"
            )
            return ""
        # Prevent static serving of jinja2 templates
        if safe_path.endswith(".jinja2.html"):
            return ""
        # Use only safe, sanitized path
        for directory in self.directories:
            abs_directory = os.path.abspath(os.path.normpath(directory))
            # Normalize and sanitize safe_path
            normalized_safe_path = os.path.normpath(safe_path)
            if (
                os.path.isabs(normalized_safe_path)
                or normalized_safe_path.startswith("..")
                or ".." in normalized_safe_path.split(os.sep)
            ):
                logging.warning(
                    f"[SECURITY] Attempted directory traversal in static path: {normalized_safe_path}"
                )
                continue
            potential_path = os.path.join(abs_directory, normalized_safe_path)
            abs_potential = os.path.abspath(potential_path)
            try:
                if (
                    os.path.commonpath([abs_directory, abs_potential])
                    != abs_directory
                ):
                    logging.warning(
                        f"[SECURITY] Attempted escape from base directory: {abs_potential} not in {abs_directory}"
                    )
                    continue
            except ValueError:
                continue
            if os.path.exists(abs_potential):
                return abs_potential
        # Fallback to default handler, but only with sanitized path
        return super().translate_path(safe_path)


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Request handler with CORS support (locked down for production)."""

    def _send_lna_cors_headers(self):
        # Do NOT send Access-Control-Allow-Private-Network or permissive CORS
        pass

    def end_headers(self):
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
        self.send_error(403, "Forbidden")

    def list_directory(self, path):
        self.send_error(403, "Directory listing not allowed")
        return None


class LocalHttpServerThread(QThread):
    """Thread to run a local HTTPS server with optional directory and SSL support.

    Args:
        lna_enabled (bool): If True, server sends LNA/CORS headers for Chromium LNA compliance.
    """

    def __init__(
        self,
        directory=None,
        additional_directories=None,
        port=LOCAL_SERVER_PORT,
        parent=None,
        certfile=None,
        keyfile=None,
        lna_enabled=False,
    ):
        super().__init__(parent)
        self.directory = directory
        self.additional_directories = additional_directories or []
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.lna_enabled = lna_enabled
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
                    "../../../components/**/gui/static",
                )
            ),
        ]
        if self.additional_directories:
            static_dirs.extend(self.additional_directories)
        static_dirs = list(dict.fromkeys(static_dirs))

        handler_class = functools.partial(
            MultiDirectoryCORSRequestHandler,
            directories=static_dirs,
            lna_enabled=self.lna_enabled,
        )

        if self.directory:
            os.chdir(self.directory)

        self._server = ReusableTCPServer(
            (LOCAL_SERVER_HOST, self.port), handler_class
        )
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        # Enforce minimum TLS version 1.2 for security
        if hasattr(context, "minimum_version"):
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            # Fallback for older Python: explicitly disable TLSv1 and TLSv1_1
            context.options |= getattr(ssl, "OP_NO_TLSv1", 0)
            context.options |= getattr(ssl, "OP_NO_TLSv1_1", 0)
            # If neither minimum_version nor options are available, raise error
            if not (
                getattr(ssl, "OP_NO_TLSv1", None)
                and getattr(ssl, "OP_NO_TLSv1_1", None)
            ):
                raise RuntimeError(
                    "Python SSLContext does not support disabling TLSv1/TLSv1_1. Upgrade your Python/SSL."
                )
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
