import os
from urllib.parse import urlparse

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.import_ui import Ui_import_model_widget
from airunner.aihandler.stablediffusion.download_civitai import DownloadCivitAI
from airunner.aihandler.stablediffusion.download_huggingface import DownloadHuggingface
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin


class ImportWidget(
    BaseWidget,
    PipelineMixin,
    AIModelMixin
):
    widget_class_ = Ui_import_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        AIModelMixin.__init__(self)
        self.current_model_data = None
        self.is_civitai = False
        self.register(SignalCode.DOWNLOAD_COMPLETE, self.show_download_complete)
        self.show_import_form()
        self.download_civit_ai = DownloadCivitAI()
        self.download_huggingface = DownloadHuggingface()

    def action_clicked_button_import(self):
        self.show_model_select_form()

    def action_clicked_button_download(self):
        self.show_download_form()

    def action_clicked_button_cancel(self):
        if self.is_civitai:
            self.download_civit_ai.stop_download()
        else:
            self.download_huggingface.stop_download()
        self.show_import_form()

    def action_download_complete_continue(self):
        self.show_import_form()

    def show_import_form(self):
        self.ui.import_form.show()
        self.ui.model_select_form.hide()
        self.ui.download_form.hide()
        self.ui.download_complete_form.hide()

    def show_model_select_form(self):
        self.ui.import_form.hide()
        self.ui.model_select_form.show()
        self.ui.download_form.hide()
        self.ui.download_complete_form.hide()
        self.import_models()

    def show_download_form(self):
        self.ui.import_form.hide()
        self.ui.model_select_form.hide()
        self.ui.download_form.show()
        self.ui.download_complete_form.hide()
        self.download_model()

    def show_download_complete(self, data=None):
        self.ui.import_form.hide()
        self.ui.model_select_form.hide()
        self.ui.download_form.hide()
        self.ui.download_complete_form.show()
    
    def download_model(self):
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
        file_path = self.download_path(
            file,
            diffuser_model_version,
            pipeline_action,
            model_type
        )

        trained_words = model_version.get("trainedWords", [])
        if isinstance(trained_words, str):
            trained_words = [trained_words]
        trained_words = ",".join(trained_words)
        if model_type == "Checkpoint":
            self.emit_signal(SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, {
                'name': name,
                'path': file_path,
                'branch': "main",
                'version': diffuser_model_version,
                'category': category,
                'pipeline_action': pipeline_action,
                'enabled': True,
                'is_default': False
            })
        elif model_type == "LORA":
            name = file["name"].replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
            lora_data = dict(
                name=name,
                path=file_path,
                scale=1,
                enabled=True,
                loaded=False,
                trigger_word=trained_words,
                version=model_version["baseModel"]
            )
            self.emit_signal(SignalCode.LORA_ADD_SIGNAL, lora_data)
        elif model_type == "TextualInversion":
            # name = file_path.split("/")[-1].split(".")[0]
            # embedding_exists = session.query(Embedding).filter_by(
            #     name=name,
            #     path=file_path,
            # ).first()
            # if not embedding_exists:
            #     new_embedding = Embedding(
            #         name=name,
            #         path=file_path,
            #         active=True,
            #         tags=trained_words,
            #     )
            #     session.add(new_embedding)
            # TODO: handle textual inversion
            pass
        elif model_type == "VAE":
            # todo save vae here
            pass
        elif model_type == "Controlnet":
            # todo save controlnet here
            pass
        elif model_type == "Poses":
            # todo save poses here
            pass
        
        self.logger.debug("starting download")
        self.ui.downloading_label.setText(f"Downloading {name}")
        self.download_model_thread(download_url, file_path, size_kb)
        # self.thread = threading.Thread(target=self.download_model_thread, args=(download_url, file_path, size_kb))
        # self.thread.start()

    def download_model_thread(self, download_url, file_path, size_kb):
        if self.is_civitai:
            self.download_civit_ai.download_model(download_url, file_path, size_kb, self.download_callback)
        else:
            self.download_huggingface.download_model(download_url, callback=self.download_callback)

    def download_callback(self, current_size, total_size):
        current_size = int(current_size / total_size * 100)
        self.ui.download_progress_bar.setValue(current_size)
        if current_size >= total_size:
            self.reset_form()
            self.emit_signal(SignalCode.AI_MODELS_CREATE_SIGNAL, {
                "models": self.current_model_data
            })
            self.show_items_in_scrollarea()

    def reset_form(self):
        self.ui.download_progress_bar.setValue(0)
        self.ui.download_progress_bar.hide()
        self.ui.downloading_label.hide()
        self.ui.cancel_download_button.hide()

    def show_items_in_scrollarea(self):
        self.ui.import_form.show()
        self.ui.model_select_form.hide()
        self.ui.download_form.hide()
        self.ui.download_complete_form.hide()
        self.import_models()

    def parse_url(self) -> str:
        url = self.ui.import_url.text()
        try:
            model_id = url.split("models/")[1]
        except IndexError:
            model_id = None
        parsed_url = urlparse(url)
        self.is_civitai = "civitai.com" in parsed_url.netloc
        return model_id

    def import_models(self):
        data = None
        model_id = self.parse_url()

        if model_id:
            data = DownloadCivitAI.get_json(model_id)

        self.current_model_data = data

        if data is not None:
            model_name = data["name"]
            model_versions = data["modelVersions"]
        else:
            model_name = ""
            model_versions = []

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

        if data:
            self.ui.name.setText(data["name"])
            self.ui.name.show()
            if not data["nsfw"]:
                self.ui.nsfw_label.hide()
            else:
                self.ui.nsfw_label.show()

            if "creator" in data and "username" in data["creator"]:
                self.ui.creator.setText(
                    f"By {data['creator']['username']}"
                )
            else:
                self.ui.creator.show()
                self.ui.creator.setText("")
        else:
            self.ui.name.hide()
            self.ui.nsfw_label.hide()
            self.ui.creator.hide()

        self.set_model_form_data()
    
    def model_version_changed(self, index):
        self.set_model_form_data()
    
    def download_path(self, file, version, pipeline_action, model_type):

        if model_type == "LORA":
            path = self.settings["path_settings"]["lora_model_path"]
        elif model_type == "Checkpoint":
            if pipeline_action == "txt2img":
                path = self.settings["path_settings"]["txt2img_model_path"]
            elif pipeline_action == "outpaint":
                path = self.settings["path_settings"]["inpaint_model_path"]
            elif pipeline_action == "upscale":
                path = self.settings["path_settings"]["upscale_model_path"]
            elif pipeline_action == "depth2img":
                path = self.settings["path_settings"]["depth2img_model_path"]
            elif pipeline_action == "pix2pix":
                path = self.settings["path_settings"]["pix2pix_model_path"]
        elif model_type == "TextualInversion":
            path = self.settings["path_settings"]["embeddings_model_path"]
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

    def get_pipeline_classname(self, pipeline_action, version, category):
        pipelines = self.get_pipelines(pipeline_action, version, category)
        if len(pipelines) > 0:
            return pipelines[0]["classname"]
        else:
            return None

    def set_model_form_data(self):
        try:
            download_url, file, model_version = self.ui.model_choices.currentData()
        except TypeError:
            return
        model_version_name = model_version["name"]

        categories = self.ai_model_categories()
        actions = [pipeline["pipeline_action"] for pipeline in self.settings["pipelines"]]
        category = "stablediffusion"
        pipeline_action = "txt2img"
        if "inpaint" in model_version_name:
            pipeline_action = "outpaint"
        diffuser_model_version = model_version["baseModel"]
        pipeline_class = self.get_pipeline_classname(pipeline_action, diffuser_model_version, category)
        diffuser_model_versions = self.ai_model_versions()
        path = self.download_path(
            file,
            diffuser_model_version,
            pipeline_action,
            self.current_model_data["type"]
        )

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
