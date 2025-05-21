import os
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread

from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST


class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


class LocalHttpServerThread(QThread):
    def __init__(self, directory, port=LOCAL_SERVER_PORT, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.port = port
        self._server = None

    def run(self):
        os.chdir(self.directory)
        handler = CORSRequestHandler
        self._server = ReusableTCPServer(
            (LOCAL_SERVER_HOST, self.port), handler
        )
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
