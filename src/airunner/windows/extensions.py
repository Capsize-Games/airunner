import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from aihandler.util import get_extensions_from_url, download_extension
from airunner.windows.base_window import BaseWindow


class ExtensionsWindow(BaseWindow):
    template_name = "extensions"
    window_title = "Extensions"

    def initialize_window(self):
        available_extensions = get_extensions_from_url(self.settings_manager.app)
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for extension in available_extensions:
            widget = uic.loadUi(os.path.join(f"pyqt/extension.ui"))
            widget.checkBox.setChecked(extension.name.get() in self.settings_manager.settings.enabled_extensions.get())
            widget.checkBox.setText(f"{extension.name.get()} - {extension.version.get()}")
            widget.checkBox.stateChanged.connect(lambda value, _extension=extension: self.on_checkbox_state_changed(value, _extension))
            widget.descriptionLabel.setText(extension.description.get())
            url = f"https://github.com/{extension.repo.get()}"
            widget.urlLabel.setText(url)
            widget.officialLabel.setText("Unofficial" if not extension.official.get() is True else "Official")
            widget.reviewedLabel.setText("Unreviewed" if not extension.reviewed.get() is True else "Reviewed")

            extension_repo = extension.repo.get()
            name = extension_repo.split("/")[-1]
            base_path = self.settings_manager.settings.model_base_path.get()
            extensions_path = self.settings_manager.settings.extensions_path.get() or "extensions"
            if extensions_path == "extensions":
                extensions_path = os.path.join(base_path, extensions_path)
            widget.installButton.clicked.connect(
                lambda x,
                _repo=extension_repo,
                _url=url,
                _path=extensions_path,
                _btn=widget.installButton,
                _remove_btn=widget.removeButton:
                    self.install(_repo, _url, _path, _btn, _remove_btn)
            )
            widget.removeButton.clicked.connect(
                lambda x,
                _btn=widget.removeButton,
                _install_btn=widget.installButton,
                _pth=extensions_path:
                    self.remove(_pth, _btn, _install_btn)
            )
            if os.path.exists(extensions_path):
                # change the download button to "update"
                widget.installButton.setText("Update")
                # enable the remove button
                widget.removeButton.setEnabled(True)
            else:
                # disable the remove button
                widget.removeButton.setEnabled(False)
                #     download_extension(extension_repo, extension_path)

            # add widget to self.template.scrollArea:QScrollArea
            container.layout().addWidget(widget)
            self.settings_manager.settings.available_extensions.append(extension)
        self.template.scrollArea.setWidget(container)

    def on_checkbox_state_changed(self, state, extension):
        extension.enabled.set(state == 2)
        # add extension to self.settings_manager.settings.enabled_extensions
        if state == 2:
            self.settings_manager.settings.enabled_extensions.append(extension.name.get())
        elif extension.name.get() in self.settings_manager.settings.enabled_extensions.get():
            self.settings_manager.settings.enabled_extensions.remove(extension.name.get())
        self.settings_manager.save_settings()

    def remove(self, path, button, install_button):
        install_button.setEnabled(False)
        button.setEnabled(False)
        self.delete_existing(path)
        install_button.setEnabled(True)
        install_button.setText("Install")

    def delete_existing(self, path):
        for root, dirs, files in os.walk(path, topdown=False):
            os.chmod(root, 0o777)
            for name in files:
                os.chmod(os.path.join(root, name), 0o777)
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o777)
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)

    def install(self, repo, url, path, button, remove_button):
        # check if text is Update, if so, call "Update" instaed of "Install"
        if button.text() == "Update":
            self.update(repo, url, path, button, remove_button)
            return
        button.setText("...")
        button.setEnabled(False)
        self.template.repaint()
        download_extension(url, path)
        button.setText("Update")
        remove_button.setEnabled(True)
        button.setEnabled(True)
        self.template.repaint()

    def update(self, repo, url, path, button, remove_button):
        button.setText("...")
        button.setEnabled(False)
        self.template.repaint()
        # get the name of the repo
        name = repo.split("/")[-1]
        self.delete_existing(os.path.join(path, name))
        download_extension(url, path)
        button.setText("Update")
        remove_button.setEnabled(True)
        button.setEnabled(True)
        self.template.repaint()
