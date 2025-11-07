import os
import urllib.parse
import posixpath
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread
import jinja2
import mimetypes
import json
import functools

from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
    LOCAL_SERVER_PORT,
    LOCAL_SERVER_HOST,
)
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
        # Security headers (HSTS removed since we're using HTTP for localhost)
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
        # Add permissive CORS for font resources and MathJax assets so the
        # QWebEngineView won't block font loads when origin differs by host
        # (e.g. requests coming from http://127.0.0.1 vs http://localhost).
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path or ""
            lower = path.lower()
            if (
                lower.endswith(".woff")
                or lower.endswith(".woff2")
                or lower.endswith(".ttf")
                or lower.endswith(".otf")
                or "/mathjax/" in lower
            ):
                # Restrict to the exact server origin to avoid overly-permissive CORS
                self.send_header(
                    "Access-Control-Allow-Origin",
                    f"http://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}",
                )
                self.send_header(
                    "Access-Control-Allow-Methods",
                    "GET, OPTIONS",
                )
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Origin, Content-Type, Accept",
                )
        except Exception:
            # Never raise from end_headers; if header addition fails, continue
            logger.debug(
                "Failed to add CORS headers for path: %s",
                getattr(self, "path", None),
            )

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
        rel_path = path.lstrip("/")
        rel_path_no_query = rel_path.split("?", 1)[0]
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
                        "static_base_path": f"http://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}"
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
        rel_path = path.lstrip("/")
        rel_path_no_query = rel_path.split("?", 1)[0]

        # Check if this is a static file within a project directory (e.g. game/css/file.css, game/js/file.js)
        path_parts = rel_path_no_query.split("/")
        if len(path_parts) >= 3:  # e.g. ["game", "css", "file.css"]
            path_parts[0]
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
                                logger.warning(
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
                            logger.warning(
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
            logger.warning(
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
                    logger.warning(
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
                        logger.warning(
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
            logger.warning(
                f"[SECURITY] Refused to serve dangerous file type: {abs_path}"
            )
            self.send_error(403)
            return
        mime, _ = mimetypes.guess_type(abs_path)
        if not mime or not mime.startswith(self.ALLOWED_MIME_PREFIXES):
            logger.warning(
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
        logger.warning(f"[SECURITY] Blocked POST request: {self.path}")
        self.send_error(405)

    def do_PUT(self):
        logger.warning(f"[SECURITY] Blocked PUT request: {self.path}")
        self.send_error(405)

    def do_DELETE(self):
        logger.warning(f"[SECURITY] Blocked DELETE request: {self.path}")
        self.send_error(405)

    def do_OPTIONS(self):
        if self.lna_enabled:
            self.send_response(204)
            self._send_lna_cors_headers()
            self.end_headers()
        else:
            logger.warning(f"[SECURITY] Blocked OPTIONS request: {self.path}")
            self.send_error(403)

    def list_directory(self, path):
        logger.warning(f"[SECURITY] Directory listing attempt: {path}")
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
            logger.warning(
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
                logger.warning(
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
                    logger.warning(
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
        # Use plain HTTP for local-only communication (no SSL overhead or certificate issues)
        logger.info(
            f"Local HTTP server running on http://{LOCAL_SERVER_HOST}:{self.port}"
        )
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
