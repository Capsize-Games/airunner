from PyQt6.QtCore import Qt, QSettings

from airunner.aihandler.settings import DEFAULT_BRUSH_PRIMARY_COLOR, DEFAULT_BRUSH_SECONDARY_COLOR
from airunner.settings import DEFAULT_PATHS
from airunner.utils import default_hf_cache_dir
from airunner.settings import BASE_PATH
from airunner.enums import Mode, SignalCode, ServiceCode
from airunner.service_locator import ServiceLocator
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data


tts_settings_default = dict(
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
)


class SettingsMixin:
    def __init__(self):
        super().__init__()
        self.application_settings = QSettings("Capsize Games", "AI Runner")
        self.register(SignalCode.RESET_SETTINGS_SIGNAL, self.on_reset_settings_signal)
        self.default_settings = dict(
            use_cuda=True,
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
            app_version="",
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
                zoom_level=1,
                zoom_in_step=0.1,
                zoom_out_step=0.1
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
                pos_y=0
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
                model="stabilityai/sd-turbo",
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
            tts_settings=tts_settings_default,
            stt_settings=dict(
                duration=10,
                fs=16000,
                channels=1,
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
            embeddings=[],
            pipelines=pipeline_bootstrap_data,
            controlnet=controlnet_bootstrap_data,
            ai_models=model_bootstrap_data,
            image_filters=imagefilter_bootstrap_data,
        )

    def update_settings(self):
        self.logger.info("Updating settings")
        default_settings = self.default_settings
        current_settings = self.settings
        for k, v in default_settings.items():
            if k not in current_settings:
                current_settings[k] = v
        self.logger.info("Settings updated")
        self.settings = current_settings

    def on_reset_settings_signal(self):
        self.logger.info("Resetting settings")
        self.application_settings.clear()
        self.application_settings.sync()
        self.settings = self.settings

    @property
    def ai_models(self):
        return self.settings["ai_models"]
    
    @ai_models.setter
    def ai_models(self, val):
        settings = self.settings
        settings["ai_models"] = val
        self.settings = settings

    @property
    def generator_settings(self):
        return self.settings["generator_settings"]
    
    @generator_settings.setter
    def generator_settings(self, val):
        settings = self.settings
        settings["generator_settings"] = val
        self.settings = settings

    @property
    def stt_settings(self):
        return self.settings["stt_settings"]
    
    @stt_settings.setter
    def stt_settings(self, val):
        settings = self.settings
        settings["stt_settings"] = val
        self.settings = settings

    @property
    def controlnet_settings(self):
        return self.settings["controlnet_settings"]
    
    @controlnet_settings.setter
    def controlnet_settings(self, val):
        settings = self.settings
        settings["controlnet_settings"] = val
        self.settings = settings

    @property
    def metadata_settings(self):
        return self.settings["metadata_settings"]
    
    @metadata_settings.setter
    def metadata_settings(self, val):
        settings = self.settings
        settings["metadata_settings"] = val
        self.settings = settings

    @property
    def canvas_settings(self):
        return self.settings["canvas_settings"]
    
    @canvas_settings.setter
    def canvas_settings(self, val):
        settings = self.settings
        settings["canvas_settings"] = val
        self.settings = settings

    @property
    def active_grid_settings(self):
        return self.settings["active_grid_settings"]
    
    @active_grid_settings.setter
    def active_grid_settings(self, val):
        settings = self.settings
        settings["active_grid_settings"] = val
        self.settings = settings

    @property
    def standard_image_settings(self):
        return self.settings["standard_image_settings"]
    
    @standard_image_settings.setter
    def standard_image_settings(self, val):
        settings = self.settings
        settings["standard_image_settings"] = val
        self.settings = settings

    @property
    def path_settings(self):
        return self.settings["path_settings"]
    
    @path_settings.setter
    def path_settings(self, val):
        settings = self.settings
        settings["path_settings"] = val
        self.settings = settings
    
    @property
    def brush_settings(self):
        return self.settings["brush_settings"]
    
    @brush_settings.setter
    def brush_settings(self, val):
        settings = self.settings
        settings["brush_settings"] = val
        self.settings = settings

    @property
    def grid_settings(self):
        return self.settings["grid_settings"]
    
    @grid_settings.setter
    def grid_settings(self, val):
        settings = self.settings
        settings["grid_settings"] = val
        self.settings = settings

    @property
    def window_settings(self):
        return self.settings["window_settings"]
    
    @window_settings.setter
    def window_settings(self, val):
        settings = self.settings
        settings["window_settings"] = val
        self.settings = settings

    @property
    def shortcut_key_settings(self):
        return self.settings["shortcut_key_settings"]
    
    @shortcut_key_settings.setter
    def shortcut_key_settings(self, val):
        settings = self.settings
        settings["shortcut_key_settings"] = val
        self.settings = settings

    @property
    def memory_settings(self):
        return self.settings["memory_settings"]
    
    @memory_settings.setter
    def memory_settings(self, val):
        settings = self.settings
        settings["memory_settings"] = val
        self.settings = settings
    
    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]
    
    @llm_generator_settings.setter
    def llm_generator_settings(self, val):
        settings = self.settings
        settings["llm_generator_settings"] = val
        self.settings = settings

    @property
    def tts_settings(self):
        tts_settings = self.settings.get("tts_settings")
        if tts_settings is None:
            self.tts_settings = tts_settings_default
            tts_settings = self.settings.get("tts_settings")
            print("GETTING TTS_SETTINGS", tts_settings)
        return tts_settings
    
    @tts_settings.setter
    def tts_settings(self, val):
        settings = self.settings
        settings["tts_settings"] = val
        self.settings = settings

    @property
    def llm_templates(self):
        return self.settings["llm_templates"]
    
    @llm_templates.setter
    def llm_templates(self, val):
        settings = self.settings
        settings["llm_templates"] = val
        self.settings = settings

    @property
    def settings(self):
        try:
            return self.get_settings()
        except Exception as e:
            self.logger.error("Failed to get settings")
            self.logger.error(e)
            return {}
    
    @settings.setter
    def settings(self, val):
        try:
            self.set_settings(val)
        except Exception as e:
            self.logger.error("Failed to set settings")
            self.logger.error(e)

    def get_settings(self):
        try:
            return self.application_settings.value(
                "settings",
                self.default_settings,
                type=dict
            )
        except TypeError as e:
            print("Settings crashed, resetting to default")
            # self.application_settings.setValue("settings", current_settings)
            # self.application_settings.sync()
            return self.default_settings

    def set_settings(self, val):
        self.application_settings.setValue("settings", val)
        self.application_settings.sync()
        self.emit(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)

    def reset_paths(self):
        path_settings = self.path_settings
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
        self.path_settings = path_settings

    @property
    def is_windows(self):
        return self.get_service(ServiceCode.IS_WINDOWS)()