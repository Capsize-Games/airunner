from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWizard, QWizardPage, QVBoxLayout, QLabel, QCheckBox, QProgressBar
from PySide6.QtCore import QThread, Signal
from huggingface_hub import hf_hub_download, snapshot_download
from tqdm.asyncio import tqdm
from tqdm import tqdm
from threading import RLock

from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.mediator_mixin import MediatorMixin
from airunner.widgets.export_preferences.export_preferences_widget import ExportPreferencesWidget
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.templates.airunner_license_ui import Ui_airunner_license
from airunner.windows.setup_wizard.templates.path_settings_ui import Ui_PathSettings
from airunner.windows.setup_wizard.templates.stable_diffusion_license_ui import Ui_stable_diffusion_license
from airunner.windows.setup_wizard.templates.stable_diffusion_setup.choose_model_ui import Ui_choose_model
from airunner.windows.setup_wizard.templates.stable_diffusion_setup.choose_style_ui import Ui_choose_model_style
from airunner.windows.setup_wizard.templates.stable_diffusion_setup.choose_version_ui import Ui_choose_model_version
from airunner.windows.setup_wizard.templates.stable_diffusion_setup.controlnet_ui import Ui_controlnet_download
from airunner.windows.setup_wizard.templates.tts.bark_ui import Ui_bark_setup
from airunner.windows.setup_wizard.templates.tts.speech_t5_ui import Ui_speecht5_setup
from airunner.windows.setup_wizard.templates.user_agreement_ui import Ui_user_agreement
from airunner.windows.setup_wizard.templates.vision_setup.download_vision_models_ui import Ui_vision_setup


class BaseWizard(QWizardPage, MediatorMixin, SettingsMixin):
    class_name_ = None
    widget_class_ = None

    def __init__(self):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(BaseWizard, self).__init__()
        if self.class_name_:
            self.ui = self.class_name_()
            self.ui.setupUi(self)
        if self.widget_class_:
            widget = self.widget_class_()
            layout = QVBoxLayout()
            layout.addWidget(widget)
            self.setLayout(layout)
        self.initialize_form()

    def initialize_form(self):
        """
        Override this function to initialize form based on specific page in question.
        :return:
        """
        pass

    def save_settings(self):
        """
        Override this function to save settings based on specific page in question.
        :return:
        """
        pass

    def nextId(self):
        self.save_settings()
        return super().nextId()



class SetupWizard(QWizard, MediatorMixin, SettingsMixin):
    def __init__(self):
        super(SetupWizard, self).__init__()

        self.addPage(WelcomePage())

        settings = self.settings
        if not settings["agreements"]["user"]:
            self.addPage(UserAgreement())
        if not settings["agreements"]["stable_diffusion"]:
            self.addPage(StableDiffusionLicense())
        if not settings["agreements"]["airunner"]:
            self.addPage(AIRunnerLicense())

        self.addPage(PathSettings())
        self.addPage(ControlnetDownload())
        self.addPage(TTSSpeechT5Setup())
        self.addPage(TTSBarkSetup())

        # self.addPage(ChooseModelStyle())
        # self.addPage(ChooseModelVersion())
        # self.addPage(ChooseModel())

        self.addPage(MetaDataSettings())
        # self.addPage(ModelDownloadPage())
        self.addPage(FinalPage())
        self.setWindowTitle("AI Runner Setup Wizard")


class WelcomePage(BaseWizard):
    def __init__(self):
        super(WelcomePage, self).__init__()

        self.setTitle("Welcome")
        layout = QVBoxLayout()
        label = QLabel("Welcome to the AI Runner setup wizard. Click Next to continue.")
        layout.addWidget(label)
        self.setLayout(layout)


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def initialize_form(self):
        self.ui.base_path.setText(self.settings["path_settings"]["base_path"])

    def save_settings(self):
        settings = self.settings
        settings["path_settings"]["base_path"] = self.ui.base_path.text()
        self.settings = settings


class MetaDataSettings(BaseWizard):
    widget_class_ = ExportPreferencesWidget


class AgreementPage(BaseWizard):
    setting_key = ""

    def __init__(self):
        super(AgreementPage, self).__init__()
        self.user_agreement_clicked = False

    @Slot(bool)
    def agreement_clicked(self, val):
        self.user_agreement_clicked = val
        settings = self.settings
        settings["agreements"][self.setting_key] = val
        self.settings = settings

    def nextId(self):
        if self.user_agreement_clicked:
            return super().nextId()


class StableDiffusionLicense(AgreementPage):
    class_name_ = Ui_stable_diffusion_license
    setting_key = "stable_diffusion"


class AIRunnerLicense(AgreementPage):
    class_name_ = Ui_airunner_license
    setting_key = "airunner"


class UserAgreement(AgreementPage):
    class_name_ = Ui_user_agreement
    setting_key = "user"


class ChooseModelVersion(BaseWizard):
    class_name_ = Ui_choose_model_version


class ChooseModelStyle(BaseWizard):
    class_name_ = Ui_choose_model_style


class ChooseModel(BaseWizard):
    class_name_ = Ui_choose_model


class DownloadWizard(BaseWizard):
    def __init__(self):
        super(DownloadWizard, self).__init__()
        self.download_thread = None
        self.models_to_download = []
        self.ui.download.clicked.connect(self.download_models)
        self._original_text = self.ui.download.text()
        self.downloading = False
        self.ui.download.show()
        self.ui.cancel.hide()

    @Slot()
    def download_models(self):
        if not self.downloading:
            self.downloading = True
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


class DownloadThread(QThread):
    progress_updated = Signal(int, int)
    download_finished = Signal()

    def __init__(self, models_to_download):
        super().__init__()
        self.models_to_download = models_to_download
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
                snapshot_download(
                    repo_id=model["path"],
                    tqdm_class=tqdm_class,
                    repo_type=repo_type
                )
            except Exception as e:
                print(e)
                continue
            if tqdm_class is not None:
                self.progress_updated.emit(tqdm_class.n, tqdm_class.total)
        self.download_finished.emit()

    def stop(self):
        self._stop_event = True


class ControlnetDownload(DownloadWizard):
    class_name_ = Ui_controlnet_download

    def __init__(self):
        super(ControlnetDownload, self).__init__()
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
            checkbox.stateChanged.connect(lambda _contrlnet=controlnet: self.models_to_download.append(_contrlnet))
            self.ui.tableWidget.setCellWidget(index, 0, checkbox)
            self.ui.tableWidget.setCellWidget(index, 1, label)
            self.ui.tableWidget.setCellWidget(index, 2, progress_bar)

    def start_download(self):
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()


class CustomTqdmProgressBar:
    def __init__(self, progress_bar):
        self.progress_bar = progress_bar
        self._lock = None

    def __call__(self, iterable=None, desc=None, total=None, leave=True, file=None, ncols=None, mininterval=0.1, maxinterval=10.0, miniters=None, ascii=None, disable=False, unit='it', unit_scale=False, dynamic_ncols=False, smoothing=0.3, bar_format=None, initial=0, position=None, postfix=None, unit_divisor=1000, write_bytes=None, lock_args=None, nrows=None, colour=None, delay=0, gui=False, **kwargs):
        if total is None:
            total = self.progress_bar.maximum()
        self.tqdm_instance = tqdm(iterable=iterable, desc=desc, total=total, leave=leave, file=file, ncols=ncols, mininterval=mininterval, maxinterval=maxinterval, miniters=miniters, ascii=ascii, disable=disable, unit=unit, unit_scale=unit_scale, dynamic_ncols=dynamic_ncols, smoothing=smoothing, bar_format=bar_format, initial=initial, position=position, postfix=postfix, unit_divisor=unit_divisor, write_bytes=write_bytes, lock_args=lock_args, nrows=nrows, colour=colour, delay=delay, gui=gui, **kwargs)
        return self.tqdm_instance

    @property
    def n(self):
        return self.tqdm_instance.n

    @property
    def total(self):
        return self.tqdm_instance.total

    def update(self, n=1):
        self.tqdm_instance.update(n)
        self.progress_bar.setValue(self.tqdm_instance.n)

    def close(self):
        self.tqdm_instance.close()
        self.progress_bar.setValue(self.progress_bar.maximum())

    def set_lock(self, lock):
        self._lock = lock

    def get_lock(self):
        return self._lock

    def clear(self):
        if hasattr(self, '_lock'):
            del self._lock


class VisionSetup(DownloadWizard):
    class_name_ = Ui_vision_setup

    def __init__(self):
        super(VisionSetup, self).__init__()
        self.ui.lineEdit.setText(self.settings["ocr_settings"]["path"])


class TTSSpeechT5Setup(DownloadWizard):
    class_name_ = Ui_speecht5_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["embeddings_path"],
                    "repo_type": "dataset",
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["vocoder_path"]
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["model_path"]
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()


class TTSBarkSetup(DownloadWizard):
    class_name_ = Ui_bark_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": self.settings["tts_settings"]["bark"]["processor_path"]
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["bark"]["voice"]
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["bark"]["model_path"]
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()


class FinalPage(BaseWizard):
    def __init__(self):
        super(FinalPage, self).__init__()

        self.setTitle("Setup Complete")
        layout = QVBoxLayout()
        label = QLabel("Setup is complete. Click Finish to close the wizard.")
        layout.addWidget(label)
        self.setLayout(layout)

        settings = self.settings
        settings["run_setup_wizard"] = False
        self.settings = settings
