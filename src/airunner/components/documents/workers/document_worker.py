import os
from PySide6.QtCore import QFileSystemWatcher, QEventLoop

from airunner.enums import SignalCode
from airunner.components.application.workers.worker import Worker
from airunner.components.documents.data.models.document import Document


class DocumentWorker(Worker):
    """Worker responsible for monitoring document directory and syncing with database."""

    def __init__(self):
        self.signal_handlers = {}
        super().__init__()
        self.file_extensions = [
            "md",
            "txt",
            "docx",
            "doc",
            "odt",
            "pdf",
            "epub",
            "zim",
        ]
        self._file_system_watcher = None
        self._watched_directories = set()
        self._known_files = set()
        self.setup_file_system_watcher()

    @property
    def documents_path(self) -> str:
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/documents",
        )

    @property
    def zim_path(self) -> str:
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "zim",
        )

    def setup_file_system_watcher(self):
        """Initialize the file system watcher for both documents and ZIM directories."""
        if not os.path.exists(self.documents_path):
            os.makedirs(self.documents_path, exist_ok=True)

        if not os.path.exists(self.zim_path):
            os.makedirs(self.zim_path, exist_ok=True)

        self._file_system_watcher = QFileSystemWatcher()
        self._file_system_watcher.directoryChanged.connect(
            self.on_directory_changed
        )

        self._watch_directory_recursively(self.documents_path)
        self._watch_directory_recursively(self.zim_path)
        self._sync_documents_with_directory()

    def _watch_directory_recursively(self, directory: str):
        """Add directory and all subdirectories to the file system watcher."""
        if not os.path.exists(directory):
            return

        if directory not in self._watched_directories:
            self._file_system_watcher.addPath(directory)
            self._watched_directories.add(directory)

        for root, dirs, files in os.walk(directory):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if dir_path not in self._watched_directories:
                    self._file_system_watcher.addPath(dir_path)
                    self._watched_directories.add(dir_path)

    def on_directory_changed(self, path: str):
        """Handle directory change events."""
        self.logger.debug(f"Directory changed: {path}")
        self._watch_directory_recursively(self.documents_path)
        self._watch_directory_recursively(self.zim_path)
        self._sync_documents_with_directory()

    def _sync_documents_with_directory(self):
        """Sync database with actual files in both documents and ZIM directories."""
        current_files = set()
        documents_added = False
        documents_removed = False

        # Scan both directories
        for doc_dir in [self.documents_path, self.zim_path]:
            if not os.path.exists(doc_dir):
                self.logger.warning(f"Directory does not exist: {doc_dir}")
                continue

            for root, dirs, files in os.walk(doc_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    ext = os.path.splitext(fname)[1][1:].lower()
                    if ext in self.file_extensions:
                        current_files.add(fpath)

                        if fpath not in self._known_files:
                            exists = Document.objects.filter_by(path=fpath)
                            if not exists or len(exists) == 0:
                                Document.objects.create(
                                    path=fpath, active=False, indexed=False
                                )
                                self.logger.info(
                                    f"Added document to database: {fname}"
                                )
                                documents_added = True

        deleted_files = self._known_files - current_files
        for fpath in deleted_files:
            docs = Document.objects.filter_by(path=fpath)
            if docs and len(docs) > 0:
                Document.objects.delete(pk=docs[0].id)
                fname = os.path.basename(fpath)
                self.logger.info(f"Removed document from database: {fname}")
                documents_removed = True

        self._known_files = current_files

        if documents_added or documents_removed:
            print("DOCUMENT COLLECTION HAS CHANGED")
            self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED)

    def handle_message(self, message):
        """Handle messages from the queue."""

    def run(self):
        """Worker run loop - process events for QFileSystemWatcher and handle messages."""
        self.running = True
        event_loop = QEventLoop()
        while self.running:
            event_loop.processEvents()  # Process QFileSystemWatcher signals
            self.preprocess()
            self.run_thread()
        event_loop.quit()
