from PySide6.QtCore import QThread, Signal
from airunner.utils.network.huggingface_downloader import HuggingfaceDownloader


class DownloadThread(QThread):
    progress_updated = Signal(int, int)
    download_finished = Signal()
    file_download_finished = Signal()

    def __init__(self, models_to_download):
        super().__init__()
        self.hf_downloader = None
        self.models_to_download = models_to_download
        self._stop_event = False

    def run(self):
        self.hf_downloader = HuggingfaceDownloader()
        self.hf_downloader.completed.connect(
            lambda: self.file_download_finished.emit()
        )
        for index, data in enumerate(self.models_to_download):
            if self._stop_event:
                break
            if "progress_bar" in self.models_to_download[index]:
                self.models_to_download[index]["progress_bar"].setValue(0)
            model = data["model"]
            self.models_to_download[index] = data
            try:
                if "files" in model:
                    for filename in model["files"]:
                        # hf_hub_download(
                        #     repo_id=model["path"],
                        #     filename=filename,
                        #     repo_type=repo_type
                        # )
                        self.hf_downloader.download_model(
                            requested_path=model["path"],
                            requested_file_name=filename,
                            requested_file_path=model["path"],
                            requested_callback=self.progress_updated.emit
                        )
                else:
                    print("Skipping download for model with no files {}".format(model["name"]))
            except Exception as e:
                print(e)
                continue
        self.download_finished.emit()

    def stop(self):
        self._stop_event = True

