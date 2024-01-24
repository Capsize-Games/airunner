from urllib.parse import urlparse

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.import_ui import Ui_import_model_widget
from airunner.aihandler.download_civitai import DownloadCivitAI


class ImportWidget(BaseWidget):
    widget_class_ = Ui_import_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_import_form()

    def action_clicked_button_import(self):
        self.show_model_select_form()

    def action_clicked_button_download(self):
        self.show_download_form()

    def action_clicked_button_cancel(self):
        self.show_import_form()

    def show_import_form(self):
        self.ui.import_form.show()
        self.ui.model_select_form.hide()
        self.ui.download_form.hide()

    def show_model_select_form(self):
        print("SHOW MODEL SELECT FORM")
        self.ui.import_form.hide()
        self.ui.model_select_form.show()
        self.ui.download_form.hide()
        self.import_models()

    def show_download_form(self):
        self.ui.import_form.hide()
        self.ui.model_select_form.hide()
        self.ui.download_form.show()
        self.download_model()
    
    def download_model(self):
        print("DOWNLOAD MODEL")
        self.download_civit_ai = DownloadCivitAI()

        # get value from import_widget.model_choices
        download_url, file, model_version = self.ui.model_choices.currentData()
        size_kb = file["sizeKB"]

        model_data = self.current_model_data
        name = model_data["name"] + " " + model_version["name"]
        
        model_version_name = model_version["name"]
        category = "stablediffusion"
        pipeline_action = "txt2img"
        if "inpaint" in model_version_name:
            pipeline_action = "outpaint"
        diffuser_model_version = model_version["baseModel"]
        model_type = model_data["type"]
        file_path = self.download_path(file, diffuser_model_version, pipeline_action, model_type)  # path is the download path of the model

        trained_words = model_version.get("trainedWords", [])
        if isinstance(trained_words, str):
            trained_words = [trained_words]
        trained_words = ",".join(trained_words)
        if model_type == "Checkpoint":
            self.emit("model_save_or_update_signal", dict(
                name=name,
                path=file_path,
                branch="main",
                version=diffuser_model_version,
                category=category,
                pipeline_action=pipeline_action,
                enabled=True,
                is_default=False
            ))
        elif model_type == "LORA":
            lora_exists = session.query(Lora).filter_by(
                name=name,
                path=file_path,
            ).first()
            if not lora_exists:
                new_lora = Lora(
                    name=name,
                    path=file_path,
                    scale=1,
                    enabled=True,
                    loaded=False,
                    trigger_word=trained_words,
                )
                session.add(new_lora)
        elif model_type == "TextualInversion":
            name = file_path.split("/")[-1].split(".")[0]
            embedding_exists = session.query(Embedding).filter_by(
                name=name,
                path=file_path,
            ).first()
            if not embedding_exists:                
                new_embedding = Embedding(
                    name=name,
                    path=file_path,
                    active=True,
                    tags=trained_words,
                )
                session.add(new_embedding)
        elif model_type == "VAE":
            # todo save vae here
            pass
        elif model_type == "Controlnet":
            # todo save controlnet here
            pass
        elif model_type == "Poses":
            # todo save poses here
            pass
        
        print("starting download")
        self.download_model_thread(download_url, file_path, size_kb)
        # self.thread = threading.Thread(target=self.download_model_thread, args=(download_url, file_path, size_kb))
        # self.thread.start()

    def download_model_thread(self, download_url, file_path, size_kb):
        self.download_civit_ai.download_model(download_url, file_path, size_kb, self.download_callback)

    def download_callback(self, current_size, total_size):
        current_size = int(current_size / total_size * 100)
        self.ui.download_progress_bar.setValue(current_size)
        if current_size >= total_size:
            self.reset_form()
            self.emit("ai_model_create_signal", self.current_model_data)
            self.show_items_in_scrollarea()
    
    def import_models(self):
        url = self.ui.import_url.text()
        try:
            model_id = url.split("models/")[1]
        except IndexError:
            return

        data = DownloadCivitAI.get_json(model_id)
        if data is None:
            self.logger.error("Failed to get JSON from CivitAI")
            return
        self.current_model_data = data
        parsed_url = urlparse(url)
        self.is_civitai = "civitai.com" in parsed_url.netloc
        model_name = data["name"]
        model_versions = data["modelVersions"]
        self.ui.model_choices.clear()
        for model_version in model_versions:
            version_name = model_version["name"]
            download_url = model_version["downloadUrl"]
            sd_model_version = model_version["baseModel"]
            files = model_version["files"]
            # try:
            #     url = file["url"]
            # except KeyError:
            #     url = ""
            download_choice = f"{model_name} - {version_name} - {sd_model_version}"
            for file in files:
                self.ui.model_choices.addItem(
                    download_choice, 
                    (download_url, file, model_version)
                )

        self.ui.model_choices.currentIndexChanged.connect(self.model_version_changed)

        self.ui.name.setText(self.current_model_data["name"])
        if not self.current_model_data["nsfw"]:
            self.ui.nsfw_label.hide()
        else:
            self.ui.nsfw_label.show()
        
        if "creator" in self.current_model_data and "username" in self.current_model_data["creator"]:
            self.ui.creator.setText(
                f"By {self.current_model_data['creator']['username']}"
            )
        else:
            self.ui.creator.setText("")

        #self.current_model_object.url = url

        self.set_model_form_data()
    
    def model_version_changed(self, index):
        self.set_model_form_data()
    
    def download_path(self, file, version, pipeline_action, model_type):

        if model_type == "LORA":
            path = self.path_settings["lora_model_path"]
        elif model_type == "Checkpoint":
            if pipeline_action == "txt2img":
                path = self.path_settings["txt2img_model_path"]
            elif pipeline_action == "outpaint":
                path = self.path_settings["outpaint_model_path"]
            elif pipeline_action == "upscale":
                path = self.path_settings["upscale_model_path"]
            elif pipeline_action == "depth2img":
                path = self.path_settings["depth2img_model_path"]
            elif pipeline_action == "pix2pix":
                path = self.path_settings["pix2pix_model_path"]
        elif model_type == "TextualInversion":
            path = self.path_settings["embeddings_model_path"]
        elif model_type == "VAE":
            # todo save vae here
            pass
        elif model_type == "Controlnet":
            # todo save controlnet here
            pass
        elif model_type == "Poses":
            # todo save poses here
            pass

        file_name = file["name"]
        return f"{path}/{version}/{file_name}"

    def set_model_form_data(self):
        try:
            download_url, file, model_version = self.ui.model_choices.currentData()
        except TypeError:
            return
        model_version_name = model_version["name"]

        categories = self.get_service("ai_model_categories")()
        actions = self.get_service("pipeline_actions")()
        category = "stablediffusion"
        pipeline_action = "txt2img"
        if "inpaint" in model_version_name:
            pipeline_action = "outpaint"
        diffuser_model_version = model_version["baseModel"]
        pipeline_class = self.get_service("get_pipeline_classname")(pipeline_action, diffuser_model_version, category)
        diffuser_model_versions = self.get_service("ai_model_versions")()
        path = self.download_path(file, diffuser_model_version, pipeline_action, self.current_model_data["type"])  # path is the download path of the model

        self.ui.model_form.set_model_form_data(
            categories, 
            actions, 
            diffuser_model_versions, 
            category, 
            pipeline_action, 
            pipeline_class, 
            diffuser_model_version, 
            path, 
            self.current_model_data["name"],
            model_data=self.current_model_data,
            model_type=self.current_model_data["type"]
        )

        if self.is_civitai:
            self.ui.model_form.ui.branch_label.hide()
            self.ui.model_form.ui.branch_line_edit.hide()
