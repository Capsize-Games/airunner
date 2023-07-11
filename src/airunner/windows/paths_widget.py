from PyQt6.QtWidgets import QFileDialog
from airunner.windows.custom_widget import CustomWidget


class PathsWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="paths")
        self.initialize_window()

    def initialize_window(self):
        self.browseButton.clicked.connect(
            lambda: self.browse_for_model_base_path(self.sd_path))
        self.sd_path.textChanged.connect(
            lambda val: self.settings_manager.settings.model_base_path.set(val))
        self.depthtoimg_model_browse_button.clicked.connect(
            lambda: self.browse_for_depthtoimg_model_path(self.depthtoimg_model_path))
        self.depthtoimg_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.depth2img_model_path.set(val))
        self.pixtopix_model_browse_button.clicked.connect(
            lambda: self.browse_for_pixtopix_model_path(self.pixtopix_model_path))
        self.pixtopix_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.pix2pix_model_path.set(val))
        self.inpaint_outpaint_browse_button.clicked.connect(
            lambda: self.browse_for_inpaint_outpaint_model_path(self.inpaint_outpaint_model_path))
        self.upscale_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.upscale_model_path.set(val))
        self.upscale_browse_button.clicked.connect(
            lambda: self.browse_for_upscale_model_path(self.upscale_model_path))
        self.inpaint_outpaint_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.outpaint_model_path.set(val))
        self.txt2vid_model_path.textChanged.connect(
            lambda val: self.settings_manager.settings.txt2vid_model_path.set(val))
        self.txt2vid_browse_button.clicked.connect(
            lambda: self.browse_for_txt2vid_model_path(self.txt2vid_model_path))
        self.embeddings_path.textChanged.connect(
            lambda val: self.settings_manager.settings.embeddings_path.set(val))
        self.embeddings_browse_button.clicked.connect(
            lambda: self.browse_for_embeddings_path(self.embeddings_path))
        self.lora_path.textChanged.connect(
            lambda val: self.settings_manager.settings.lora_path.set(val))
        self.lora_browse_button.clicked.connect(
            lambda: self.browse_for_lora_path(self.lora_path))
        self.image_path.textChanged.connect(
            lambda val: self.settings_manager.settings.image_path.set(val))
        self.image_path_browse_button.clicked.connect(
            lambda: self.browse_for_image_path(self.image_path))
        self.video_path.textChanged.connect(
            lambda val: self.settings_manager.settings.video_path.set(val))
        self.video_path_browse_button.clicked.connect(
            lambda: self.browse_for_video_path(self.video_path))
        self.sd_path.setText(self.settings_manager.settings.model_base_path.get())
        self.depthtoimg_model_path.setText(self.settings_manager.settings.depth2img_model_path.get())
        self.pixtopix_model_path.setText(self.settings_manager.settings.pix2pix_model_path.get())
        self.inpaint_outpaint_model_path.setText(self.settings_manager.settings.outpaint_model_path.get())
        self.txt2vid_model_path.setText(self.settings_manager.settings.txt2vid_model_path.get())
        self.upscale_model_path.setText(self.settings_manager.settings.upscale_model_path.get())
        self.embeddings_path.setText(self.settings_manager.settings.embeddings_path.get())
        self.lora_path.setText(self.settings_manager.settings.lora_path.get())
        self.image_path.setText(self.settings_manager.settings.image_path.get())
        self.video_path.setText(self.settings_manager.settings.video_path.get())

        # Removing extensions settings until feature is complete:
        # self.hf_token.textChanged.connect(
        #     lambda val: self.settings_manager.settings.hf_api_key.set(val))
        # self.hf_token.setText(self.settings_manager.settings.hf_api_key.get())
        # self.initialize_extensions()  TODO: Extensions

    """
    TODO: Extensions
    def initialize_extensions(self):
        self.extensions_path.textChanged.connect(
            lambda val: self.settings_manager.settings.extensions_path.set(val))
        self.extensions_path.setText(
            self.settings_manager.settings.extensions_path.get())
        self.extensions_browse_button.clicked.connect(
            lambda: self.browse_for_extensions_path(self.extensions_path))
        self.app.do_preferences_injection(self)
    
    def browse_for_extensions_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.extensions_path.set(path)
    """

    def browse_for_txt2vid_model_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.txt2vid_model_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.txt2vid_model_path.set(path)

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

    def browse_for_video_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            self.settings_manager.settings.video_path.get())
        line_edit.setText(path)
        self.settings_manager.settings.video_path.set(path)

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
