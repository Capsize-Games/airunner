import os
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from PySide6.QtCore import QThread


class LocalHttpServerThread(QThread):
    def __init__(self, directory, port=8765, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.port = port
        self._server = None

    def run(self):
        os.chdir(self.directory)
        handler = SimpleHTTPRequestHandler
        self._server = ThreadingTCPServer(("127.0.0.1", self.port), handler)
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
