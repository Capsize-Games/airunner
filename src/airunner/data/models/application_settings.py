from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import BaseModel
from airunner.enums import (
    ImageGenerator,
    GeneratorSection,
    CanvasToolName,
    Mode,
)


class ApplicationSettings(BaseModel):
    __tablename__ = "application_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    use_cuda = Column(Boolean, default=True)
    sd_enabled = Column(Boolean, default=False)
    llm_enabled = Column(Boolean, default=False)
    tts_enabled = Column(Boolean, default=False)
    stt_enabled = Column(Boolean, default=False)
    controlnet_enabled = Column(Boolean, default=False)
    ai_mode = Column(Boolean, default=True)
    active_grid_size_lock = Column(Boolean, default=False)
    installation_path = Column(String, default="~/.local/share/airunner")
    current_layer_index = Column(Integer, default=0)
    paths_initialized = Column(Boolean, default=False)
    trust_remote_code = Column(
        Boolean, default=False
    )  # Leave this hardcoded. We will never trust remote code.
    nsfw_filter = Column(Boolean, default=True)
    resize_on_paste = Column(Boolean, default=True)
    image_to_new_layer = Column(Boolean, default=True)
    dark_mode_enabled = Column(Boolean, default=True)
    override_system_theme = Column(Boolean, default=True)
    latest_version_check = Column(Boolean, default=True)
    app_version = Column(String, default="")
    allow_online_mode = Column(Boolean, default=True)
    current_tool = Column(String, default=CanvasToolName.BRUSH.value)
    image_export_type = Column(String, default="png")
    auto_export_images = Column(Boolean, default=True)
    show_active_image_area = Column(Boolean, default=True)
    working_width = Column(Integer, default=512)
    working_height = Column(Integer, default=512)
    current_llm_generator = Column(String, default="causallm")
    current_image_generator = Column(
        String, default=ImageGenerator.STABLEDIFFUSION.value
    )
    generator_section = Column(String, default=GeneratorSection.TXT2IMG.value)
    hf_api_key_read_key = Column(String, default="")
    hf_api_key_write_key = Column(String, default="")
    civit_ai_api_key = Column(String, default="")
    is_maximized = Column(Boolean, default=False)
    pivot_point_x = Column(Integer, default=0)
    pivot_point_y = Column(Integer, default=0)
    mode = Column(String, default=Mode.IMAGE.value)
    autoload_sd = Column(Boolean, default=True)
    autoload_llm = Column(Boolean, default=False)
    show_nsfw_warning = Column(Boolean, default=True)
    run_setup_wizard = Column(Boolean, default=True)
    download_wizard_completed = Column(Boolean, default=False)
    stable_diffusion_agreement_checked = Column(Boolean, default=True)
    airunner_agreement_checked = Column(Boolean, default=True)
    user_agreement_checked = Column(Boolean, default=True)
    llama_license_agreement_checked = Column(Boolean, default=True)
