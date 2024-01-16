import base64
import io
import os
import queue
import pickle
import platform
import subprocess
import sys
import uuid
import webbrowser
from functools import partial

from PyQt6 import uic, QtCore
from PyQt6.QtCore import pyqtSlot, Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow
from PyQt6 import QtGui
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QPixmap

from PIL import Image

from airunner.resources_light_rc import *
from airunner.resources_dark_rc import *
from airunner.aihandler.enums import MessageCode, Mode
from airunner.aihandler.logger import Logger
from airunner.aihandler.pyqt_client import OfflineClient
from airunner.aihandler.qtvar import MessageHandlerVar
from airunner.aihandler.settings import DEFAULT_BRUSH_PRIMARY_COLOR, DEFAULT_BRUSH_SECONDARY_COLOR, LOG_LEVEL
from airunner.airunner_api import AIRunnerAPI
from airunner.data.models import DEFAULT_PATHS
from airunner.filters.windows.filter_base import FilterBase
from airunner.input_event_manager import InputEventManager
from airunner.settings import BASE_PATH
from airunner.utils import get_version, auto_export_image, default_hf_cache_dir
from airunner.widgets.status.status_widget import StatusWidget
from airunner.windows.about.about import AboutWindow
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.update.update_window import UpdateWindow
from airunner.windows.video import VideoPopup
from airunner.widgets.brushes.brushes_container import BrushesContainer
from airunner.workers.image_data_worker import ImageDataWorker

class MainWindow(
    QMainWindow
):
    logger = Logger(prefix="MainWindow")
    # signals
    show_grid_toggled = pyqtSignal(bool)
    cell_size_changed_signal = pyqtSignal(int)
    line_width_changed_signal = pyqtSignal(int)
    line_color_changed_signal = pyqtSignal(str)
    canvas_color_changed_signal = pyqtSignal(str)
    snap_to_grid_changed_signal = pyqtSignal(bool)

    token_signal = pyqtSignal(str)
    api = None
    input_event_manager = None
    current_filter = None
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    is_saved = False
    action = "txt2img"
    message_var = MessageHandlerVar()
    progress_bar_started = False
    window = None
    history = None
    canvas = None
    _settings_manager = None
    models = None
    client = None
    _version = None
    _latest_version = None
    add_image_to_canvas_signal = pyqtSignal(dict)
    data = None  # this is set in the generator_mixin image_handler function and used for deterministic generation
    status_error_color = "#ff0000"
    status_normal_color_light = "#000000"
    status_normal_color_dark = "#ffffff"
    is_started = False
    _themes = None
    button_clicked_signal = pyqtSignal(dict)
    status_widget = None
    header_widget_spacer = None
    deterministic_window = None

    class History:
        def add_event(self, *args, **kwargs):
            print("TODO")
    history = History()

    _tabs = {
        "stablediffusion": {
            "txt2img": None,
            "outpaint": None,
            "depth2img": None,
            "pix2pix": None,
            "upscale": None,
            "superresolution": None,
            "txt2vid": None
        },
    }
    registered_settings_handlers = []
    image_generated = pyqtSignal(bool)
    controlnet_image_generated = pyqtSignal(bool)
    generator_tab_changed_signal = pyqtSignal()
    tab_section_changed_signal = pyqtSignal()
    image_data = pyqtSignal(dict)
    load_image = pyqtSignal(str)
    load_image_object = pyqtSignal(object)
    window_resized_signal = pyqtSignal(object)
    application_settings_changed_signal = pyqtSignal()

    generator = None
    _generator = None
    _generator_settings = None
    listening = False

    def handle_key_press(self, key):
        super().keyPressEvent(key)
        print(key.key())

        if self.key_matches("generate_image_key", key.key()):
            print("generate_image_key PRESSED")
    
    def key_matches(self, key_name, keyboard_key):
        if not key_name in self.settings["shortcut_key_settings"]:
            return False
        return self.settings["shortcut_key_settings"][key_name]["key"] == keyboard_key
    
    def key_text(self, key_name):
        if not key_name in self.settings["shortcut_key_settings"]:
            return ""
        return self.settings["shortcut_key_settings"][key_name]["text"]
    
    @property
    def settings(self):
        return self.application_settings.value("settings", dict(
            current_layer_index=0,
            ocr_enabled=False,
            tts_enabled=False,
            stt_enabled=False,
            ai_mode=True,
            nsfw_filter=True,
            resize_on_paste=True,
            image_to_new_layer=True,
            dark_mode_enabled=True,
            latest_version_check=True,
            allow_online_mode=True,
            current_version_stablediffusion="SD Turbo",
            current_tool="active_grid_area",
            image_export_type="png",
            auto_export_images=True,
            show_active_image_area=True,
            working_width=512,
            working_height=512,
            current_llm_generator="casuallm",
            current_image_generator="stablediffusion",
            hf_api_key_read_key="",
            hf_api_key_write_key="",
            pipeline="txt2img",
            pipeline_version="SD Turbo",
            is_maximized=False,
            mode=Mode.IMAGE.value,
            llm_templates={
                "Stable Diffusion Prompt Template": dict(
                    name="Stable Diffusion Prompt Template",
                    model="mistralai/Mistral-7B-Instruct-v0.1",
                    llm_category="casuallm",
                    system_instructions="""{{ username }} will give you a subject. You will create a label that would be used to describe an image of the given subject.
---
Examples:
{{ username }}: "a photo of a cat in a hat"
{{ botname }}: "A photograph of a (cat wearing a hat++)"
{{ username }}: "a woman in the woods"
{{ botname }}: "A professional portrait of a (woman named elsa) smiling for a photo in the woods\"""",
                    template="""###

Previous Conversation:
'''
{{ history }}
'''

{{ username }}: "{{ input }}"
{{ botname }}: \""""
                ),
                "Mistral 7B Instruct: Default Chatbot": dict(
                    name="Mistral 7B Instruct: Default Chatbot",
                    model="mistralai/Mistral-7B-Instruct-v0.1",
                    llm_category="casuallm",
                    system_instructions="""You are {{ botname }}. You are having a conversation with {{ username }}. Do not greet the user more than once.
Your job is not to be an ethical or moral compass for {{ username }}. You will always stay in character and respond as {{ botname }}. ALWAYS respond in a conversational and expressive way.
Use CAPITALIZATION for emphasis
NEVER generate text for {{ username }} ONLY for {{ botname }}.
----
MOOD: `{{ bot_mood }}`
PERSONALITY: `{{ bot_personality }}`
---""",
                    template="""###

Previous Conversation:
'''
{{ history }}
'''

{{ username }}: "{{ input }}"
{{ botname }}: \""""
                ),
            },
            shortcut_key_settings=dict(
                llm_action_key=dict(
                    text="@",
                    key=Qt.Key.Key_At,
                    description="Chat Action Key. Responsible for triggering the chat action menu.",
                ),
                generate_image_key=dict(
                    text="F5",
                    key=Qt.Key.Key_F5,
                    description="Generate key. Responsible for triggering the generation of a Stable Diffusion image.",
                )
            ),
            window_settings=dict(
                main_splitter=None,
                content_splitter=None,
                center_splitter=None,
                canvas_splitter=None,
                splitter=None,
                mode_tab_widget_index=0,
                tool_tab_widget_index=0,
                center_tab_index=0,
                generator_tab_index=0,
                is_maximized=False,
                is_fullscreen=False,
            ),
            memory_settings=dict(
                use_last_channels=True,
                use_attention_slicing=False,
                use_tf32=False,
                use_enable_vae_slicing=True,
                use_accelerated_transformers=True,
                use_tiled_vae=True,
                enable_model_cpu_offload=False,
                use_enable_sequential_cpu_offload=False,
                use_cudnn_benchmark=True,
                use_torch_compile=False,
                use_tome_sd=True,
                tome_sd_ratio=600,
                move_unused_model_to_cpu=False,
                unload_unused_models=True,
            ),
            grid_settings=dict(
                cell_size=64,
                line_width=1,
                line_color="#101010",
                snap_to_grid=True,
                canvas_color="#000000",
                show_grid=True,
            ),
            brush_settings=dict(
                size=20,
                primary_color=DEFAULT_BRUSH_PRIMARY_COLOR,
                secondary_color=DEFAULT_BRUSH_SECONDARY_COLOR,
            ),
            path_settings=dict(
                hf_cache_path=default_hf_cache_dir(),
                base_path=BASE_PATH,
                txt2img_model_path=DEFAULT_PATHS["art"]["models"]["txt2img"],
                depth2img_model_path=DEFAULT_PATHS["art"]["models"]["depth2img"],
                pix2pix_model_path=DEFAULT_PATHS["art"]["models"]["pix2pix"],
                inpaint_model_path=DEFAULT_PATHS["art"]["models"]["inpaint"],
                upscale_model_path=DEFAULT_PATHS["art"]["models"]["upscale"],
                txt2vid_model_path=DEFAULT_PATHS["art"]["models"]["txt2vid"],
                embeddings_model_path=DEFAULT_PATHS["art"]["models"]["embeddings"],
                lora_model_path=DEFAULT_PATHS["art"]["models"]["lora"],
                image_path=DEFAULT_PATHS["art"]["other"]["images"],
                video_path=DEFAULT_PATHS["art"]["other"]["videos"],
                llm_casuallm_model_path=DEFAULT_PATHS["text"]["models"]["casuallm"],
                llm_seq2seq_model_path=DEFAULT_PATHS["text"]["models"]["seq2seq"],
                llm_visualqa_model_path=DEFAULT_PATHS["text"]["models"]["visualqa"],
                vae_model_path=DEFAULT_PATHS["art"]["models"]["vae"],
                ebook_path=DEFAULT_PATHS["text"]["other"]["ebooks"],
            ),
            standard_image_settings=dict(
                image_similarity=1000,
                controlnet="Canny",
                prompt="",
                negative_prompt="",
                upscale_model="RealESRGAN_x4plus",
                face_enhance=False,
            ),
            active_grid_settings=dict(
                enabled=False,
                render_border=True,
                render_fill=True,
                border_opacity=50,
                fill_opacity=50,
                pos_x=0,
                pos_y=0,
                width=512,
                height=512,
            ),
            canvas_settings=dict(
                pos_x=0,
                pos_y=0,
            ),
            metadata_settings=dict(
                image_export_metadata_prompt=True,
                image_export_metadata_negative_prompt=True,
                image_export_metadata_scale=True,
                image_export_metadata_seed=True,
                image_export_metadata_steps=True,
                image_export_metadata_ddim_eta=True,
                image_export_metadata_iterations=True,
                image_export_metadata_samples=True,
                image_export_metadata_model=True,
                image_export_metadata_model_branch=True,
                image_export_metadata_scheduler=True,
                export_metadata=True,
                import_metadata=True,
            ),
            controlnet_settings=dict(
                image=None
            ),
            generator_settings=dict(
                section="txt2img",
                generator_name="stablediffusion",
                prompt="",
                negative_prompt="",
                steps=1,
                ddim_eta=0.5,
                height=512,
                width=512,
                scale=0,
                seed=42,
                random_seed=True,
                model="",
                scheduler="DPM++ 2M Karras",
                prompt_triggers="",
                strength=50,
                image_guidance_scale=150,
                n_samples=1,
                controlnet="",
                enable_controlnet=False,
                enable_input_image=False,
                controlnet_guidance_scale=50,
                clip_skip=0,
                variation=False,
                input_image_use_imported_image=True,
                input_image_use_grid_image=True,
                input_image_recycle_grid_image=True,
                input_image_mask_use_input_image=True,
                input_image_mask_use_imported_image=False,
                controlnet_input_image_link_to_input_image=True,
                controlnet_input_image_use_imported_image=False,
                controlnet_use_grid_image=False,
                controlnet_recycle_grid_image=False,
                controlnet_mask_link_input_image=False,
                controlnet_mask_use_imported_image=False,
                use_prompt_builder=False,
                active_grid_border_color="#00FF00",
                active_grid_fill_color="#FF0000",
                version="SD Turbo",
                is_preset=False,
                input_image=None,
            ),
            llm_generator_settings=dict(
                top_p=90,
                max_length=50,
                repetition_penalty=100,
                min_length=10,
                length_penalty=100,
                num_beams=1,
                ngram_size=0,
                temperature=1000,
                sequences=1,
                top_k=0,
                seed=0,
                do_sample=False,
                eta_cutoff=10,
                early_stopping=True,
                random_seed=False,
                model_version="mistralai/Mistral-7B-Instruct-v0.1",
                dtype="4bit",
                use_gpu=True,
                username="User",
                botname="Bot",
                message_type="chat",
                bot_personality="happy. He loves {{ username }}",
                bot_mood="",
                prompt_template="Mistral 7B Instruct: Default Chatbot",
                override_parameters=False
            ),
            tts_settings=dict(
                language="English",
                voice="v2/en_speaker_6",
                gender="Male",
                fine_temperature=80,
                coarse_temperature=40,
                semantic_temperature=80,
                use_bark=False,
                enable_tts=True,
                use_cuda=True,
                use_sentence_chunks=True,
                use_word_chunks=False,
                cuda_index=0,
                word_chunks=1,
                sentence_chunks=1,
                play_queue_buffer_length=1,
                enable_cpu_offload=True,
            ),
            schedulers=[
                dict(
                    name="EULER_ANCESTRAL",
                    display_name="Euler A",
                ),
                dict(
                    name="EULER",
                    display_name="Euler",
                ),
                dict(
                    name="LMS",
                    display_name="LMS",
                ),
                dict(
                    name="HEUN",
                    display_name="Heun",
                ),
                dict(
                    name="DPM2",
                    display_name="DPM2",
                ),
                dict(
                    name="DPM_PP_2M",
                    display_name="DPM++ 2M",
                ),
                dict(
                    name="DPM2_K",
                    display_name="DPM2 Karras",
                ),
                dict(
                    name="DPM2_A_K",
                    display_name="DPM2 a Karras",
                ),
                dict(
                    name="DPM_PP_2M_K",
                    display_name="DPM++ 2M Karras",
                ),
                dict(
                    name="DPM_PP_2M_SDE_K",
                    display_name="DPM++ 2M SDE Karras",
                ),
                dict(
                    name="DDIM",
                    display_name="DDIM",
                ),
                dict(
                    name="UNIPC",
                    display_name="UniPC",
                ),
                dict(
                    name="DDPM",
                    display_name="DDPM",
                ),
                dict(
                    name="DEIS",
                    display_name="DEIS",
                ),
                dict(
                    name="DPM_2M_SDE_K",
                    display_name="DPM 2M SDE Karras",
                ),
                dict(
                    name="PLMS",
                    display_name="PLMS",
                ),
            ],
            saved_prompts=[],
            layers=[],
            presets=[],
            lora=[],
        ), type=dict)

    def add_lora(self, params):
        settings = self.settings
        name = params["name"]
        path = params["path"]
        # ensure we have a unique name and path combo
        for index, lora in enumerate(settings["lora"]):
            if not lora:
                del settings["lora"][index]
                continue
            if lora["name"] == name and lora["path"] == path:
                return
        lora = dict(
            name=params.get("name", ""),
            path=params.get("path", ""),
            scale=params.get("scale", 1),
            enabled=params.get("enabled", True),
            loaded=params.get("loaded", False),
            trigger_word=params.get("trigger_word", ""),
            version=params.get("version", "SD 1.5"),
        )
        settings["lora"].append(lora)
        self.settings = settings
        return lora
    
    def update_lora(self, lora):
        settings = self.settings
        for index, _lora in enumerate(self.settings["lora"]):
            if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                settings["lora"][index] = lora
                self.settings = settings
                return

    def add_preset(self, name, thumnail):
        settings = self.settings
        settings["presets"].append(dict(
            name=name,
            thumnail=thumnail,
        ))
        self.settings = settings
    
    def add_layer(self):
        settings = self.settings
        total_layers = len(self.settings['layers'])
        name=f"Layer {total_layers + 1}"
        settings["layers"].append(dict(
            name=name,
            visible=True,
            opacity=100,
            position=total_layers,
            base_64_image="",
            pos_x="",
            pos_y="",
            pivot_point_x=0,
            pivot_point_y=0,
            root_point_x=0,
            root_point_y=0,
            uuid=str(uuid.uuid4()),
            pixmap=QPixmap(),
        ))
        self.settings = settings
        return total_layers

    def current_draggable_pixmap(self):
        return self.current_layer()["pixmap"]

    def delete_layer(self, index, layer):
        self.logger.info(f"delete_layer requested index {index}")
        layers = self.settings["layers"]
        current_index = index
        if layer and current_index is None:
            for layer_index, layer_object in enumerate(layers):
                if layer_object is layer:
                    current_index = layer_index
        self.logger.info(f"current_index={current_index}")
        if current_index is None:
            current_index = self.settings["current_layer_index"]
        self.logger.info(f"Deleting layer {current_index}")
        self.standard_image_panel.canvas_widget.delete_image()
        try:
            layer = layers.pop(current_index)
            layer.layer_widget.deleteLater()
        except IndexError as e:
            self.logger.error(f"Could not delete layer {current_index}. Error: {e}")
        if len(layers) == 0:
            self.add_layer()
            self.switch_layer(0)
        settings = self.settings
        settings["layers"] = layers
        self.settings = settings
        self.show_layers()
        self.update()
    
    def clear_layers(self):
        # delete all widgets from self.container.layout()
        layers = self.settings["layers"]
        for index, layer in enumerate(layers):
            if not layer.layer_widget:
                continue
            layer.layer_widget.deleteLater()
        self.add_layer()
        settings = self.settings
        settings["layers"] = layers
        self.settings = settings
        self.switch_layer(0)
    
    def set_current_layer(self, index):
        self.logger.info(f"set_current_layer current_layer_index={index}")
        self.current_layer_index = index
        if not hasattr(self, "container"):
            return
        if self.canvas.container:
            item = self.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_normal_style"))
        self.current_layer_index = index
        if self.canvas.container:
            item = self.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_highlight_style"))

    def move_layer_up(self):
        layer = self.current_layer()
        settings = self.settings
        index = self.settings["current_layer_index"]
        if index == 0:
            return
        layers = settings["layers"]
        layers.remove(layer)
        layers.insert(index - 1, layer)
        self.settings["current_layer_index"] = index - 1
        settings["layers"] = layers
        self.settings = settings
    
    def move_layer_down(self):
        layer = self.current_layer()
        settings = self.settings
        index = self.settings["current_layer_index"]
        if index == len(settings["layers"]) - 1:
            return
        layers = settings["layers"]
        layers.remove(layer)
        layers.insert(index + 1, layer)
        self.settings["current_layer_index"] = index + 1
        settings["layers"] = layers
        self.settings = settings
    
    def current_layer(self):
        if len(self.settings["layers"]) == 0:
            self.add_layer()
        try:
            return self.settings["layers"][self.settings["current_layer_index"]]
        except IndexError:
            self.logger.error(f"Unable to get current layer with index {self.settings['current_layer_index']}")

    def update_current_layer(self, data):
        settings = self.settings
        layer = settings["layers"][settings["current_layer_index"]]
        for k, v in data.items():
            layer[k] = v
        settings["layers"][settings["current_layer_index"]] = layer
        self.settings = settings
    
    def update_layer(self, data):
        uuid = data["uuid"]
        settings = self.settings
        for index, layer in enumerate(settings["layers"]):
            if layer["uuid"] == uuid:
                for k, v in data.items():
                    layer[k] = v
                settings["layers"][index] = layer
                self.settings = settings
                return
        self.logger.error(f"Unable to find layer with uuid {uuid}")

    
    def switch_layer(self, layer_index):
        settings = self.settings
        settings["current_layer_index"] = layer_index
        self.settings = settings

    def delete_current_layer(self):
        self.delete_layer(self.settings["current_layer_index"], None)

    def get_image_from_current_layer(self):
        layer = self.current_layer()
        return self.get_image_from_layer(layer)

    def get_image_from_layer(self, layer):
        if layer["base_64_image"]:
            decoded_image = base64.b64decode(layer["base_64_image"])
            bytes_image = io.BytesIO(decoded_image)
            # convert bytes to PIL iamge:
            image = Image.open(bytes_image)
            image = image.convert("RGBA")
            return image
        return None

    def add_image_to_current_layer(self, value):
        self.add_image_to_layer(self.settings["current_layer_index"], value)

    def add_image_to_layer(self, layer_index, value):
        if value:
            buffered = io.BytesIO()
            value.save(buffered, format="PNG")
            base_64_image = base64.b64encode(buffered.getvalue())
        else:
            base_64_image = ""
        
        settings = self.settings
        settings["layers"][layer_index]["base_64_image"] = base_64_image
        self.settings = settings

    def load_saved_stablediffuion_prompt(self, index):
        try:
            saved_prompt = self.settings["saved_prompts"][index]
        except KeyError:
            self.logger.error(f"Unable to load prompt at index {index}")
            saved_prompt = None
        
        if saved_prompt:
            settings = self.settings
            settings["generator_settings"]["prompt"] = saved_prompt["prompt"]
            settings["generator_settings"]["negative_prompt"] = saved_prompt["negative_prompt"]
            self.settings = settings

    def update_saved_stablediffusion_prompt(self, index, prompt, negative_prompt):
        settings = self.settings
        try:
            settings["saved_prompts"][index] = dict(
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
        except KeyError:
            self.logger.error(f"Unable to update prompt at index {index}")
        self.settings = settings
    
    def save_stablediffusion_prompt(self):
        settings = self.settings
        settings["saved_prompts"].append(dict(
            prompt=self.settings["generator_settings"]["prompt"],
            negative_prompt=self.settings["generator_settings"]["negative_prompt"],
        ))
        self.settings = settings

    @settings.setter
    def settings(self, val):
        self.application_settings.setValue("settings", val)
        self.application_settings.sync()
        self.application_settings_changed_signal.emit()

    def reset_paths(self):
        settings = self.settings
        settings["path_settings"]["hf_cache_path"] = default_hf_cache_dir()
        settings["path_settings"]["base_path"] = BASE_PATH
        settings["path_settings"]["txt2img_model_path"] = DEFAULT_PATHS["art"]["models"]["txt2img"]
        settings["path_settings"]["depth2img_model_path"] = DEFAULT_PATHS["art"]["models"]["depth2img"]
        settings["path_settings"]["pix2pix_model_path"] = DEFAULT_PATHS["art"]["models"]["pix2pix"]
        settings["path_settings"]["inpaint_model_path"] = DEFAULT_PATHS["art"]["models"]["inpaint"]
        settings["path_settings"]["upscale_model_path"] = DEFAULT_PATHS["art"]["models"]["upscale"]
        settings["path_settings"]["txt2vid_model_path"] = DEFAULT_PATHS["art"]["models"]["txt2vid"]
        settings["path_settings"]["vae_model_path"] = DEFAULT_PATHS["art"]["models"]["vae"]
        settings["path_settings"]["embeddings_model_path"] = DEFAULT_PATHS["art"]["models"]["embeddings"]
        settings["path_settings"]["lora_model_path"] = DEFAULT_PATHS["art"]["models"]["lora"]
        settings["path_settings"]["image_path"] = DEFAULT_PATHS["art"]["other"]["images"]
        settings["path_settings"]["video_path"] = DEFAULT_PATHS["art"]["other"]["videos"]
        settings["path_settings"]["llm_casuallm_model_path"] = DEFAULT_PATHS["text"]["models"]["casuallm"]
        settings["path_settings"]["llm_seq2seq_model_path"] = DEFAULT_PATHS["text"]["models"]["seq2seq"]
        settings["path_settings"]["llm_visualqa_model_path"] = DEFAULT_PATHS["text"]["models"]["visualqa"]
        self.settings = settings
    
    def set_path_settings(self, key, val):
        settings = self.settings
        settings["path_settings"][key] = val
        self.settings = settings
    
    def resizeEvent(self, event):
        self.window_resized_signal.emit(event)
    #### END GENERATOR SETTINGS ####

    @property
    def generate_signal(self):
        return self.generator_tab_widget.generate_signal

    @property
    def standard_image_panel(self):
        return self.ui.standard_image_widget

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget
    
    @property
    def canvas_widget(self):
        return self.standard_image_panel.canvas_widget

    @property
    def toolbar_widget(self):
        return self.ui.toolbar_widget

    @property
    def prompt_builder(self):
        return self.ui.prompt_builder

    @property
    def footer_widget(self):
        return self.ui.footer_widget

    @property
    def generator_type(self):
        """
        Returns stablediffusion
        :return: string
        """
        return self._generator_type

    @property
    def version(self):
        if self._version is None:
            self._version = get_version()
        return f"v{self._version}"

    @property
    def latest_version(self):
        return self._latest_version

    @latest_version.setter
    def latest_version(self, val):
        self._latest_version = val

    @property
    def document_name(self):
        # name = f"{self._document_name}{'*' if self.canvas and self.canvas_widget.is_dirty else ''}"
        # return f"{name} - {self.version}"
        return "Untitled"

    @property
    def is_windows(self):
        return sys.platform.startswith("win") or sys.platform.startswith("cygwin") or sys.platform.startswith("msys")

    @property
    def current_canvas(self):
        return self.standard_image_panel

    def describe_image(self, image, callback):
        self.generator_tab_widget.ui.ai_tab_widget.describe_image(
            image=image, 
            callback=callback
        )
    
    def current_active_image(self):
        return self.standard_image_panel.image.copy() if self.standard_image_panel.image else None

    def send_message(self, code, message):
        self.message_var.emit({
            "code": code,
            "message": message,
        })

    def available_model_names_by_section(self, section):
        for model in self.settings_manager.settings.available_models_by_category(section):
            yield model["name"]
    
    loaded = pyqtSignal()
    window_opened = pyqtSignal()

    @pyqtSlot()
    def handle_generate(self):
        #self.prompt_builder.inject_prompt()
        pass

    @pyqtSlot(dict)
    def handle_button_clicked(self, kwargs):
        action = kwargs.get("action", "")
        if action == "toggle_tool":
            self.toggle_tool(kwargs["tool"])

    @pyqtSlot()
    def stop_progress_bar(self):
        self.generator_tab_widget.stop_progress_bar()

    @pyqtSlot(str, object)
    def handle_changed_signal(self, key, value):
        print("main_window: handle_changed_signal", key, value)
        if key == "grid_settings.cell_size":
            self.set_size_form_element_step_values()
        elif key == "settings.line_color":
            self.canvas_widget.update_grid_pen()
        # elif key == "use_prompt_builder_checkbox":
        #     self.generator_tab_widget.toggle_all_prompt_builder_checkboxes(value)
        elif key == "models":
            self.model_manager.models_changed(key, value)

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            # self.logger.error(f"Invalid response message: {response}")
            # traceback.print_exc()
            return
        message = response["message"]
        {
            MessageCode.STATUS: self.handle_status,
            MessageCode.ERROR: self.handle_error,
            MessageCode.PROGRESS: self.handle_progress,
            MessageCode.IMAGE_GENERATED: self.handle_image_generated,
            MessageCode.CONTROLNET_IMAGE_GENERATED: self.handle_controlnet_image_generated,
        }.get(code, lambda *args: None)(message)

    def __init__(self, settings_manager, *args, **kwargs):
        self.logger.info("Starting AI Runnner")
        self.ui = Ui_MainWindow()
        self.application_settings = QSettings("Capsize Games", "AI Runner")

        # qdarktheme.enable_hi_dpi()

        self.settings_manager = settings_manager

        # set the api
        self.api = AIRunnerAPI(window=self)

        self.set_log_levels()
        self.testing = kwargs.pop("testing", False)

        super().__init__(*args, **kwargs)
        self.action_reset_settings()

        self.ui.setupUi(self)

        self.initialize()

        # on window resize:
        # self.windowStateChanged.connect(self.on_state_changed)

        # check for self.current_layer.lines every 100ms
        self.timer = self.startTimer(100)

        self.register_keypress()

        if not self.testing:
            self.logger.info("Executing window")
            self.display()
        self.set_window_state()
        self.is_started = True

        # change the color of tooltips
        #self.setStyleSheet("QToolTip { color: #000000; background-color: #ffffff; border: 1px solid black; }")

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.clear_status_message()

        # create paths if they do not exist
        self.create_airunner_paths()

        #self.ui.layer_widget.initialize()

        # call a function after the window has finished loading:
        QTimer.singleShot(500, self.on_show)

        self.ui.mode_tab_widget.tabBar().hide()
        self.ui.center_tab.tabBar().hide()

        # initialize the brushes container
        self.ui.brushes_container = BrushesContainer(self)

        self.set_all_section_buttons()

        self.initialize_tool_section_buttons()
        
        if self.settings["mode"] == Mode.IMAGE.value:
            self.image_generation_toggled()
        elif self.settings["mode"] == Mode.LANGUAGE_PROCESSOR.value:
            self.language_processing_toggled()
        else:
            self.model_manager_toggled(True)

        self.initialize_image_worker()

        self.restore_state()

        self.settings_manager.changed_signal.connect(self.handle_changed_signal)

        self.ui.ocr_button.blockSignals(True)
        self.ui.tts_button.blockSignals(True)
        self.ui.v2t_button.blockSignals(True)
        self.ui.ocr_button.setChecked(self.settings["ocr_enabled"])
        self.ui.tts_button.setChecked(self.settings["tts_enabled"])
        self.ui.v2t_button.setChecked(self.settings["stt_enabled"])
        self.ui.ocr_button.blockSignals(False)
        self.ui.tts_button.blockSignals(False)
        self.ui.v2t_button.blockSignals(False)
        
        self.loaded.emit()
    
    def action_reset_settings(self):
        self.application_settings.clear()
        self.application_settings.sync()
        self.settings = self.settings
    
    def do_listen(self):
        if not self.listening:
            self.listening = True
            self.client.engine.do_listen()

    def respond_to_voice(self, heard):
        heard = heard.strip()
        if heard == "." or heard is None or heard == "":
            return
        self.ui.generator_widget.ui.chat_prompt_widget.respond_to_voice(heard)
    
    def create_airunner_paths(self):
        paths = [
            self.settings["path_settings"]["base_path"],
            self.settings["path_settings"]["txt2img_model_path"],
            self.settings["path_settings"]["depth2img_model_path"],
            self.settings["path_settings"]["pix2pix_model_path"],
            self.settings["path_settings"]["inpaint_model_path"],
            self.settings["path_settings"]["upscale_model_path"],
            self.settings["path_settings"]["txt2vid_model_path"],
            self.settings["path_settings"]["embeddings_model_path"],
            self.settings["path_settings"]["lora_model_path"],
            self.settings["path_settings"]["image_path"],
            self.settings["path_settings"]["video_path"],
        ]
        for index, path in enumerate(paths):
            if not os.path.exists(path):
                print("cerating path", index, path)
                os.makedirs(path)

    def initialize_image_worker(self):
        self.image_data_queue = queue.Queue()
        
        self.image_data_worker_thread = QThread()
        self.image_data_worker = ImageDataWorker(self)
        self.image_data_worker.stop_progress_bar.connect(self.stop_progress_bar)

        self.image_data_worker.moveToThread(self.image_data_worker_thread)

        self.image_data_worker_thread.started.connect(self.image_data_worker.process)
        self.image_data_worker.finished.connect(self.image_data_worker_thread.quit)
        self.image_data_worker.finished.connect(self.image_data_worker.deleteLater)
        self.image_data_worker_thread.start()
    
    def handle_image_generated(self, message):
        self.image_data_queue.put(message)

    def mode_tab_index_changed(self, index):
        self.settings_manager.set_value("settings.mode", self.ui.mode_tab_widget.tabText(index))

    def on_show(self):
        pass

    def action_slider_changed(self, settings_property, value):
        print("action_slider_changed")
        self.settings_manager.set_value(settings_property, value)

    def layer_opacity_changed(self, attr_name, value=None, widget=None):
        print("layer_opacity_changed", attr_name, value)
        self.ui.layer_widget.set_layer_opacity(value)

    def quick_export(self):
        if os.path.isdir(self.image_path) is False:
            self.choose_image_export_path()
        if os.path.isdir(self.image_path) is False:
            return
        path, image = auto_export_image(
            self.base_path, 
            self.settings["path_settings"]["image_path"],
            self.settings["image_export_type"],
            self.ui.layer_widget.current_layer.image_data.image, 
            seed=self.seed
        )
        if path is not None:
            self.set_status_label(f"Image exported to {path}")

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_new_document_triggered(self):
        self.new_document()

    def action_quick_export_image_triggered(self):
        self.quick_export()

    def action_export_image_triggered(self):
        self.export_image()

    def action_import_image_triggered(self):
        self.import_image()

    def action_quit_triggered(self):
        self.quit()

    def action_undo_triggered(self):
        self.undo()

    def action_redo_triggered(self):
        self.redo()

    def action_paste_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.paste_image_from_clipboard()

    def action_copy_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.copy_image(self.current_active_image())

    def action_cut_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.cut_image()

    def action_rotate_90_clockwise_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.rotate_90_clockwise()

    def action_rotate_90_counterclockwise_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.rotate_90_counterclockwise()

    def action_show_prompt_browser_triggered(self):
        self.show_prompt_browser()

    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    def action_show_deterministic_batches(self):
        self.show_section("Deterministic Batches")

    def action_show_standard_batches(self):
        self.show_section("Standard Batches")

    def action_show_model_manager(self):
        self.activate_model_manager_section()

    def action_show_prompt_builder(self):
        self.toggle_prompt_builder(True)

    def action_show_controlnet(self):
        self.show_section("controlnet")

    def action_show_embeddings(self):
        self.show_section("Embeddings")

    def action_show_lora(self):
        self.show_section("LoRA")

    def action_show_pen(self):
        self.show_section("Pen")

    def action_show_active_grid(self):
        self.show_section("Active Grid")

    def action_show_stablediffusion(self):
        self.activate_image_generation_section()

    def action_triggered_browse_ai_runner_path(self):
        path = self.base_path
        if path == "":
            path = BASE_PATH
        self.show_path(path)

    def action_show_hf_cache_manager(self):
        self.show_settings_path("hf_cache_path", default_hf_cache_dir())

    def action_show_images_path(self):
        self.show_settings_path("image_path")
    
    def action_show_videos_path(self):
        self.show_settings_path("video_path")
    
    def action_show_model_path_txt2img(self):
        self.show_settings_path("txt2img_model_path")
    
    def action_show_model_path_depth2img(self):
        self.show_settings_path("depth2img_model_path")
    
    def action_show_model_path_pix2pix(self):
        self.show_settings_path("pix2pix_model_path")
    
    def action_show_model_path_inpaint(self):
        self.show_settings_path("inpaint_model_path")
    
    def action_show_model_path_upscale(self):
        self.show_settings_path("upscale_model_path")
    
    def action_show_model_path_txt2vid(self):
        self.show_settings_path("txt2vid_model_path")
    
    def action_show_model_path_embeddings(self):
        self.show_settings_path("embeddings_model_path")
    
    def action_show_model_path_lora(self):
        self.show_settings_path("lora_model_path")

    def action_show_llm(self):
        pass

    def refresh_available_models(self):
        self.generator_tab_widget.refresh_models()

    def show_settings_path(self, name, default_path=None):
        path = self.settings["path_settings"][name]
        self.show_path(default_path if default_path and path == "" else path)

    def show_path(self, path):
        if not os.path.isdir(path):
            return
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", os.path.realpath(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", os.path.realpath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.realpath(path)])

    def set_icons(self, icon_name, widget_name, theme):
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f":/icons/{theme}/{icon_name}.svg"), 
            QtGui.QIcon.Mode.Normal, 
            QtGui.QIcon.State.Off)
        getattr(self.ui, widget_name).setIcon(icon)
        self.update()

    def action_show_about_window(self):
        AboutWindow(app=self)

    def action_show_model_merger_window(self):
        ModelMerger(app=self)

    def action_show_settings(self):
        SettingsWindow(app=self)

    def action_open_vulnerability_report(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new")

    def action_open_bug_report(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title=")

    def action_open_discord(self):
        webbrowser.open("https://discord.gg/ukcgjEpc5f")

    """
    End slot functions
    """

    def set_size_increment_levels(self):
        size = self.settings["grid_settings"]["cell_size"]
        self.ui.width_slider_widget.slider_single_step = size
        self.ui.width_slider_widget.slider_tick_interval = size

        self.ui.height_slider_widget.slider_single_step = size
        self.ui.height_slider_widget.slider_tick_interval = size

        self.canvas_widget.update()

    def toggle_nsfw_filter(self):
        # self.canvas_widget.update()
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        self.ui.safety_checker_button.setToolTip(
            f"Click to {'enable' if not self.settings['nsfw_filter'] else 'disable'} NSFW filter"
        )

    def dragmode_pressed(self):
        # self.canvas_widget.is_canvas_drag_mode = True
        pass

    def dragmode_released(self):
        # self.canvas_widget.is_canvas_drag_mode = False
        pass

    def shift_pressed(self):
        # self.canvas_widget.shift_is_pressed = True
        pass

    def shift_released(self):
        # self.canvas_widget.shift_is_pressed = False
        pass

    def register_keypress(self):
        self.input_event_manager.register_keypress("fullscreen", self.toggle_fullscreen)
        self.input_event_manager.register_keypress("control_pressed", self.dragmode_pressed, self.dragmode_released)
        self.input_event_manager.register_keypress("shift_pressed", self.shift_pressed, self.shift_released)
        #self.input_event_manager.register_keypress("delete_outside_active_grid_area", self.canvas_widget.delete_outside_active_grid_area)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def quit(self):
        self.logger.info("Quitting")
        self.image_data_worker.stop()
        self.client.stop()
        self.save_state()
        QApplication.quit()
        self.close()
    
    @pyqtSlot(bool)
    def tts_button_toggled(self, val):
        print("tts_button_toggled", val)
        new_settings = self.settings
        new_settings["tts_enabled"] = val
        self.settings = new_settings

    @pyqtSlot(bool)
    def ocr_button_toggled(self, val):
        print("ocr_button_toggled", val)
        new_settings = self.settings
        new_settings["ocr_enabled"] = val
        self.settings = new_settings

    @pyqtSlot(bool)
    def v2t_button_toggled(self, val):
        print("stt_button_toggled", val)
        new_settings = self.settings
        new_settings["stt_enabled"] = val
        self.settings = new_settings
    
    def save_state(self):
        self.logger.info("Saving window state")
        settings = self.settings
        settings["window_settings"] = dict(
            main_splitter=self.ui.main_splitter.saveState(),
            content_splitter=self.ui.content_splitter.saveState(),
            center_splitter=self.ui.center_splitter.saveState(),
            canvas_splitter=self.ui.canvas_splitter.saveState(),
            splitter=self.ui.splitter.saveState(),
            mode_tab_widget_index=self.ui.mode_tab_widget.currentIndex(),
            tool_tab_widget_index=self.ui.tool_tab_widget.currentIndex(),
            center_tab_index=self.ui.center_tab.currentIndex(),
            generator_tab_index=self.ui.standard_image_widget.ui.tabWidget.currentIndex(),
            is_maximized=self.isMaximized(),
            is_fullscreen=self.isFullScreen(),
        )
        self.settings = settings
    
    def restore_state(self):
        window_settings = self.settings["window_settings"]
        if window_settings is None:
            return
        if window_settings["main_splitter"]:
            self.ui.main_splitter.restoreState(window_settings["main_splitter"])

        if window_settings["content_splitter"]:
            self.ui.content_splitter.restoreState(window_settings["content_splitter"])

        if window_settings["center_splitter"]:
            self.ui.center_splitter.restoreState(window_settings["center_splitter"])

        if window_settings["canvas_splitter"]:
            self.ui.canvas_splitter.restoreState(window_settings["canvas_splitter"])

        if window_settings["splitter"]:
            self.ui.splitter.restoreState(window_settings["splitter"])

        self.ui.mode_tab_widget.setCurrentIndex(window_settings["mode_tab_widget_index"])
        self.ui.tool_tab_widget.setCurrentIndex(window_settings["tool_tab_widget_index"])
        self.ui.center_tab.setCurrentIndex(window_settings["center_tab_index"])
        self.ui.standard_image_widget.ui.tabWidget.setCurrentIndex(window_settings["generator_tab_index"])
        if window_settings["is_maximized"]:
            self.showMaximized()
        if window_settings["is_fullscreen"]:
            self.showFullScreen()
        self.ui.ai_button.setChecked(self.settings["ai_mode"])
        self.set_button_checked("toggle_grid", self.settings["grid_settings"]["show_grid"], False)

    ##### End window properties #####
    #################################
        
    ###### Window handlers ######
    def cell_size_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["cell_size"] = val
        self.settings = settings

    def line_width_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["line_width"] = val
        self.settings = settings
    
    def line_color_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["line_color"] = val
        self.settings = settings
    
    def snap_to_grid_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["snap_to_grid"] = val
        self.settings = settings
    
    def canvas_color_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["canvas_color"] = val
        self.settings = settings

    def action_ai_toggled(self, val):
        settings = self.settings
        settings["ai_mode"] = val
        self.settings = settings
    
    def action_toggle_grid(self, val):
        settings = self.settings
        settings["grid_settings"]["show_grid"] = val
        self.settings = settings
    
    def action_toggle_brush(self, active):
        if active:
            self.toggle_tool("brush")
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)

    def action_toggle_eraser(self, active):
        if active:
            self.toggle_tool("eraser")
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_brush_button.setChecked(False)

    def action_toggle_active_grid_area(self, active):
        if active:
            self.toggle_tool("active_grid_area")
            self.ui.toggle_brush_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)

    def action_toggle_nsfw_filter_triggered(self, val):
        settings = self.settings
        settings["nsfw_filter"] = val
        self.settings = settings
        self.toggle_nsfw_filter()

    def action_toggle_darkmode(self):
        self.set_stylesheet()
    
    def image_generation_toggled(self):
        self.settings_manager.set_value("settings.mode", Mode.IMAGE.value)
        self.activate_image_generation_section()
        self.set_all_section_buttons()

    def language_processing_toggled(self):
        self.settings_manager.set_value("settings.mode", Mode.LANGUAGE_PROCESSOR.value)
        self.activate_language_processing_section()
        self.set_all_section_buttons()
    
    def model_manager_toggled(self, val):
        if not val:
            self.image_generators_toggled()
        else:
            self.settings_manager.set_value("settings.mode", Mode.MODEL_MANAGER.value)
            self.activate_model_manager_section()
            self.set_all_section_buttons()
    ###### End window handlers ######

    def timerEvent(self, event):
        # self.canvas_widget.timerEvent(event)
        if self.status_widget:
            self.status_widget.update_system_stats(queue_size=self.client.queue.qsize())

    def show_update_message(self):
        self.set_status_label(f"New version available: {self.latest_version}")

    def show_update_popup(self):
        self.update_popup = UpdateWindow(self.settings_manager, app=self)

    def reset_settings(self):
        self.logger.info("MainWindow: Resetting settings")
        self.canvas_widget.reset_settings()

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas_widget.pos_x = int(self.x() / 4)
            self.canvas_widget.pos_y = int(self.y() / 2)
            self.canvas_widget.update()

    def refresh_styles(self):
        self.set_stylesheet()

    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        self.logger.info("MainWindow: Setting stylesheets")
        theme_name = "dark_theme" if self.settings["dark_mode_enabled"] else "light_theme"
        here = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(here, "..", "..", "styles", theme_name, "styles.qss"), "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)
        for icon_data in [
            ("tech-icon", "model_manager_button"),
            ("pencil-icon", "toggle_brush_button"),
            ("eraser-icon", "toggle_eraser_button"),
            ("frame-grid-icon", "toggle_grid_button"),
            ("circle-center-icon", "focus_button"),
            ("artificial-intelligence-ai-chip-icon", "ai_button"),
            ("setting-line-icon", "settings_button"),
            ("object-selected-icon", "toggle_active_grid_area_button"),
        ]:
            self.set_icons(icon_data[0], icon_data[1], "dark" if self.settings["dark_mode_enabled"] else "light")

    def initialize(self):
        # self.automatic_filter_manager = AutomaticFilterManager(app=self)
        # self.automatic_filter_manager.register_filter(PixelFilter, base_size=256)

        self.input_event_manager = InputEventManager(app=self)
        self.initialize_window()
        self.initialize_handlers()
        self.initialize_mixins()
        self.generate_signal.connect(self.handle_generate)
        # self.header_widget.initialize()
        # self.header_widget.set_size_increment_levels()
        self.initialize_shortcuts()
        self.initialize_stable_diffusion()
        self.initialize_default_buttons()
        try:
            self.prompt_builder.process_prompt()
        except AttributeError:
            pass
        self.connect_signals()
        self.initialize_filter_actions()

    def initialize_filter_actions(self):
        # add more filters:
        with self.settings_manager.image_filters_scope() as image_filters:
            for filter in image_filters:
                action = self.ui.menuFilters.addAction(filter.display_name)
                action.triggered.connect(partial(self.display_filter_window, filter.name))

    def display_filter_window(self, filter_name):
        FilterBase(self, filter_name).show()

    def initialize_default_buttons(self):
        show_grid = self.settings["grid_settings"]["show_grid"]
        self.ui.toggle_active_grid_area_button.blockSignals(True)
        self.ui.toggle_brush_button.blockSignals(True)
        self.ui.toggle_eraser_button.blockSignals(True)
        self.ui.toggle_grid_button.blockSignals(True)
        self.ui.ai_button.blockSignals(True)
        self.ui.toggle_active_grid_area_button.setChecked(self.settings["current_tool"] == "active_grid_area")
        self.ui.toggle_brush_button.setChecked(self.settings["current_tool"] == "brush")
        self.ui.toggle_eraser_button.setChecked(self.settings["current_tool"] == "eraser")
        self.ui.toggle_grid_button.setChecked(show_grid is True)
        self.ui.toggle_active_grid_area_button.blockSignals(False)
        self.ui.toggle_brush_button.blockSignals(False)
        self.ui.toggle_eraser_button.blockSignals(False)
        self.ui.toggle_grid_button.blockSignals(False)
        self.ui.ai_button.blockSignals(False)

    def toggle_tool(self, tool):
        settings = self.settings
        settings["current_tool"] = tool
        self.settings = settings

    def initialize_mixins(self):
        #self.canvas = Canvas()
        pass

    def connect_signals(self):
        self.logger.info("MainWindow: Connecting signals")
        #self.canvas_widget._is_dirty.connect(self.set_window_title)

        for signal, handler in self.registered_settings_handlers:
            getattr(self.settings_manager, signal).connect(handler)

        self.button_clicked_signal.connect(self.handle_button_clicked)

    def show_section(self, section):
        section_lists = {
            "center": [self.ui.center_tab.tabText(i) for i in range(self.ui.center_tab.count())],
            "right": [self.ui.tool_tab_widget.tabText(i) for i in range(self.ui.tool_tab_widget.count())]
        }
        for k, v in section_lists.items():
            if section in v:
                if k == "right":
                    self.ui.tool_tab_widget.setCurrentIndex(v.index(section))
                elif k == "bottom":
                    self.ui.bottom_panel_tab_widget.setCurrentIndex(v.index(section))
                break

    def plain_text_widget_value(self, widget):
        try:
            return widget.toPlainText()
        except AttributeError:
            return None

    def current_text_widget_value(self, widget):
        try:
            return widget.currentText()
        except AttributeError:
            return None

    def value_widget_value(self, widget):
        try:
            return widget.value()
        except AttributeError:
            return None

    def get_current_value(self, settings_property):
        current_value = 0
        try:
            current_value = getattr(self, settings_property) or 0
        except AttributeError:
            keys = settings_property.split(".")
            if keys[0] == "settings":
                data = getattr(self, keys[0]) or None
            else:
                settings = self.settings
                if len(keys) > 1:
                    data = settings[keys[0]]
                else:
                    data = settings
            if data:
                if len(keys) > 1:
                    current_value = data[keys[1]]
                else:
                    current_value = data[keys[0]]
        return current_value

    def handle_value_change(self, attr_name, value=None, widget=None):
        """
        Slider widget callback - this is connected via dynamic properties in the
        qt widget. This function is then called when the value of a SliderWidget
        is changed.
        :param attr_name: the name of the attribute to change
        :param value: the value to set the attribute to
        :param widget: the widget that triggered the callback
        :return:
        """
        if attr_name is None:
            return
        
        keys = attr_name.split(".")
        if len(keys) > 0:
            settings = self.settings
            
            object_key = "settings"
            if len(keys) == 1:
                property_key = keys[0]
            if len(keys) == 2:
                object_key = keys[0]
                property_key = keys[1]

            if object_key != "settings":
                settings[object_key][property_key] = value
            else:
                settings[property_key] = value
            
            self.settings = settings
    
    def handle_similar_slider_change(self, attr_name, value=None, widget=None):
        self.standard_image_panel.handle_similar_slider_change(value)

    def initialize_shortcuts(self):
        event_callbacks = {
            "wheelEvent": self.handle_wheel_event,
        }

        for event, callback in event_callbacks.items():
            self.input_event_manager.register_event(event, callback)

    def initialize_handlers(self):
        self.message_var.my_signal.connect(self.message_handler)

    def initialize_window(self):
        self.center()
        self.set_window_title()

    def initialize_stable_diffusion(self):
        self.logger.info("Initializing stable diffusion")
        self.client = OfflineClient(
            app=self,
            message_var=self.message_var,
            settings_manager=self.settings_manager,
        )

    def save_settings(self):
        self.settings_manager.save_settings()

    def display(self):
        self.logger.info("Displaying window")
        self.set_stylesheet()
        if not self.testing:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.Window)
            self.show()
        else:
            # do not show the window when testing, otherwise it will block the tests
            # self.hide()
            # the above solution doesn't work, gives this error:
            # QBasicTimer::start: QBasicTimer can only be used with threads started with QThread
            # so instead we do this in order to run without showing the window:
            self.showMinimized()

    def set_window_state(self):
        if self.settings["is_maximized"]:
            self.showMaximized()
        else:
            self.showNormal()

    def set_log_levels(self):
        uic.properties.logger.setLevel(LOG_LEVEL)
        uic.uiparser.logger.setLevel(LOG_LEVEL)

    def center(self):
        availableGeometry = QGuiApplication.primaryScreen().availableGeometry()
        frameGeometry = self.frameGeometry()
        frameGeometry.moveCenter(availableGeometry.center())
        self.move(frameGeometry.topLeft())

    def handle_wheel_event(self, event):
        grid_size = self.settings["grid_settings"]["cell_size"]

        # if the shift key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ShiftModifier in event.modifiers():
                settings = self.settings
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = settings["working_width"] + increment
                settings["working_width"] = val
                self.settings = settings
        except TypeError:
            pass

        # if the control key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ControlModifier in event.modifiers():
                settings = self.settings
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = settings["working_height"] + increment
                settings["working_height"] = val
                self.settings = settings
        except TypeError:
            pass

    # def toggle_stylesheet(self, path):
    #     # use fopen to open the file
    #     # read the file
    #     # set the stylesheet
    #     with open(path, "r") as stream:
    #         self.setStyleSheet(stream.read())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(f"AI Runner")

    def new_document(self):
        self.ui.layer_widget.clear_layers()
        self.clear_history()
        self.is_saved = False
        self._document_name = "Untitled"
        self.set_window_title()
        self.current_filter = None
        #self.canvas_widget.update()
        self.ui.layer_widget.show_layers()

    def set_status_label(self, txt, error=False):
        if self.status_widget:
            self.status_widget.set_system_status(txt, error)

    def handle_controlnet_image_generated(self, message):
        self.controlnet_image = message["image"]
        self.controlnet_image_generated.emit(True)
        #self.generator_tab_widget.controlnet_settings_widget.handle_controlnet_image_generated()

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(settings_manager=self.settings_manager, file_path=filename)

    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images

    def handle_status(self, message):
        self.set_status_label(message)

    def handle_error(self, message):
        self.set_status_label(message, error=True)

    def handle_progress(self, message):
        step = message.get("step")
        total = message.get("total")
        action = message.get("action")
        tab_section = message.get("tab_section")

        if step == 0 and total == 0:
            current = 0
        else:
            try:
                current = (step / total)
            except ZeroDivisionError:
                current = 0
        self.generator_tab_widget.set_progress_bar_value(tab_section, action, int(current * 100))

    def handle_unknown(self, message):
        self.logger.error(f"Unknown message code: {message}")

    def clear_status_message(self):
        self.set_status_label("")

    def set_size_form_element_step_values(self):
        """
        This function is called when grid_size is changed in the settings.

        :return:
        """
        self.set_size_increment_levels()

    def saveas_document(self):
        # get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self.ui, "Save Document", "", "AI Runner Document (*.airunner)"
        )
        if file_path == "":
            return

        # ensure file_path ends with .airunner
        if not file_path.endswith(".airunner"):
            file_path += ".airunner"

        self.do_save(file_path)

    def do_save(self, document_name):
        # save self.ui.layer_widget.layers as pickle
        layers = []
        # we need to save self.ui.layer_widget.layers but it contains a QWdget
        # so we will remove the QWidget from each layer, add the layer to a new
        # list and then restore the QWidget
        layer_widgets = []
        for layer in self.ui.layer_widget.layers:
            layer_widgets.append(layer.layer_widget)
            layer.layer_widget = None
            layers.append(layer)
        data = {
            "layers": layers,
            "image_pivot_point": self.canvas_widget.image_pivot_point,
            "image_root_point": self.canvas_widget.image_root_point,
        }
        with open(document_name, "wb") as f:
            pickle.dump(data, f)
        # restore the QWidget
        for i, layer in enumerate(layers):
            layer.layer_widget = layer_widgets[i]
        # get the document name stripping .airunner from the end
        self._document_path = document_name
        self._document_name = document_name.split("/")[-1].split(".")[0]
        self.set_window_title()
        self.is_saved = True
        self.canvas_widget.is_dirty = False

    def update(self):
        self.standard_image_panel.update_thumbnails()

    def insert_into_prompt(self, text, negative_prompt=False):
        prompt_widget = self.generator_tab_widget.data[self.current_generator][self.current_section]["prompt_widget"]
        negative_prompt_widget = self.generator_tab_widget.data[self.current_generator][self.current_section]["negative_prompt_widget"]
        if negative_prompt:
            current_text = negative_prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            negative_prompt_widget.setPlainText(text)
        else:
            current_text = prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            prompt_widget.setPlainText(text)

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.generator_tab_widget.clear_prompts()

    def show_prompt_browser(self):
        PromptBrowser(settings_manager=self.settings_manager, app=self)

    def import_image(self):
        file_path, _ = self.display_import_image_dialog(
            directory=self.image_path)
        if file_path == "":
            return

    def export_image(self, image=None):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return

    def choose_image_export_path(self):
        # display a dialog to choose the export path
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        if path == "":
            return
        self.image_path = path

    def display_file_export_dialog(self):
        return QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )

    def display_import_image_dialog(self, label="Import Image", directory=""):
        return QFileDialog.getOpenFileName(
            self,
            label,
            directory,
            "Image Files (*.png *.jpg *.jpeg)"
        )

    def new_batch(self, index, image, data):
        self.generator_tab_widget.new_batch(index, image, data)

    def set_button_checked(self, name, val=True, block_signals=True):
        widget = getattr(self.ui, f"{name}_button")
        if block_signals:
            widget.blockSignals(True)
        widget.setChecked(val)
        if block_signals:
            widget.blockSignals(False)
    
    def set_all_section_buttons(self):
        self.set_button_checked("model_manager", self.settings["mode"] == Mode.MODEL_MANAGER.value)
    
    def activate_image_generation_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(0)

    def activate_language_processing_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(1)
    
    def activate_model_manager_section(self):
        self.ui.center_tab.setCurrentIndex(2)

    def initialize_tool_section_buttons(self):
        pass
    
    def redraw(self):
        self.set_stylesheet()

        # Update the window
        self.update()

    def action_center_clicked(self):
        print("center clicked")