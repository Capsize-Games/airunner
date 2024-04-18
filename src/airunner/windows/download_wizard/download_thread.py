from PySide6.QtCore import QThread, Signal
from huggingface_hub import hf_hub_download, snapshot_download
from airunner.windows.download_wizard.custom_tqdm_progress_bar import CustomTqdmProgressBar


class DownloadThread(QThread):
    progress_updated = Signal(int, int)
    download_finished = Signal()
    file_download_finished = Signal()

    def __init__(self, models_to_download):
        super().__init__()
        self.models_to_download = models_to_download
        print(self.models_to_download)
        self._stop_event = False

    def run(self):
        for index, data in enumerate(self.models_to_download):
            if self._stop_event:
                break
            if "progress_bar" in self.models_to_download[index]:
                self.models_to_download[index]["progress_bar"].setValue(0)
            model = data["model"]
            tqdm_class = None
            if "tqdm_class" in data:
                tqdm_class = data["tqdm_class"]
            if "progress_bar" in data:
                tqdm_class = CustomTqdmProgressBar(data["progress_bar"])
                data["tqdm_class"] = tqdm_class
            self.models_to_download[index] = data
            if "repo_type" in model:
                repo_type = model["repo_type"]
            else:
                repo_type = None
            try:
                if "files" in model:
                    for filename in model["files"]:
                        hf_hub_download(
                            repo_id=model["path"],
                            filename=filename,
                            repo_type=repo_type
                        )
                        self.file_download_finished.emit()
                else:
                    snapshot_download(
                        repo_id=model["path"],
                        repo_type=repo_type,
                        tqdm_class=tqdm_class
                    )
            except Exception as e:
                print(e)
                continue
            if tqdm_class is not None:
                self.progress_updated.emit(tqdm_class.n, tqdm_class.total)
        self.download_finished.emit()

    def stop(self):
        self._stop_event = True

