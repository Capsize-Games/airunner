from PyQt6.QtWidgets import QFileDialog
from airunner.windows.base_window import BaseWindow


class PreferencesWindow(BaseWindow):
    template_name = "preferences"
    window_title = "Preferences"

    def initialize_window(self):
        self.template.browseButton.clicked.connect(
            lambda: self.browse_for_model_base_path(self.template.sd_path))
        self.template.sd_path.textChanged.connect(
            lambda val: self.settings_manager.settings.model_base_path.set(val))
        self.template.depthtoimg_model_browse_button.clicked.connect(
            lambda: self.browse_for_depthtoimg_model_path(self.template.depthtoimg_model_path))
        self.template.depthtoimg_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.depth2img_model_path.set(val))
        self.template.pixtopix_model_browse_button.clicked.connect(
            lambda: self.browse_for_pixtopix_model_path(self.template.pixtopix_model_path))
        self.template.pixtopix_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.pix2pix_model_path.set(val))
        self.template.inpaint_outpaint_browse_button.clicked.connect(
            lambda: self.browse_for_inpaint_outpaint_model_path(self.template.inpaint_outpaint_model_path))
        self.template.upscale_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.upscale_model_path.set(val))
        self.template.upscale_browse_button.clicked.connect(
            lambda: self.browse_for_upscale_model_path(self.template.upscale_model_path))
        self.template.inpaint_outpaint_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.outpaint_model_path.set(val))
        self.template.embeddings_path.textChanged.connect(
            lambda val: self.settings_manager.settings.embeddings_path.set(val))
        self.template.embeddings_browse_button.clicked.connect(
            lambda: self.browse_for_embeddings_path(self.template.embeddings_path))
        self.template.lora_path.textChanged.connect(
            lambda val: self.settings_manager.settings.lora_path.set(val))
        self.template.lora_browse_button.clicked.connect(
            lambda: self.browse_for_lora_path(self.template.lora_path))
        self.template.image_path.textChanged.connect(
            lambda val: self.settings_manager.settings.image_path.set(val))
        self.template.image_path_browse_button.clicked.connect(
            lambda: self.browse_for_image_path(self.template.image_path))
        self.template.sd_path.setText(self.settings_manager.settings.model_base_path.get())
        self.template.depthtoimg_model_path.setText(self.settings_manager.settings.depth2img_model_path.get())
        self.template.pixtopix_model_path.setText(self.settings_manager.settings.pix2pix_model_path.get())
        self.template.inpaint_outpaint_model_path.setText(self.settings_manager.settings.outpaint_model_path.get())
        self.template.embeddings_path.setText(self.settings_manager.settings.embeddings_path.get())
        self.template.lora_path.setText(self.settings_manager.settings.lora_path.get())
        self.template.image_path.setText(self.settings_manager.settings.image_path.get())

        # Removing extensions settings until feature is complete:
        # self.template.hf_token.textChanged.connect(
        #     lambda val: self.settings_manager.settings.hf_api_key.set(val))
        # self.template.hf_token.setText(self.settings_manager.settings.hf_api_key.get())
        # self.initialize_extensions()  TODO: Extensions

    """
    TODO: Extensions
    def initialize_extensions(self):
        self.template.extensions_path.textChanged.connect(
            lambda val: self.settings_manager.settings.extensions_path.set(val))
        self.template.extensions_path.setText(
            self.settings_manager.settings.extensions_path.get())
        self.template.extensions_browse_button.clicked.connect(
            lambda: self.browse_for_extensions_path(self.template.extensions_path))
        self.app.do_preferences_injection(self)
    
    def browse_for_extensions_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.extensions_path.set(path)
    """

    def browse_for_model_base_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.model_base_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.model_base_path.set(path)

    def browse_for_embeddings_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.embeddings_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.embeddings_path.set(path)

    def browse_for_lora_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.lora_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.lora_path.set(path)

    def browse_for_image_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.image_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.image_path.set(path)

    def browse_for_depthtoimg_model_path(self, line_edit):
        # get path, not file
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.depth2img_model_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.depth2img_model_path.set(path)

    def browse_for_pixtopix_model_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.pix2pix_model_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.pix2pix_model_path.set(path)

    def browse_for_inpaint_outpaint_model_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.outpaint_model_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.outpaint_model_path.set(path)

    def browse_for_upscale_model_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.upscale_model_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.upscale_model_path.set(path)
