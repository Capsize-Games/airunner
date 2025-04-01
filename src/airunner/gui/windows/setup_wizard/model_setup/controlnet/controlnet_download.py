from PySide6.QtWidgets import QLabel, QCheckBox, QProgressBar
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.gui.windows.download_wizard.download_thread import DownloadThread
from airunner.gui.windows.download_wizard.download_wizard_page import DownloadWizardPage


class ControlnetDownload(DownloadWizardPage):
    def __init__(self, *args):
        super(ControlnetDownload, self).__init__(*args)

        self.download_thread = None
        self.models_to_download = []
        self.ui.tableWidget.setRowCount(len(controlnet_bootstrap_data))
        self.ui.tableWidget.setColumnCount(3)
        for index, controlnet in enumerate(controlnet_bootstrap_data):
            label = QLabel(controlnet["name"])
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            progress_bar = QProgressBar()
            progress_bar.setValue(0)
            progress_bar.setMaximum(100)
            self.models_to_download.append(dict(
                model=controlnet,
                progress_bar=progress_bar
            ))
            checkbox.stateChanged.connect(lambda _controlnet=controlnet: self.models_to_download.append(_controlnet))
            self.ui.tableWidget.setCellWidget(index, 0, checkbox)
            self.ui.tableWidget.setCellWidget(index, 1, label)
            self.ui.tableWidget.setCellWidget(index, 2, progress_bar)

    def start_download(self):
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()
