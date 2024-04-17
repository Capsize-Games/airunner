from PySide6.QtCore import Slot

from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.templates.controlnet_ui import Ui_controlnet_download


class ControlnetDownload(BaseWizard):
    class_name_ = Ui_controlnet_download

    def __init__(self, *args):
        super(ControlnetDownload, self).__init__(*args)
        self.toggled_no = False
        self.toggled_yes = False

    @Slot(bool)
    def no_toggled(self, val: bool):
        self.toggled_no = val

    @Slot(bool)
    def yes_toggled(self, val: bool):
        self.toggled_yes = val

        # self.download_thread = None
        # self.models_to_download = []
        # self.ui.tableWidget.setRowCount(len(controlnet_bootstrap_data))
        # self.ui.tableWidget.setColumnCount(3)
        # for index, controlnet in enumerate(controlnet_bootstrap_data):
        #     label = QLabel(controlnet["name"])
        #     checkbox = QCheckBox()
        #     checkbox.setChecked(True)
        #     progress_bar = QProgressBar()
        #     progress_bar.setValue(0)
        #     progress_bar.setMaximum(100)
        #     self.models_to_download.append(dict(
        #         model=controlnet,
        #         progress_bar=progress_bar
        #     ))
        #     checkbox.stateChanged.connect(lambda _controlnet=controlnet: self.models_to_download.append(_controlnet))
        #     self.ui.tableWidget.setCellWidget(index, 0, checkbox)
        #     self.ui.tableWidget.setCellWidget(index, 1, label)
        #     self.ui.tableWidget.setCellWidget(index, 2, progress_bar)

    # def start_download(self):
    #     self.download_thread = DownloadThread(self.models_to_download)
    #     self.download_thread.progress_updated.connect(self.update_progress)
    #     self.download_thread.download_finished.connect(self.download_finished)
    #     self.download_thread.start()

