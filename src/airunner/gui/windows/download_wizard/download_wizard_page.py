from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard


class DownloadWizardPage(BaseWizard):
    def __init__(self, *args):
        super(DownloadWizardPage, self).__init__(*args)
        self.download_thread = None
        self.models_to_download = []
        if self.ui:
            self.ui.download.clicked.connect(self.download_models)
        self._original_text = self.ui.download.text()
        self.downloading = False
        self.ui.download.show()
        self.ui.cancel.hide()

    @Slot()
    def download_models(self):
        if not self.downloading:
            self.downloading = True
            if self.ui:
                self.ui.download.setText("Cancel")
                self.ui.download.hide()
                self.ui.cancel.show()
            self.start_download()

    def start_download(self):
        """
        Placeholder for download function
        :return:
        """
        pass

    @Slot()
    def cancel(self):
        self.downloading = False
        if self.ui:
            self.ui.download.setText(self._original_text)
            self.ui.download.show()
            self.ui.cancel.hide()

    def update_progress(self, current, total):
        for data in self.models_to_download:
            if "progress_bar" in data:
                progress_bar = data["progress_bar"]
                progress_bar.setMaximum(total)
                progress_bar.setValue(current)

    def download_finished(self):
        for data in self.models_to_download:
            if "tqdm_class" in data:
                data["tqdm_class"].clear()

    def closeEvent(self, event):
        if self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
        event.accept()
