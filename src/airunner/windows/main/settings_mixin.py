import json

from PySide6.QtCore import QSettings
import traceback

from airunner.aihandler.logger import Logger
from airunner.settings import (
    DEFAULT_BRUSH_PRIMARY_COLOR,
    DEFAULT_BRUSH_SECONDARY_COLOR,
    DEFAULT_SCHEDULER, ORGANIZATION, APPLICATION_NAME, DEFAULT_SHORTCUTS
)
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.enums import Mode, SignalCode, CanvasToolName, LLMActionType, ImageGenerator, GeneratorSection, \
    ImageCategory, Controlnet
from airunner.settings import BASE_PATH, MALE, DEFAULT_MODELS, DEFAULT_MODELS_VERSION, LLM_TEMPLATES_VERSION
from airunner.settings import DEFAULT_PATHS
from airunner.settings import DEFAULT_CHATBOT
from airunner.utils import default_hf_cache_dir

tts_settings_default = {
    'use_bark': False,
    'enable_tts': True,
    'use_cuda': True,
    'use_sentence_chunks': True,
    'use_word_chunks': False,
    'cuda_index': 0,
    'word_chunks': 1,
    'sentence_chunks': 1,
    'play_queue_buffer_length': 1,
    'enable_cpu_offload': True,
    "model": "SpeechT5",
    "espeak": {
        "gender": "male",
        "voice": "male1",
        "language": "en-US",
        "rate": 0,
        "pitch": 0,
        "volume": 0,
        "punctuation_mode": "none",
    },
    "bark": {
        "language": "English",
        "voice": "v2/en_speaker_6",
        "gender": "Male",
        "fine_temperature": 80,
        "coarse_temperature": 40,
        "semantic_temperature": 80,
    }
}
STABLEDIFFUSION_GENERATOR_SETTINGS = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 1,
    "ddim_eta": 0.5,
    "height": 512,
    "width": 512,
    "scale": 0,
    "seed": 42,
    "random_seed": True,
    "model": "stabilityai/sd-turbo",
    "scheduler": DEFAULT_SCHEDULER,
    "prompt_triggers": "",
    "strength": 50,
    "image_guidance_scale": 150,
    "n_samples": 1,
    "enable_controlnet": False,
    "clip_skip": 0,
    "variation": False,
    "use_prompt_builder": False,
    "active_grid_border_color": "#00FF00",
    "active_grid_fill_color": "#FF0000",
    "version": "SD Turbo",
    "is_preset": False,
    "input_image": None,
}
DEFAULT_GENERATOR_SETTINGS = {
    "controlnet_image_settings": {
        "imported_image_base64": None,
        "link_to_input_image": True,
        "use_imported_image": False,
        "use_grid_image": False,
        "recycle_grid_image": False,
        "mask_link_input_image": False,
        "mask_use_imported_image": False,
        "controlnet": Controlnet.CANNY.value,
        "conditioning_scale": 100,
        "guidance_scale": 750,
        "controlnet_image_base64": None
    },
    "section": "txt2img",
    "generator_name": "stablediffusion",
    "presets": {},
}
GENERATOR_SETTINGS = DEFAULT_GENERATOR_SETTINGS.copy()
GENERATOR_SETTINGS.update(STABLEDIFFUSION_GENERATOR_SETTINGS)

for category in ImageCategory:
    GENERATOR_SETTINGS["presets"][category.value] = {}
    GENERATOR_SETTINGS["presets"][category.value][ImageGenerator.STABLEDIFFUSION.value] = {}

    for section in GeneratorSection:
        # TODO: default upscale model?
        if section == GeneratorSection.UPSCALE:
            continue
        default_model = DEFAULT_MODELS[ImageGenerator.STABLEDIFFUSION.value][section]
        GENERATOR_SETTINGS["presets"][category.value][ImageGenerator.STABLEDIFFUSION.value][section.value] = STABLEDIFFUSION_GENERATOR_SETTINGS.copy()


class SettingsMixin:
    def __init__(self):
        self.logger = Logger(prefix=self.__class__.__name__)
        self.application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        self.register(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL, self.on_reset_settings_signal)
        self.default_settings = {
            "trust_remote_code": False,
            "use_cuda": True,
            "current_layer_index": 0,
            "ocr_enabled": False,
            "tts_enabled": False,
            "stt_enabled": False,
            "ai_mode": True,
            "nsfw_filter": True,
            "resize_on_paste": True,
            "image_to_new_layer": True,
            "dark_mode_enabled": True,
            "latest_version_check": True,
            "app_version": "",
            "allow_online_mode": True,
            "current_version_stablediffusion": "SD Turbo",
            "current_tool": CanvasToolName.ACTIVE_GRID_AREA.value,
            "image_export_type": "png",
            "auto_export_images": True,
            "show_active_image_area": True,
            "working_width": 512,
            "working_height": 512,
            "current_llm_generator": "casuallm",
            "current_image_generator": ImageGenerator.STABLEDIFFUSION.value,
            "generator_section": GeneratorSection.TXT2IMG.value,
            "hf_api_key_read_key": "",
            "hf_api_key_write_key": "",
            "pipeline": "txt2img",
            "pipeline_version": "SD Turbo",
            "is_maximized": False,
            "llm_templates_version": LLM_TEMPLATES_VERSION,
            "default_models_version": DEFAULT_MODELS_VERSION,
            "pivot_point_x": 0,
            "pivot_point_y": 0,
            "mode": Mode.IMAGE.value,
            "autoload_sd": True,
            "autoload_llm": False,
            "llm_templates": {
                "Stable Diffusion Prompt Template": {
                    "name": "Stable Diffusion Prompt Template",
                    "model": "mistralai/Mistral-7B-Instruct-v0.2",
                    "llm_category": "casuallm",
                },
                "Mistral 7B Instruct: Default Chatbot": {
                    "name": "Mistral 7B Instruct: Default Chatbot",
                    "model": "mistralai/Mistral-7B-Instruct-v0.2",
                    "llm_category": "casuallm",
                },
                "StableLM 2 Zephyr: Default Chatbot": {
                    "name": "StableLM 2 Zephyr: Default Chatbot",
                    "model": "stabilityai/stablelm-2-zephyr-1_6b",
                    "llm_category": "casuallm",
                }
            },
            "shortcut_key_settings": DEFAULT_SHORTCUTS,
            "window_settings": {
                "content_splitter": None,
                "splitter": None,
                "mode_tab_widget_index": 0,
                "tool_tab_widget_index": 0,
                "center_tab_index": 0,
                "generator_tab_index": 0,
                "is_maximized": False,
                "is_fullscreen": False,
                "canvas_splitter": None,
                "canvas_side_splitter": None
            },
            "memory_settings": {
               "use_last_channels": True,
               "use_attention_slicing": False,
               "use_tf32": False,
               "use_enable_vae_slicing": True,
               "use_accelerated_transformers": True,
               "use_tiled_vae": True,
               "enable_model_cpu_offload": False,
               "use_enable_sequential_cpu_offload": False,
               "use_cudnn_benchmark": True,
               "use_torch_compile": False,
               "use_tome_sd": True,
               "tome_sd_ratio": 600,
               "move_unused_model_to_cpu": False,
               "unload_unused_models": True,
            },
            "drawing_pad_settings": {
                "image": None,
                "mask": None,
                "enabled": True,
            },
            "grid_settings": {
                "cell_size": 64,
                "line_width": 1,
                "line_color": "#101010",
                "snap_to_grid": True,
                "canvas_color": "#000000",
                "show_grid": True,
                "zoom_level": 1,
                "zoom_in_step": 0.1,
                "zoom_out_step": 0.1
            },
            "brush_settings": {
                "size": 20,
                "primary_color": DEFAULT_BRUSH_PRIMARY_COLOR,
                "secondary_color": DEFAULT_BRUSH_SECONDARY_COLOR,
            },
            "path_settings": {
                "hf_cache_path": default_hf_cache_dir(),
                "base_path": BASE_PATH,
                "txt2img_model_path": DEFAULT_PATHS["art"]["models"]["txt2img"],
                "depth2img_model_path": DEFAULT_PATHS["art"]["models"]["depth2img"],
                "pix2pix_model_path": DEFAULT_PATHS["art"]["models"]["pix2pix"],
                "inpaint_model_path": DEFAULT_PATHS["art"]["models"]["inpaint"],
                "upscale_model_path": DEFAULT_PATHS["art"]["models"]["upscale"],
                "txt2vid_model_path": DEFAULT_PATHS["art"]["models"]["txt2vid"],
                "embeddings_model_path": DEFAULT_PATHS["art"]["models"]["embeddings"],
                "lora_model_path": DEFAULT_PATHS["art"]["models"]["lora"],
                "image_path": DEFAULT_PATHS["art"]["other"]["images"],
                "video_path": DEFAULT_PATHS["art"]["other"]["videos"],
                "llm_casuallm_model_path": DEFAULT_PATHS["text"]["models"]["casuallm"],
                "llm_seq2seq_model_path": DEFAULT_PATHS["text"]["models"]["seq2seq"],
                "llm_visualqa_model_path": DEFAULT_PATHS["text"]["models"]["visualqa"],
                "llm_casuallm_model_cache_path": DEFAULT_PATHS["text"]["models"]["casuallm_cache"],
                "llm_seq2seq_model_cache_path": DEFAULT_PATHS["text"]["models"]["seq2seq_cache"],
                "llm_visualqa_model_cache_path": DEFAULT_PATHS["text"]["models"]["visualqa_cache"],
                "llm_misc_model_cache_path": DEFAULT_PATHS["text"]["models"]["misc_cache"],
                "vae_model_path": DEFAULT_PATHS["art"]["models"]["vae"],
                "ebook_path": DEFAULT_PATHS["text"]["other"]["ebooks"],
                "documents_path": DEFAULT_PATHS["text"]["other"]["documents"],
                "llama_index_path": DEFAULT_PATHS["text"]["other"]["llama_index"],
            },
            "active_grid_settings": {
                "enabled": True,
                "render_border": True,
                "render_fill": False,
                "border_opacity": 50,
                "fill_opacity": 50,
                "pos_x": 0,
                "pos_y": 0,
                "width": 512,
                "height": 512,
            },
            "canvas_settings": {
                "pos_x": 0,
                "pos_y": 0,
                "image": None,
                "enable_automatic_drawing": True,
            },
            "metadata_settings": {
                "image_export_metadata_prompt": True,
                "image_export_metadata_negative_prompt": True,
                "image_export_metadata_scale": True,
                "image_export_metadata_seed": True,
                "image_export_metadata_steps": True,
                "image_export_metadata_ddim_eta": True,
                "image_export_metadata_iterations": True,
                "image_export_metadata_samples": True,
                "image_export_metadata_model": True,
                "image_export_metadata_model_branch": True,
                "image_export_metadata_scheduler": True,
                "export_metadata": True,
                "import_metadata": True,
            },
            "controlnet_settings": {
                "image": None
            },
            "generator_settings": GENERATOR_SETTINGS,
            "llm_generator_settings": {
                "action": LLMActionType.CHAT.value,
                "use_tool_filter": False,
                "top_p": 90,
                "max_length": 50,
                "repetition_penalty": 100,
                "min_length": 10,
                "length_penalty": 100,
                "num_beams": 1,
                "ngram_size": 0,
                "temperature": 1000,
                "sequences": 1,
                "top_k": 0,
                "seed": 0,
                "do_sample": False,
                "eta_cutoff": 10,
                "early_stopping": True,
                "random_seed": False,
                "model_version": "mistralai/Mistral-7B-Instruct-v0.2",
                "dtype": "4bit",
                "use_gpu": True,
                "message_type": "chat",
                "override_parameters": False,
                "current_chatbot": "Default",
                "saved_chatbots": {
                    "Default": DEFAULT_CHATBOT
                },
        "embeddings_model_path": "BAAI/bge-small-en-v1.5",
        "prompt_template": "StableLM 2 Zephyr: Default Chatbot",
            },
            "tts_settings": tts_settings_default,
            "stt_settings": {
                "duration": 10,
                "fs": 16000,
                "channels": 1,
                "volume_input_threshold": 0.08,
                "silence_buffer_seconds": 1.0,
                "chunk_duration": 0.03,
            },
            "schedulers": [
                {
                    "name": "EULER_ANCESTRAL",
                    "display_name": "Euler A",
                },
                {
                    "name": "EULER",
                    "display_name": "Euler",
                },
                {
                    "name": "LMS",
                    "display_name": "LMS",
                },
                {
                    "name": "HEUN",
                    "display_name": "Heun",
                },
                {
                    "name": "DPM2",
                    "display_name": "DPM2",
                },
                {
                    "name": "DPM_PP_2M",
                    "display_name": "DPM++ 2M",
                },
                {
                    "name": "DPM2_K",
                    "display_name": "DPM2 Karras",
                },
                {
                    "name": "DPM2_A_K",
                    "display_name": "DPM2 a Karras",
                },
                {
                    "name": "DPM_PP_2M_K",
                    "display_name": "DPM++ 2M Karras",
                },
                {
                    "name": "DPM_PP_2M_SDE_K",
                    "display_name": "DPM++ 2M SDE Karras",
                },
                {
                    "name": "DDIM",
                    "display_name": "DDIM",
                },
                {
                    "name": "UNIPC",
                    "display_name": "UniPC",
                },
                {
                    "name": "DDPM",
                    "display_name": "DDPM",
                },
                {
                    "name": "DEIS",
                    "display_name": "DEIS",
                },
                {
                    "name": "DPM_2M_SDE_K",
                    "display_name": "DPM 2M SDE Karras",
                },
                {
                    "name": "PLMS",
                    "display_name": "PLMS",
                },
            ],
            "translation_settings": {
                "language": "English",
                "gender": MALE,
                "voice": "",
                "translation_model": "",
                "enabled": False,
            },
            "saved_prompts": [],
            "presets": [],
            "lora": [],
            "embeddings": [],
            "pipelines": pipeline_bootstrap_data,
            "controlnet": controlnet_bootstrap_data,
            "ai_models": model_bootstrap_data,
            "image_filters": imagefilter_bootstrap_data,
            "trusted_huggingface_repos": []
        }

    def update_settings(self):
        self.logger.debug("Updating settings")
        default_settings = self.default_settings
        current_settings = self.settings
        if current_settings is None:
            current_settings = default_settings
        else:
            self.recursive_update(current_settings, default_settings)
        self.logger.debug("Settings updated")

        # update llm_templates_version
        llm_templates_version = self.default_settings["llm_templates_version"]
        if llm_templates_version != current_settings["llm_templates_version"]:
            self.logger.debug("Updating LLM templates")
            current_settings["llm_templates"] = self.default_settings["llm_templates"]
            current_settings["llm_templates_version"] = llm_templates_version

        # update default_models_version
        default_models_version = self.default_settings["default_models_version"]
        if default_models_version != current_settings["default_models_version"]:
            self.logger.debug("Updating default models")
            current_settings["ai_models"] = model_bootstrap_data
            current_settings["default_models_version"] = default_models_version

        self.settings = current_settings

    def recursive_update(self, current, default):
        for k, v in default.items():
            if k not in current or k not in current or (not isinstance(current[k], type(v)) and v is not None):
                self.logger.debug(f"Updating {k} to {v}")
                current[k] = v
            elif isinstance(v, dict):
                self.recursive_update(current[k], v)

    def on_reset_settings_signal(self):
        self.logger.debug("Resetting settings")
        self.application_settings.clear()
        self.application_settings.sync()
        self.settings = self.settings

    @property
    def settings(self):
        try:
            settings = self.get_settings()
            if settings == {} or settings == "" or settings is None:
                print("SETTINGS IS BLANK")
                traceback.print_stack()
            return settings
        except Exception as e:
            print("Failed to get settings")
            print(e)
        return {}
    
    @settings.setter
    def settings(self, val):
        try:
            self.set_settings(val)
        except Exception as e:
            print("Failed to set settings")
            print(e)

    def get_settings(self):
        application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        try:
            settings: str = application_settings.value(
                "settings",
                "",
                type=str
            )
            settings = json.loads(settings) if settings != "" else self.default_settings
            if settings != {} and settings != "" and settings != None:
                return settings
        except TypeError as e:
            print(e)
        except RuntimeError as e:
            print(e)

        # self.application_settings.setValue("settings", self.default_settings)
        # self.application_settings.sync()
        # return self.default_settings

    def save_settings(self):
        application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        application_settings.sync()

    def set_settings(self, val):
        application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        if val == {} or val == "" or val is None:
            return
        application_settings.setValue("settings", json.dumps(val))
        #self.application_settings.sync()
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)

    def reset_paths(self):
        path_settings = self.settings["path_settings"]
        path_settings["hf_cache_path"] = default_hf_cache_dir()
        path_settings["base_path"] = BASE_PATH
        path_settings["txt2img_model_path"] = DEFAULT_PATHS["art"]["models"]["txt2img"]
        path_settings["depth2img_model_path"] = DEFAULT_PATHS["art"]["models"]["depth2img"]
        path_settings["pix2pix_model_path"] = DEFAULT_PATHS["art"]["models"]["pix2pix"]
        path_settings["inpaint_model_path"] = DEFAULT_PATHS["art"]["models"]["inpaint"]
        path_settings["upscale_model_path"] = DEFAULT_PATHS["art"]["models"]["upscale"]
        path_settings["txt2vid_model_path"] = DEFAULT_PATHS["art"]["models"]["txt2vid"]
        path_settings["vae_model_path"] = DEFAULT_PATHS["art"]["models"]["vae"]
        path_settings["embeddings_model_path"] = DEFAULT_PATHS["art"]["models"]["embeddings"]
        path_settings["lora_model_path"] = DEFAULT_PATHS["art"]["models"]["lora"]
        path_settings["image_path"] = DEFAULT_PATHS["art"]["other"]["images"]
        path_settings["video_path"] = DEFAULT_PATHS["art"]["other"]["videos"]
        path_settings["llm_casuallm_model_path"] = DEFAULT_PATHS["text"]["models"]["casuallm"]
        path_settings["llm_seq2seq_model_path"] = DEFAULT_PATHS["text"]["models"]["seq2seq"]
        path_settings["llm_visualqa_model_path"] = DEFAULT_PATHS["text"]["models"]["visualqa"]
        path_settings["ebook_path"] = DEFAULT_PATHS["text"]["other"]["ebooks"]
        path_settings["documents_path"] = DEFAULT_PATHS["text"]["other"]["documents"]
        path_settings["llama_index_path"] = DEFAULT_PATHS["text"]["other"]["llama_index"]
        self.settings["path_settings"] = path_settings
