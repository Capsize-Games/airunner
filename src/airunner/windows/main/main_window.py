import os
import queue
import pickle
import platform
import subprocess
import sys
import webbrowser
from functools import partial

from PyQt6 import uic, QtCore
from PyQt6.QtCore import pyqtSlot, Qt, pyqtSignal, QTimer, QObject, QThread
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow
from PyQt6 import QtGui
from PyQt6.QtCore import QSettings

from airunner.resources_light_rc import *
from airunner.resources_dark_rc import *
from airunner.aihandler.enums import MessageCode, Mode
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.pyqt_client import OfflineClient
from airunner.aihandler.qtvar import MessageHandlerVar
from airunner.aihandler.settings import LOG_LEVEL
from airunner.airunner_api import AIRunnerAPI
from airunner.data.models import DEFAULT_PATHS, Prompt, LLMGenerator
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
from airunner.data.models import Document
from airunner.data.session_scope import session_scope


class ImageDataWorker(QObject):
    finished = pyqtSignal()
    stop_progress_bar = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    @pyqtSlot()
    def process(self):
        while True:
            item = self.parent.image_data_queue.get()
            self.process_image_data(item)
        self.finished.emit()
    
    def process_image_data(self, message):
        print("process_image_data 1")
        images = message["images"]
        data = message["data"]
        nsfw_content_detected = message["nsfw_content_detected"]
        self.parent.clear_status_message()
        self.parent.data = data
        print("process_image_data 3")
        if data["action"] == "txt2vid":
            return self.parent.video_handler(data)
        self.stop_progress_bar.emit()
        print("process_image_data 4")
        path = ""
        if self.parent.auto_export_images:
            procesed_images = []
            for image in images:
                path, image = auto_export_image(
                    base_path=self.base_path,
                    image_path=self.app.image_path,
                    image_export_type=self.app.image_export_type,
                    image=image, 
                    data=data, 
                    seed=data["options"]["seed"], 
                    latents_seed=data["options"]["latents_seed"]
                )
                if path is not None:
                    self.parent.set_status_label(f"Image exported to {path}")
                procesed_images.append(image)
            images = procesed_images
        if nsfw_content_detected and self.nsfw_filter:
            self.parent.message_handler({
                "message": "Explicit content detected, try again.",
                "code": MessageCode.ERROR
            })

        images = self.parent.post_process_images(images)
        self.parent.image_data.emit({
            "images": images,
            "path": path,
            "data": data
        })
        self.parent.message_handler("")
        self.parent.ui.layer_widget.show_layers()
        self.parent.image_generated.emit(True)



class MainWindow(
    QMainWindow
):
    # signals
    ai_mode_toggled = pyqtSignal(bool)
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

    generator = None
    _generator = None
    _generator_settings = None

    @property
    def use_last_channels(self):
        return self.application_settings.value("use_last_channels", True, type=bool)
    
    @use_last_channels.setter
    def use_last_channels(self, val):
        self.application_settings.setValue("use_last_channels", val)

    @property
    def use_attention_slicing(self):
        return self.application_settings.value("use_attention_slicing", False, type=bool)
    
    @use_attention_slicing.setter
    def use_attention_slicing(self, val):
        self.application_settings.setValue("use_attention_slicing", val)

    @property
    def use_tf32(self):
        return self.application_settings.value("use_tf32", False, type=bool)
    
    @use_tf32.setter
    def use_tf32(self, val):
        self.application_settings.setValue("use_tf32", val)

    @property
    def use_enable_vae_slicing(self):
        return self.application_settings.value("use_enable_vae_slicing", True, type=bool)
    
    @use_enable_vae_slicing.setter
    def use_enable_vae_slicing(self, val):
        self.application_settings.setValue("use_enable_vae_slicing", val)

    @property
    def use_accelerated_transformers(self):
        return self.application_settings.value("use_accelerated_transformers", True, type=bool)
    
    @use_accelerated_transformers.setter
    def use_accelerated_transformers(self, val):
        self.application_settings.setValue("use_accelerated_transformers", val)

    @property
    def use_tiled_vae(self):
        return self.application_settings.value("use_tiled_vae", True, type=bool)
    
    @use_tiled_vae.setter
    def use_tiled_vae(self, val):
        self.application_settings.setValue("use_tiled_vae", val)

    @property
    def enable_model_cpu_offload(self):
        return self.application_settings.value("enable_model_cpu_offload", False, type=bool)
    
    @enable_model_cpu_offload.setter
    def enable_model_cpu_offload(self, val):
        self.application_settings.setValue("enable_model_cpu_offload", val)

    @property
    def use_enable_sequential_cpu_offload(self):
        return self.application_settings.value("use_enable_sequential_cpu_offload", False, type=bool)
    
    @use_enable_sequential_cpu_offload.setter
    def use_enable_sequential_cpu_offload(self, val):
        self.application_settings.setValue("use_enable_sequential_cpu_offload", val)

    @property
    def use_cudnn_benchmark(self):
        return self.application_settings.value("use_cudnn_benchmark", True, type=bool)
    
    @use_cudnn_benchmark.setter
    def use_cudnn_benchmark(self, val):
        self.application_settings.setValue("use_cudnn_benchmark", val)

    @property
    def use_torch_compile(self):
        return self.application_settings.value("use_torch_compile", False, type=bool)
    
    @use_torch_compile.setter
    def use_torch_compile(self, val):
        self.application_settings.setValue("use_torch_compile", val)

    @property
    def use_tome_sd(self):
        return self.application_settings.value("use_tome_sd", True, type=bool)
    
    @use_tome_sd.setter
    def use_tome_sd(self, val):
        self.application_settings.setValue("use_tome_sd", val)

    @property
    def tome_sd_ratio(self):
        return self.application_settings.value("tome_sd_ratio", 600, type=int)
    
    @tome_sd_ratio.setter
    def tome_sd_ratio(self, val):
        self.application_settings.setValue("tome_sd_ratio", val)


    @property
    def brush_size(self):
        return self.application_settings.value("brush_size", 1, type=int)
    
    @brush_size.setter
    def brush_size(self, val):
        self.application_settings.setValue("brush_size", val)
    
    @property
    def brush_primary_color(self):
        return self.application_settings.value("brush_primary_color", "#000000")
    
    @brush_primary_color.setter
    def brush_primary_color(self, val):
        self.application_settings.setValue("brush_primary_color", val)

    @property
    def brush_secondary_color(self):
        return self.application_settings.value("brush_secondary_color", "#ffffff")
    
    @brush_secondary_color.setter
    def brush_secondary_color(self, val):
        self.application_settings.setValue("brush_secondary_color", val)

    @property
    def ai_mode(self):
        return self.application_settings.value("ai_mode", False, type=bool)
    
    @ai_mode.setter
    def ai_mode(self, val):
        self.application_settings.setValue("ai_mode", val)
        self.ai_mode_toggled.emit(val)

    @property
    def show_grid(self):
        return self.application_settings.value("show_grid", True, type=bool)
    
    @show_grid.setter
    def show_grid(self, val):
        self.application_settings.setValue("show_grid", val)
        self.show_grid_toggled.emit(val)

    @property
    def hf_cache_path(self):
        return self.application_settings.value("hf_cache_path", default_hf_cache_dir())
    
    @hf_cache_path.setter
    def hf_cache_path(self, val):
        self.application_settings.setValue("hf_cache_path", val)
                
    @property
    def base_path(self):
        return self.application_settings.value("base_path", BASE_PATH + "/models")
    
    @base_path.setter
    def base_path(self, val):
        self.application_settings.setValue("base_path", val)
                
    @property
    def txt2img_model_path(self):
        return self.application_settings.value("txt2img_model_path", DEFAULT_PATHS["art"]["models"]["txt2img"])
    
    @txt2img_model_path.setter
    def txt2img_model_path(self, val):
        self.application_settings.setValue("txt2img_model_path", val)
                
    @property
    def depth2img_model_path(self):
        return self.application_settings.value("depth2img_model_path", DEFAULT_PATHS["art"]["models"]["depth2img"])
    
    @depth2img_model_path.setter
    def depth2img_model_path(self, val):
        self.application_settings.setValue("depth2img_model_path", val)
                
    @property
    def pix2pix_model_path(self):
        return self.application_settings.value("pix2pix_model_path", DEFAULT_PATHS["art"]["models"]["pix2pix"])
    
    @pix2pix_model_path.setter
    def pix2pix_model_path(self, val):
        self.application_settings.setValue("pix2pix_model_path", val)
                
    @property
    def inpaint_model_path(self):
        return self.application_settings.value("inpaint_model_path", DEFAULT_PATHS["art"]["models"]["inpaint"])
    
    @inpaint_model_path.setter
    def inpaint_model_path(self, val):
        self.application_settings.setValue("inpaint_model_path", val)
                
    @property
    def upscale_model_path(self):
        return self.application_settings.value("upscale_model_path", DEFAULT_PATHS["art"]["models"]["upscale"])
    
    @upscale_model_path.setter
    def upscale_model_path(self, val):
        self.application_settings.setValue("upscale_model_path", val)
                
    @property
    def txt2vid_model_path(self):
        return self.application_settings.value("txt2vid_model_path", DEFAULT_PATHS["art"]["models"]["txt2vid"])
    
    @txt2vid_model_path.setter
    def txt2vid_model_path(self, val):
        self.application_settings.setValue("txt2vid_model_path", val)
                
    @property
    def embeddings_model_path(self):
        return self.application_settings.value("embeddings_model_path", DEFAULT_PATHS["art"]["models"]["embeddings"])
    
    @embeddings_model_path.setter
    def embeddings_model_path(self, val):
        self.application_settings.setValue("embeddings_model_path", val)
                
    @property
    def lora_model_path(self):
        return self.application_settings.value("lora_model_path", DEFAULT_PATHS["art"]["models"]["lora"])
    
    @lora_model_path.setter
    def lora_model_path(self, val):
        self.application_settings.setValue("lora_model_path", val)
                
    @property
    def image_path(self):
        return self.application_settings.value("image_path", DEFAULT_PATHS["art"]["other"]["images"])
    
    @image_path.setter
    def image_path(self, val):
        self.application_settings.setValue("image_path", val)
                
    @property
    def video_path(self):
        return self.application_settings.value("video_path", DEFAULT_PATHS["art"]["other"]["videos"])
    
    @video_path.setter
    def video_path(self, val):
        self.application_settings.setValue("video_path", val)
                
    @property
    def llm_casuallm_model_path(self):
        return self.application_settings.value("llm_casuallm_model_path", DEFAULT_PATHS["text"]["models"]["casuallm"])
    
    @llm_casuallm_model_path.setter
    def llm_casuallm_model_path(self, val):
        self.application_settings.setValue("llm_casuallm_model_path", val)
                
    @property
    def llm_seq2seq_model_path(self):
        return self.application_settings.value("llm_seq2seq_model_path", DEFAULT_PATHS["text"]["models"]["seq2seq"])
    
    @llm_seq2seq_model_path.setter
    def llm_seq2seq_model_path(self, val):
        self.application_settings.setValue("llm_seq2seq_model_path", val)
                
    @property
    def llm_visualqa_model_path(self):
        return self.application_settings.value("llm_visualqa_model_path", DEFAULT_PATHS["text"]["models"]["visualqa"])
    
    @llm_visualqa_model_path.setter
    def llm_visualqa_model_path(self, val):
        self.application_settings.setValue("llm_visualqa_model_path", val)
                
    @property
    def vae_model_path(self):
        return self.application_settings.value("vae_model_path", DEFAULT_PATHS["art"]["models"]["vae"])
    
    @vae_model_path.setter
    def vae_model_path(self, val):
        self.application_settings.setValue("vae_model_path", val)

    def reset_paths(self):
        self.hf_cache_path = default_hf_cache_dir()
        self.base_path = BASE_PATH
        self.txt2img_model_path = DEFAULT_PATHS["art"]["models"]["txt2img"]
        self.depth2img_model_path = DEFAULT_PATHS["art"]["models"]["depth2img"]
        self.pix2pix_model_path = DEFAULT_PATHS["art"]["models"]["pix2pix"]
        self.inpaint_model_path = DEFAULT_PATHS["art"]["models"]["inpaint"]
        self.upscale_model_path = DEFAULT_PATHS["art"]["models"]["upscale"]
        self.txt2vid_model_path = DEFAULT_PATHS["art"]["models"]["txt2vid"]
        self.vae_model_path = DEFAULT_PATHS["art"]["models"]["vae"]
        self.embeddings_model_path = DEFAULT_PATHS["art"]["models"]["embeddings"]
        self.lora_model_path = DEFAULT_PATHS["art"]["models"]["lora"]
        self.image_path = DEFAULT_PATHS["art"]["other"]["images"]
        self.video_path = DEFAULT_PATHS["art"]["other"]["videos"]
        self.llm_casuallm_model_path = DEFAULT_PATHS["text"]["models"]["casuallm"]
        self.llm_seq2seq_model_path = DEFAULT_PATHS["text"]["models"]["seq2seq"]
        self.llm_visualqa_model_path = DEFAULT_PATHS["text"]["models"]["visualqa"]            
    
    def set_path_settings(self, key, val):
        path_settings = self.path_settings
        path_settings[key] = val
        self.path_settings = path_settings

    @property
    def resize_on_paste(self):
        return self.application_settings.value("resize_on_paste", True, type=bool)

    @resize_on_paste.setter
    def resize_on_paste(self, val):
        self.application_settings.setValue("resize_on_paste", val)
    
    @property
    def snap_to_grid(self):
        return self.application_settings.value("snap_to_grid", True, type=bool)

    @snap_to_grid.setter
    def snap_to_grid(self, val):
        self.application_settings.setValue("snap_to_grid", val)
        self.snap_to_grid_changed_signal.emit(val)

    @property
    def cell_size(self):
        return self.application_settings.value("cell_size", 64, type=int)

    @cell_size.setter
    def cell_size(self, val):
        self.application_settings.setValue("cell_size", val)
        self.cell_size_changed_signal.emit(val)
    
    @property
    def canvas_color(self):
        return self.application_settings.value("canvas_color", "#ffffff")
    
    @canvas_color.setter
    def canvas_color(self, val):
        self.application_settings.setValue("canvas_color", val)
        self.canvas_color_changed_signal.emit(val)
    
    @property
    def line_color(self):
        return self.application_settings.value("line_color", "#000000")
    
    @line_color.setter
    def line_color(self, val):
        self.application_settings.setValue("line_color", val)
        self.line_color_changed_signal.emit(val)
    
    @property
    def line_width(self):
        return self.application_settings.value("line_width", 1, type=int)
    
    @line_width.setter
    def line_width(self, val):
        self.application_settings.setValue("line_width", val)
        self.line_width_changed_signal.emit(val)

    @property
    def mode(self):
        return self.application_settings.value("mode", "Image Generation")
    
    @mode.setter
    def mode(self, val):
        self.application_settings.setValue("mode", val)
    
    @property
    def current_version_stablediffusion(self):
        return self.application_settings.value("current_version_stablediffusion", "1.5")
    
    @current_version_stablediffusion.setter
    def current_version_stablediffusion(self, val):
        self.application_settings.setValue("current_version_stablediffusion", val)

    @property
    def move_unused_model_to_cpu(self):
        return self.application_settings.value("move_unused_model_to_cpu", True, type=bool)
    
    @move_unused_model_to_cpu.setter
    def move_unused_model_to_cpu(self, val):
        self.application_settings.setValue("move_unused_model_to_cpu", val)

    @property
    def unload_unused_models(self):
        return self.application_settings.value("unload_unused_models", True, type=bool)
    
    @unload_unused_models.setter
    def unload_unused_models(self, val):
        self.application_settings.setValue("unload_unused_models", val)


    #### SETTINGS ####
    @property
    def canvas_settings(self):
        return self.application_settings.value("grid_settings", dict(
            pos_x=0,
            pos_y=0,
        ))
    
    @canvas_settings.setter
    def canvas_settings(self, val):
        self.application_settings.setValue("grid_settings", val)
        
    @property
    def generator_settings(self):
        return self.application_settings.value("generator_settings", dict(
            section="txt2img",
            generator_name="stablediffusion",
            prompt="",
            negative_prompt="",
            steps=20,
            ddim_eta=0.5,
            height=512,
            width=512,
            scale=750,
            seed=42,
            latents_seed=42,
            random_seed=True,
            random_latents_seed=True,
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
            version="SD 1.5",
            is_preset=False,
        ))

    @generator_settings.setter
    def generator_settings(self, val):
        self.application_settings.setValue("generator_settings", val)
    #### END GENERATOR SETTINGS ####

    @property
    def nsfw_filter(self):
        return self.application_settings.value("nsfw_filter", True, type=bool)
    
    @nsfw_filter.setter
    def nsfw_filter(self, val):
        self.application_settings.setValue("nsfw_filter", val)

    @property
    def current_tool(self):
        return self.application_settings.value("current_tool", "brush")
    
    @current_tool.setter
    def current_tool(self, val):
        self.application_settings.setValue("current_tool", val)

    @property
    def working_height(self):
        return self.application_settings.value("working_height", 512, type=int)
    
    @working_height.setter
    def working_height(self, val):
        self.application_settings.setValue("working_height", val)

    @property
    def working_width(self):
        return self.application_settings.value("working_width", 512, type=int)
    
    @working_width.setter
    def working_width(self, val):
        self.application_settings.setValue("working_width", val)
    
    @property
    def current_llm_generator(self):
        return self.application_settings.value("current_llm_generator", "casuallm")
    
    @current_llm_generator.setter
    def current_llm_generator(self, val):
        self.application_settings.setValue("current_llm_generator", val)

    @property
    def current_image_generator(self):
        return self.application_settings.value("current_image_generator", "stablediffusion")
    
    @current_image_generator.setter
    def current_image_generator(self, val):
        self.application_settings.setValue("current_image_generator", val)

    @property
    def hf_api_key_read_key(self):
        return self.application_settings.value("hf_api_key_read_key", "")
    
    @hf_api_key_read_key.setter
    def hf_api_key_read_key(self, val):
        self.application_settings.setValue("hf_api_key_read_key", val)

    @property
    def hf_api_key_write_key(self):
        return self.application_settings.value("hf_api_key_write_key", "")
    
    @hf_api_key_write_key.setter
    def hf_api_key_write_key(self, val):
        self.application_settings.setValue("hf_api_key_write_key", val)
    
    @property
    def pipeline(self):
        return self.application_settings.value("pipeline", "txt2img")
    
    @pipeline.setter
    def pipeline(self, val):
        self.application_settings.setValue("pipeline", val)

    @property
    def pipeline_versin(self):
        return self.application_settings.value("pipeline_version", "SD 1.5")
        
    @pipeline_versin.setter
    def pipeline_versin(self, val):
        self.application_settings.setValue("pipeline_version", val)

    @property
    def is_maximized(self):
        return self.application_settings.value("is_maximized", False, type=bool)
    
    @is_maximized.setter
    def is_maximized(self, val):
        self.application_settings.setValue("is_maximized", val)

    @property
    def show_active_image_area(self):
        return self.application_settings.value("show_active_image_area", True, type=bool)
    
    @show_active_image_area.setter
    def show_active_image_area(self, val):
        self.application_settings.setValue("show_active_image_area", val)

    @property
    def auto_export_images(self):
        return self.application_settings.value("auto_export_images", True, type=bool)
    
    @auto_export_images.setter
    def auto_export_images(self, val):
        self.application_settings.setValue("auto_export_images", val)
    
    @property
    def image_export_type(self):
        return self.application_settings.value("image_export_type", "png")
    
    @image_export_type.setter
    def image_export_type(self, val):
        self.application_settings.setValue("image_export_type", val)

    @property
    def enable_tts(self):
        return self.application_settings.value("enable_tts", True, type=bool)
    
    @enable_tts.setter
    def enable_tts(self, val):
        self.application_settings.setValue("enable_tts", val)
    
    @property
    def image_to_new_layer(self):
        return self.application_settings.value("image_to_new_layer", True, type=bool)
    
    @image_to_new_layer.setter
    def image_to_new_layer(self, val):
        self.application_settings.setValue("image_to_new_layer", val)
    
    @property
    def latest_version_check(self):
        return self.application_settings.value("latest_version_check", True, type=bool)
    
    @latest_version_check.setter
    def latest_version_check(self, val):
        self.application_settings.setValue("latest_version_check", val)
    
    @property
    def dark_mode_enabled(self):
        return self.application_settings.value("dark_mode_enabled", True, type=bool)
    
    @dark_mode_enabled.setter
    def dark_mode_enabled(self, val):
        self.application_settings.setValue("dark_mode_enabled", val)
        self.set_stylesheet()

    @property
    def allow_online_mode(self):
        return self.application_settings.value("allow_online_mode", True, type=bool)

    @allow_online_mode.setter
    def allow_online_mode(self, val):
        self.application_settings.setValue("allow_online_mode", val)

    @property
    def generator(self):
        with session_scope() as session:
            if self._generator is None:
                try:
                    self._generator = session.query(LLMGenerator).filter(
                        LLMGenerator.name == self.ui.standard_image_widget.ui.llm_settings_widget.current_generator
                    ).first()
                    if self._generator is None:
                        logger.error("Unable to locate generator by name " + self.ui.standard_image_widget.ui.llm_settings_widget.current_generator if self.ui.llm_settings_widget.current_generator else "None")
                except Exception as e:
                    logger.error(e)
            return self._generator
    
    @property
    def generate_signal(self):
        return self.generator_tab_widget.generate_signal

    @property
    def is_dark(self):
        return self.dark_mode_enabled

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

    def stop_progress_bar(self):
        self.generator_tab_widget.stop_progress_bar()
    
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

    def __init__(self, settings_manager, *args, **kwargs):
        logger.info("Starting AI Runnner")
        self.ui = Ui_MainWindow()
        self.application_settings = QSettings("Capsize Games", "AI Runner")

        # qdarktheme.enable_hi_dpi()

        self.settings_manager = settings_manager

        # set the api
        self.api = AIRunnerAPI(window=self)

        self.set_log_levels()
        self.testing = kwargs.pop("testing", False)

        # initialize the document
        with session_scope() as session:
            self.document = session.query(Document).first()

        super().__init__(*args, **kwargs)

        self.ui.setupUi(self)

        self.initialize()

        # on window resize:
        # self.windowStateChanged.connect(self.on_state_changed)

        # check for self.current_layer.lines every 100ms
        self.timer = self.startTimer(100)

        self.register_keypress()

        if not self.testing:
            logger.info("Executing window")
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
        
        if self.mode == Mode.IMAGE.value:
            self.image_generation_toggled()
        elif self.mode == Mode.LANGUAGE_PROCESSOR.value:
            self.language_processing_toggled()
        else:
            self.model_manager_toggled(True)

        self.initialize_image_worker()

        self.restore_state()

        self.settings_manager.changed_signal.connect(self.handle_changed_signal)
        
        self.loaded.emit()
    
    def create_airunner_paths(self):
        paths = [
            self.base_path,
            self.txt2img_model_path,
            self.depth2img_model_path,
            self.pix2pix_model_path,
            self.inpaint_model_path,
            self.upscale_model_path,
            self.txt2vid_model_path,
            self.embeddings_model_path,
            self.lora_model_path,
            self.image_path,
            self.video_path
        ]
        for index, path in enumerate(paths):
            if not os.path.exists(path):
                print("cerating path", index, path)
                os.makedirs(path)

    def initialize_image_worker(self):
        self.image_data_queue = queue.Queue()
        
        self.worker_thread = QThread()
        self.worker = ImageDataWorker(self)
        self.worker.stop_progress_bar.connect(self.stop_progress_bar)

        self.worker.moveToThread(self.worker_thread)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.started.connect(self.worker.process)
        self.worker_thread.start()
    
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
            self.app.image_path,
            self.app.image_export_type,
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
        if self.mode == Mode.IMAGE.value:
            self.canvas_widget.paste_image_from_clipboard()

    def action_copy_image_triggered(self):
        if self.mode == Mode.IMAGE.value:
            self.canvas_widget.copy_image(self.current_active_image())

    def action_cut_image_triggered(self):
        if self.mode == Mode.IMAGE.value:
            self.canvas_widget.cut_image()

    def action_rotate_90_clockwise_triggered(self):
        if self.mode == Mode.IMAGE.value:
            self.canvas_widget.rotate_90_clockwise()

    def action_rotate_90_counterclockwise_triggered(self):
        if self.mode == Mode.IMAGE.value:
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
        path = getattr(self.settings_manager.path_settings, name)
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
        size = self.cell_size
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
            f"Click to {'enable' if not self.nsfw_filter else 'disable'} NSFW filter"
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
        self.close()

    ##### Window properties #####
    # Use this to set and restore window properties
    # Such as splitter positions, window size, etc
    def closeEvent(self, event):
        logger.info("Quitting")
        self.save_state()
        event.accept()
        QApplication.quit()
    
    def save_state(self):
        self.application_settings.setValue("main_splitter", self.ui.main_splitter.saveState())
        self.application_settings.setValue("content_splitter", self.ui.content_splitter.saveState())
        self.application_settings.setValue("center_splitter", self.ui.center_splitter.saveState())
        self.application_settings.setValue("canvas_splitter", self.ui.canvas_splitter.saveState())
        self.application_settings.setValue("splitter", self.ui.splitter.saveState())
        self.application_settings.setValue("mode_tab_widget_index", self.ui.mode_tab_widget.currentIndex())
        self.application_settings.setValue("tool_tab_widget_index", self.ui.tool_tab_widget.currentIndex())
        self.application_settings.setValue("center_tab_index", self.ui.center_tab.currentIndex())
        self.application_settings.setValue("generator_tab_index", self.ui.standard_image_widget.ui.tabWidget.currentIndex())
        pass
    
    def restore_state(self):
        main_splitter = self.application_settings.value("main_splitter")
        if main_splitter is not None:
            self.ui.main_splitter.restoreState(main_splitter)
        
        content_splitter = self.application_settings.value("content_splitter")
        if content_splitter is not None:
            self.ui.content_splitter.restoreState(content_splitter)
        
        center_splitter = self.application_settings.value("center_splitter")
        if center_splitter is not None:
            self.ui.center_splitter.restoreState(center_splitter)
        
        canvas_splitter = self.application_settings.value("canvas_splitter")
        if canvas_splitter is not None:
            self.ui.canvas_splitter.restoreState(canvas_splitter)
        
        splitter = self.application_settings.value("splitter")
        if splitter is not None:
            self.ui.splitter.restoreState(splitter)

        mode_tab_widget_index = self.application_settings.value("mode_tab_widget_index", 0, type=int)
        self.ui.mode_tab_widget.setCurrentIndex(mode_tab_widget_index)

        tool_tab_widget_index = self.application_settings.value("tool_tab_widget_index", 0, type=int)
        self.ui.tool_tab_widget.setCurrentIndex(tool_tab_widget_index)

        center_tab_index = self.application_settings.value("center_tab_index", 0, type=int)
        self.ui.center_tab.setCurrentIndex(center_tab_index)

        generator_tab_index = self.application_settings.value("generator_tab_index", 0, type=int)
        self.ui.standard_image_widget.ui.tabWidget.setCurrentIndex(generator_tab_index)

        self.ui.ai_button.setChecked(self.ai_mode)
        self.set_button_checked("toggle_grid", self.show_grid, False)
    ##### End window properties #####
    #################################
        
    ###### Window handlers ######
    def cell_size_changed(self, val):
        self.cell_size = val

    def line_width_changed(self, val):
        self.line_width = val
    
    def line_color_changed(self, val):
        self.line_color = val
    
    def snap_to_grid_changed(self, val):
        self.snap_to_grid = val
    
    def canvas_color_changed(self, val):
        self.canvas_color = val

    def action_ai_toggled(self, val):
        self.ai_mode = val
    
    def action_toggle_grid(self, val):
        self.show_grid = val
    
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
        self.application_settings.setValue("nsfw_filter", val)
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
        logger.info("Resetting settings")
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
        logger.info("Setting stylesheets")
        theme_name = "dark_theme" if self.is_dark else "light_theme"
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
            self.set_icons(icon_data[0], icon_data[1], "dark" if self.is_dark else "light")

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

    def handle_generate(self):
        #self.prompt_builder.inject_prompt()
        pass

    def initialize_default_buttons(self):
        show_grid = self.show_grid
        self.ui.toggle_active_grid_area_button.blockSignals(True)
        self.ui.toggle_brush_button.blockSignals(True)
        self.ui.toggle_eraser_button.blockSignals(True)
        self.ui.toggle_grid_button.blockSignals(True)
        self.ui.ai_button.blockSignals(True)
        self.ui.toggle_active_grid_area_button.setChecked(self.current_tool == "active_grid_area")
        self.ui.toggle_brush_button.setChecked(self.current_tool == "brush")
        self.ui.toggle_eraser_button.setChecked(self.current_tool == "eraser")
        self.ui.toggle_grid_button.setChecked(show_grid is True)
        self.ui.toggle_active_grid_area_button.blockSignals(False)
        self.ui.toggle_brush_button.blockSignals(False)
        self.ui.toggle_eraser_button.blockSignals(False)
        self.ui.toggle_grid_button.blockSignals(False)
        self.ui.ai_button.blockSignals(False)

    @pyqtSlot(dict)
    def handle_button_clicked(self, kwargs):
        action = kwargs.get("action", "")
        if action == "toggle_tool":
            self.toggle_tool(kwargs["tool"])

    def toggle_tool(self, tool):
        self.settings_manager.set_value("settings.current_tool", tool)

    def initialize_mixins(self):
        #self.canvas = Canvas()
        pass

    def connect_signals(self):
        logger.info("Connecting signals")
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
        print(keys)
        if len(keys) > 0:
            if hasattr(self, keys[0]):
                obj = getattr(self, keys[0])
                if keys[1] in obj:
                    obj[keys[1]] = value
                    print("SETTING")
                    setattr(self, keys[0], obj)
            else:
                self.settings_manager.set_value(attr_name, value)
    
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
        logger.info("Initializing stable diffusion")
        self.client = OfflineClient(
            app=self,
            message_var=self.message_var,
            settings_manager=self.settings_manager,
        )

    def save_settings(self):
        self.settings_manager.save_settings()

    def display(self):
        logger.info("Displaying window")
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
        if self.is_maximized:
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
        grid_size = self.cell_size

        # if the shift key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ShiftModifier in event.modifiers():
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = self.working_width + increment
                self.settings_manager.set_value("settings.working_width", val)
        except TypeError:
            pass

        # if the control key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ControlModifier in event.modifiers():
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = self.working_height + increment
                self.settings_manager.set_value("settings.working_height", val)
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
        self.setWindowTitle(f"AI Runner {self.document_name}")

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

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            # logger.error(f"Invalid response message: {response}")
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
        logger.error(f"Unknown message code: {message}")

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

    def load_prompt(self, prompt: Prompt):
        """
        Loads prompt values from a Prompt model instance.
        :param prompt: PromptModel
        :return:
        """
        self.update_prompt(prompt.prompt)
        self.update_negative_prompt(prompt.negative_prompt)

    def update_prompt(self, prompt_value):
        self.generator_tab_widget.update_prompt(prompt_value)

    def update_negative_prompt(self, prompt_value):
        self.generator_tab_widget.update_negative_prompt(prompt_value)

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
        self.set_button_checked("model_manager", self.mode == Mode.MODEL_MANAGER.value)
    
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