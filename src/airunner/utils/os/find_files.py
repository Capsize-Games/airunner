import os
import mimetypes
from PySide6.QtCore import Signal
from airunner.workers.worker import Worker
from airunner.utils.application.create_worker import create_worker


class FindFilesWorker(Worker):
    files_found = Signal(list)

    def __init__(self, path, file_extension, recursive=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = os.path.expanduser(path)
        # Accept file_extension as a string or list of strings
        if isinstance(file_extension, str):
            self.file_extensions = [file_extension.lower().lstrip(".")]
        else:
            self.file_extensions = [
                ext.lower().lstrip(".") for ext in file_extension
            ]
        self.recursive = recursive

    def handle_message(self, _message=None):
        found_files = []
        for root, dirs, files in os.walk(self.path):
            for fname in files:
                for ext in self.file_extensions:
                    if fname.lower().endswith("." + ext):
                        abs_path = os.path.abspath(os.path.join(root, fname))
                        mime, _ = mimetypes.guess_type(abs_path)
                        found_files.append(abs_path)
                        break  # Only add once per file
            if not self.recursive:
                break
        self.files_found.emit(found_files)


def find_files(
    path: str = "~",
    file_extension="md",
    recursive: bool = True,
    callback=None,
):
    """
    Launches a worker to find files with the given extension(s) under path.
    file_extension can be a string or a list of strings.
    Calls callback(list_of_files) when done, if callback is provided.
    """
    worker = create_worker(
        FindFilesWorker,
        path=path,
        file_extension=file_extension,
        recursive=recursive,
    )
    if callback:
        worker.files_found.connect(callback)
    # Trigger the worker by adding a dummy message to the queue
    worker.add_to_queue({})
    return worker
